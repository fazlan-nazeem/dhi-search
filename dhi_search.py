import requests
import json
import sys
import os
from fuzzywuzzy import process, fuzz

def get_jwt_token():
    """Exchanges Docker PAT for JWT token using auth/token endpoint."""
    username = os.getenv('DOCKER_USERNAME')
    pat = os.getenv('DOCKER_PAT')

    if not username or not pat:
        print("Error: DOCKER_USERNAME and DOCKER_PAT environment variables must be set.")
        sys.exit(1)

    # User requested https://hub.docker.com/v2/auth/token
    # usage for PAT exchange often implies sending the PAT.
    url = 'https://hub.docker.com/v2/auth/token'
    
    try:
        # User provided specific payload format:
        # { "identifier": "username", "secret": "pat" }
        payload = {
            'identifier': username,
            'secret': pat
        }
        response = requests.post(url, json=payload)
        
        response.raise_for_status()
        data = response.json()
        return data.get('token') or data.get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Error authenticating: {e}")
        if 'response' in locals() and response.content:
            print(f"Response: {response.content.decode()}")
        sys.exit(1)

def fetch_catalog(token):
    """Fetches the Docker Hardened Image catalog using Scout GraphQL API."""
    url = 'https://api.scout.docker.com/v1/graphql'
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'dhi-search-tool/1.0'
    }
    
    # Query structure based on found schema
    query = """
    query dhiListRepositories {
      dhiListRepositories {
        items {
          name
          type
          tagNames
        }
      }
    }
    """
    
    payload = {'query': query}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching catalog: {e}")
        if response.content:
             print(f"Response: {response.content.decode()}")
        sys.exit(1)

def extract_image_names(catalog_data):
    """Extracts image names and stats from the GraphQL response."""
    stats = {}
    image_data = {} # name -> tags_list
    
    try:
        items = catalog_data['data']['dhiListRepositories']['items']
        for item in items:
            name = item.get('name')
            # Assuming 'type' values like 'IMAGE', 'HELM_CHART' etc. 
            item_type = item.get('type', 'Unknown')
            
            if name:
                stats[item_type] = stats.get(item_type, 0) + 1
                
                # Extract tags
                # Field is 'tagNames', which is a list of strings
                tags = item.get('tagNames', []) or []
                
                image_data[name] = tags
                
    except (KeyError, TypeError) as e:
        print(f"Error parsing GraphQL response: {e}")
        print("Full response from server:")
        print(json.dumps(catalog_data, indent=2))
        sys.exit(1)

    return image_data, stats

def find_matches(input_image, catalog_image_data):
    """Finds fuzzy matches for a given image name."""
    catalog_images = list(catalog_image_data.keys())
    # Normalize input: remove spaces, lowercase
    query = input_image.lower()
    
    # Aliases for known mappings
    aliases = {
        '.net': 'dotnet',
    }
    
    for k, v in aliases.items():
        if k in query:
            query = query.replace(k, v)
    
    # Common words that might cause false positives if matched alone    
    stop_words = {'runtime', 'sdk', 'cli', 'agent', 'operator', 'server', 'client', 'driver', 'plugin', 'controller'}
    
    # Create a "core" name removing stop words for stricter checking
    query_parts = query.split()
    core_parts = [p for p in query_parts if p not in stop_words]
    core_name = " ".join(core_parts) if core_parts else query
    
    # We want to find catalog images that correspond to the input.
    matches = process.extract(query, catalog_images, limit=5, scorer=fuzz.WRatio)
    
    results = []
    for name, score in matches:
        # Filter 1: High score threshold
        # WRatio handles case and some partial matching, so we can expect higher scores for good matches.
        if score < 85:
            continue
            
        # Filter 2: Core name check
        # If the query had stop words, ensure the core name is present in the result
        # This prevents ".NET Runtime" (core: .net) matching "Rust" just because of "Runtime" partials or other noise
        # Actually, .NET Runtime failing to match Rust is likely due to length differences or specific token matches.
        # But let's verify if 'core_name' is a substring of the result or highly similar.
        
        # If we have a distinctive core name, enforce it.
        # e.g. "Angular CLI" -> core "angular". Result "argo-cli" -> core "argo". "angular" not in "argo-cli".
        
        name_clean = name.replace('-', ' ').replace('_', ' ').lower()
        if core_name and len(core_name) > 2:
             # simple substring check for the core part
             if core_name not in name_clean:
                 # Double check with fuzzy on core name to allow some variation
                 core_score = fuzz.partial_ratio(core_name, name_clean)
                 if core_score < 80:
                     continue
                     
        # Filter 3: Specific Keyword Enforcement
        # If specific keywords are in the input, the result MUST contain them
        keywords_to_enforce = ['cli', 'sdk']
        should_continue = False
        for kw in keywords_to_enforce:
            if kw in query_parts and kw not in name_clean:
                should_continue = True
                break
        
        if should_continue:
            # CHECK TAGS: If specific keywords are missing from name, check if they exist in tags
            # We need to access tags for 'name'.
            tags = catalog_image_data.get(name, [])
            tags_str = " ".join(tags).lower()
            
            # Re-evaluate keywords against tags
            all_keywords_found_in_tags = True
            for kw in keywords_to_enforce:
                if kw in query_parts:
                    # kw must be in name OR tags
                    if kw not in name_clean and kw not in tags_str:
                        all_keywords_found_in_tags = False
                        break
            
            if not all_keywords_found_in_tags:
                continue

        results.append((name, score))
             
    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

def load_input(filepath):
    """Reads the list of images from the input file."""
    try:
        with open(filepath, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: {filepath} not found.")
        sys.exit(1)

def main():
    input_file = 'input.txt'
    input_images = load_input(input_file)
    
    print("Fetching Docker Hardened Image catalog...")
    print("Authenticating with Docker Hub...")
    token = get_jwt_token()
    print("Authentication successful.")
    
    print("Fetching Docker Hardened Image catalog (via GraphQL)...")
    catalog_data = fetch_catalog(token)
    
    catalog_image_data, stats = extract_image_names(catalog_data)
    catalog_images = list(catalog_image_data.keys())
    
    print("\nCatalog Statistics:")
    total_images = len(catalog_images)
    for k, v in stats.items():
        print(f"  - {k}: {v}")
    print(f"  - Total: {total_images}")
    
    print("\nMatching Results:")
    print(f"{'Input Image':<40} | {'Matched Images'}")
    print("-" * 80)
    
    for img in input_images:
        matches = find_matches(img, catalog_image_data)
        if matches:
            match_str = ", ".join(matches[:3]) # Show top 3
            print(f"{img:<40} | {match_str}")
        else:
            print(f"{img:<40} | (No match found)")
            
    # Save results to CSV files
    import csv
    
    with open('unmatched_results.csv', 'w', newline='') as f_unmatched, open('matched_results.csv', 'w', newline='') as f_matched:
        writer_unmatched = csv.writer(f_unmatched)
        writer_matched = csv.writer(f_matched)
        
        # Headers
        writer_unmatched.writerow(['Input Image'])
        writer_matched.writerow(['Input Image', 'Matched Images'])
        
        for img in input_images:
            matches = find_matches(img, catalog_image_data)
            if matches:
                 match_str = ', '.join(matches[:3])
                 row = [img, match_str]
                 writer_matched.writerow(row)
                 print(f"{img:<40} | {match_str}")
            else:
                 writer_unmatched.writerow([img])
                 print(f"{img:<40} | (No match found)")
                 
    print("\nUnmatched images saved to 'unmatched_results.csv'")
    print("Matched entries saved to 'matched_results.csv'")
    
if __name__ == '__main__':
    main()
