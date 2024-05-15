# Vertex AI Search Proxy

This project provides a simple FastAPI-based proxy for interacting with the Vertex AI Search service (previously known as Discovery Engine). It allows you to:

- Send search queries to a specified data store.
- Retrieve search results, including:
  - Document titles and links.
  - Snippets.
  - Answers.
  - Segments.
  - Metadata.
- Get a summarized overview of the search results.

## Getting Started

### Prerequisites

- **Google Cloud Project:** An active Google Cloud Project with the Vertex AI API enabled.
- **Vertex AI Search Data Store:** A configured data store within your project.
- **API Key:**  An API key for authentication.

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jorsj/vertex-ai-search-proxy.git
cd vertex-ai-search-proxy
```
2. Install the required Python libraries:
```bash
pip install -r requirements.txt 
```
3. Build the Docker image:
```bash
docker build -t vertex-ai-search-proxy . 
```

4. Set the environment variables:
```bash
export GOOGLE_CLOUD_PROJECT=<your_project_id>
export DATA_STORE_LOCATION=<your_data_store_region> # us, eu or global
export API_KEY=<your_api_key>
export PORT=<your_desired_port> # Example: 8000
```

5. Run the application:
```bash
docker run -d -p $PORT:$PORT -e GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT  -e DATA_STORE_LOCATION=$DATA_STORE_LOCATION  -e API_KEY=$API_KEY -e PORT=$PORT vertex-ai-search-proxy 
```

## Usage

The API proxy provides the following endpoint:

- **`/search/{data_store}` (POST):**  
  - Performs a search against the specified data store. 
  - Accepts request data in the following structure:
  ```json
  {
    "query": "your search query",
    "language_code": "en",
    "include_citations": true,                  // (Optional)
    "summary_result_count": 3,                  // (Optional)
    "return_extractive_segment_score": true,    // (Optional)
    "return_snippet": true,                     // (Optional)
    "ignore_adversarial_query": true,           // (Optional)
    "ignore_non_summary_seeking_query": true,   // (Optional)
    "max_extractive_answer_count": 3,           // (Optional)
    "max_extractive_segment_count": 3,          // (Optional)
    "num_previous_segments": 0,                 // (Optional)
    "num_next_segments": 0,                     // (Optional)
    "page_size": 3                              // (Optional)
  } 
  ```
- Returns a JSON response containing the search results and an optional summary.

### Example Request: 

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_api_key" \
     -d '{ "query": "example query", "language_code": "en" }' \
     http://localhost:8000/search/your_data_store_id
```

## Files

- **`app.py`:** The main FastAPI application.
- **`requirements.txt`:**  Lists the required Python packages for the project.
- **`Dockerfile`:**  Contains instructions for building the Docker image. 

## Notes

- Remember to create an API key in your Google Cloud project and configure it securely.
- This is a basic implementation, and you can extend it further based on your needs.
