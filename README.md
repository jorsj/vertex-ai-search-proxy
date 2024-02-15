# Vertex AI Search Proxy

**Purpose:** This Python project builds a search API that interfaces with a configured Google Vertex AI Search data store. The core features of the project include:

-   **Enhanced Search**: Provides search results from the Vertex AI Search, enriched with elements like snippets, potential answers, answer segments, and summaries.
-   **Security:**  Implements API Key-based authentication to protect the search API endpoints.
-   **Flexible Content Delivery:**  Adapts to user-specified output paths and protocols for document links.
-   **Generative AI Functionality:**  Leverages Google Vertex AI Search and its advanced language capabilities to offer informative summaries and concise extractions.

**Key Components:**

-   **Google Vertex AI Search Libraries:**  Uses the  `google.cloud`  and  `google.api_core`  libraries to connect with the Google Vertex AI Search. These libraries manage the interactions essential for querying the configured data store.
-   **FastAPI:**  Provides the foundation for the web API framework, enabling RESTful endpoints for processing search requests and providing structured responses.
-   **Pydantic:**  Ensures data validation for incoming requests and outgoing responses, enforcing structure and type safety.
-   **Environment Variables:**  Employs environment variables to store sensitive information like API keys, the Google Cloud project ID, data store configuration, and settings for controlling summaries and extractions. This increases security and simplifies project configuration.

**Code Breakdown:**

1.  **Imports:**  Includes necessary libraries (FastAPI for web framework, security, Google Cloud/Discovery, etc.).
2.  **Environment Variables:**  Loads required configuration settings from environment variables.
3.  **Vertex AI Search Client:**  Instantiates a client for interacting with the Google Vertex AI Search service, establishing the connection.
4.  **API Key Authentication:**  Defines authentication logic to control access to API endpoints.
5.  **Data Models (Pydantic):**  Establishes 'Request', 'Response', and other data models, clarifying the expected structure of input and output.
6.  **Health Check Endpoint (`healthcheck`)**: A basic endpoint (`/healthcheck`) for quick status verification.
7.  **Search Endpoint (`/`)**:
    -   Handles incoming search requests.
    -   Constructs a detailed search query with advanced settings (snippets, extractive answers, query expansion, spell correction) for submission to the Vertex AI Search.
    -   Processes search results retrieved from the Vertex AI Search.
    -   Structures the search results, including additional details like snippets, extracted answers, extracted segments, and summaries.
    -   Formats the response, adhering to the defined data model.

Invoke will handle establishing local virtual environments, etc. Task definitions can be found in `tasks.py`.

**How to Use**

1. Set environment variables:
    ```bash
    export API_KEY=12345
    export DATA_STORE_LOCATION=us
    export GOOGLE_CLOUD_PROJECT=sandcastle-401718
    export DATA_STORE_ID=infofin_pdf_1703800611405
    export OUTPUT_PROTOCOL=HTTPS
    export OUTPUT_PATH_OVERRIDE=jasj.com/docs
    export PORT=8000
    export ENABLE_EXTRACTIVE_ANSWERS=TRUE
    export ENABLE_EXTRACTIVE_SEGMENTS=TRUE
    ```
2. Start the server with hot reload:
    ```bash
uvicorn app:app --reload
    ```

3.  **Send Requests:**  Send a POST request to the root endpoint (`/`), including:
    -   A valid API key in the  `X-API-Key`  header.
    -   Your search query in the  `query`  field of the JSON request body.

## Maintenance & Support

This repo performs basic periodic testing for maintenance. Please use the issue tracker for bug reports, features requests and submitting pull requests.

## Contributions

Please see the [contributing guidelines](CONTRIBUTING.md)

## License

This library is licensed under Apache 2.0. Full license text is available in [LICENSE](LICENSE).
