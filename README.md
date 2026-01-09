# Docker Hardened Image Search

A tool to fuzzy-match a list of image names against the [Docker Hardened Image (DHI) catalog](https://hub.docker.com/orgs/demonstrationorg/hardened-images/catalog).

## Features
- **Fuzzy Matching**: Uses `fuzzywuzzy` to find potential matches even with slight name variations (e.g., "PostgreSQL" -> "postgres").
- **Alias Support**: specifically handles known mapping like `.NET` -> `dotnet`.
- **CSV Export**: Outputs results to `matched_results.csv` and `unmatched_results.csv` files.
- **Stop Words**: Filters out common words (like `runtime`, `sdk`, `cli`, `agent`, etc.) from the core name to reduce false positives, while ensuring critical terms like `cli` and `sdk` are present if they appear in the input.



## How to Run

1. **Modify the input.txt file**

This file should contain a list of image names, one per line.Modify the file which is included in this repository.


2.  **Build the image**:
    ```bash
    docker build -t dhi-search .
    ```

3.  **Run the container**:
    ```bash
    # Run with credentials passed as environment variables
    docker run --rm \
      -e DOCKER_USERNAME="your_username" \
      -e DOCKER_PAT="your_pat" \
      dhi-search
    ```

    **Sample Output:**

    ```text
    Fetching Docker Hardened Image catalog...
    Authenticating with Docker Hub...
    Authentication successful.
    Fetching Docker Hardened Image catalog (via GraphQL)...

    Catalog Statistics:
      - IMAGE: 246
      - HELM_CHART: 28
      - Total: 274

    Matching Results:
    Input Image                              | Matched Images
    --------------------------------------------------------------------------------
    .NET Runtime                             | dotnet
    .NET SDK                                 | (No match found)
    7-Zip                                    | (No match found)
    A2A JS SDK                               | (No match found)
    Active Directory Authentication Library  | (No match found)
    Aiohttp                                  | (No match found)
    Alma Linux                               | (No match found)
    Amazon Corretto JDK                      | amazoncorretto
    Amazon Corretto JRE                      | amazoncorretto
    ```

4. **Manual Verification**

It is recommended to manually verify the results. The tool will output two CSV files: `matched_results.csv` and `unmatched_results.csv`. 
The `matched_results.csv` file will contain the list of images that were matched, and the `unmatched_results.csv` file will contain the list of images that were not matched.