# Docker Hardened Image Search

A tool to fuzzy-match a list of image names against the [Docker Hardened Image (DHI) catalog](https://hub.docker.com/orgs/demonstrationorg/hardened-images/catalog).

## Features
- **Fuzzy Matching**: Uses `fuzzywuzzy` to find potential matches even with slight name variations (e.g., "PostgreSQL" -> "postgres").
- **Alias Support**: specifically handles known mapping like `.NET` -> `dotnet`.
- **CSV Export**: Outputs results to `matched_results.csv` and `unmatched_results.csv` files.



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

4. **Manual Verification**

It