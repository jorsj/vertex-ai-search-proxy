# Vertex AI Search Proxy

This project provides a FastAPI-based proxy for interacting with Agent Builder Search (formerly Discovery Engine). It enables you to perform searches on your data store, retrieve documents, snippets, and summaries.

## Features

- Search a specified Agent Builder Search data store.
- Retrieve document details, including title, link, and snippets.
- Get extractive answers and segments.
- Extract metadata from documents stored in Google Cloud Storage.
- Obtain a search summary.
- Basic health check endpoint.

## Requirements

- Python 3.7+
- Virtual environment (recommended)

## Installation

1. Clone the repository:

```bash
  git clone https://github.com/jorsj/vertex-ai-search-proxy.git
```

2. Navigate to the project directory:

```bash
  cd vertex-ai-search-proxy
```

3. Create and activate a virtual environment (optional but recommended):

```bash
  python3 -m venv env
  source env/bin/activate
```

4. Install the required packages:

```bash
  pip install -r requirements.txt
```

## Configuration

1. Set up environment variables (in a `.env` file or directly):
  - `API_KEY`: Your API key for authentication.
  - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID.
  - `DATA_STORE_LOCATION`: The location of your Agent Builder Search data store (e.g., 'us-central1').
  - `ENABLE_EXTRACTIVE_ANSWERS`: Set to "true" to enable extractive answers (default: "false").
  - `ENABLE_EXTRACTIVE_SEGMENTS`: Set to "true" to enable extractive segments (default: "false").
  - `PORT`: The port the application will run on (default: 8000).

2.  Build the Docker image:

```bash
  docker build -t vertex-ai-search-proxy .
```

## Running the Application

1.  Run the application using Docker:

```bash
  docker run -p 8000:8000 -e API_KEY=your_api_key -e GOOGLE_CLOUD_PROJECT=your_project_id -e DATA_STORE_LOCATION=your_data_store_location vertex-ai-search-proxy 
```

  Replace `your_api_key`, `your_project_id`, and `your_data_store_location` with your actual values.

2.   Alternatively, run the application directly:
```bash
  uvicorn app:app --reload
```

## Usage

Once the application is running, you can send POST requests to the `/search/{data_store}` endpoint. The `{data_store}` placeholder represents the ID of your Agent Builder Search data store. 

**Request Body:**

```json
{
"query": "your search query"
}
```

**Headers:**

- `X-API-Key`: Your API key.

**Example:**

```bash
curl -X POST -H "X-API-Key: your_api_key" -H "Content-Type: application/json" -d '{"query": "example query"}' http://localhost:8000/search/your_data_store_id 
```

The API will return a JSON response containing the search results, including documents, snippets, summaries, and other relevant information. 

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 