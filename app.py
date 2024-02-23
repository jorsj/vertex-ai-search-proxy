import os
import uvicorn
import re
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.api_core.client_options import ClientOptions
from google.cloud import storage

api_keys = [
    os.environ["API_KEY"]
]

project = os.environ["GOOGLE_CLOUD_PROJECT"]
location = os.environ["DATA_STORE_LOCATION"]
data_store = os.environ["DATA_STORE_ID"]

try:
    enable_extractive_answers = os.environ["ENABLE_EXTRACTIVE_ANSWERS"].lower(
    ) == "true"
except:
    enable_extractive_answers = False

try:
    enable_extractive_segments = os.environ["ENABLE_EXTRACTIVE_SEGMENTS"].lower(
    ) == "true"
except:
    enable_extractive_segments = False

client_options = (
    ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
    if location != "global"
    else None
)

search_client = discoveryengine.SearchServiceClient(
    client_options=client_options)
storage_client = storage.Client()

# Initialize request argument(s)

serving_config = search_client.serving_config_path(
    project=project,
    location=location,
    data_store=data_store,
    serving_config="default_config"
)

max_extractive_answer_count = 5*int(enable_extractive_answers)
max_extractive_segment_count = 5*int(enable_extractive_segments)


content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
    # For information about snippets, refer to:
    # https://cloud.google.com/generative-ai-app-builder/docs/snippets
    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
        return_snippet=True
    ),
    # For information about search summaries, refer to:
    # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
    summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
        summary_result_count=5,
        include_citations=False,
        ignore_adversarial_query=True,
        ignore_non_summary_seeking_query=True,
        language_code="es",
        model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
            version="preview"
        )
    ),
    extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_answer_count=5*int(enable_extractive_answers),
        max_extractive_segment_count=5*int(enable_extractive_segments),
        return_extractive_segment_score=True,
        num_previous_segments=0,
        num_next_segments=0
    )
)

app = FastAPI(docs_url=None, redoc_url=None)
api_key_header = APIKeyHeader(name="X-API-Key")


def parse_gcs_uri(uri):
    """Parses a Google Cloud Storage URI and returns the bucket and name.

    Args:
      uri: The Google Cloud Storage URI to parse.

    Returns:
      A tuple of (bucket, name), where bucket is the name of the bucket and name is
      the name of the object within the bucket.

    Raises:
      ValueError: If the URI is not a valid Google Cloud Storage URI.
    """

    match = re.match(r"^gs://(?P<bucket>[^/]+)/(?P<name>.*)$", uri)
    if not match:
        raise ValueError("Invalid Google Cloud Storage URI: {}".format(uri))
    return match.group("bucket"), match.group("name")


def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """Validates an API key provided in a request header.

    Args:
        api_key_header (str): The API key value extracted from the request header 
                              (using the 'api_key_header' Security dependency).

    Returns:
        str: The validated API key.

    Raises:
        HTTPException: If the provided API key is invalid or missing, with a 
                       status code of 401 (Unauthorized).
    """
    if api_key_header in api_keys:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )


class Request(BaseModel):
    query: str


class ExtractiveAnswer (BaseModel):
    content: str | None = None
    page_number: int | None = None


class ExtractiveSegment (BaseModel):
    content: str | None = None
    page_number: int | None = None


class Metadata(BaseModel):
    key: str | None
    value: str | None


class Document(BaseModel):
    title: str | None = None
    link: str | None = None
    snippets: list[str] | None = None
    extractive_answers: list[ExtractiveAnswer] | None = None
    extractive_segments: list[ExtractiveSegment] | None = None
    metadata: list[Metadata] | None


class Response(BaseModel):
    summary: str | None = None
    documents: list[Document] | None = None


@app.get("/healthcheck")
async def healthcheck() -> str:
    """
    Provides a simple health check endpoint.

    This asynchronous function is intended for basic status checks within a 
    web application or service.

    Returns:
        str: The string "OK" to signal operational status.
    """
    return "OK"


def get_metadata(uri) -> list[Metadata]:
    """
    Extracts metadata from a Google Cloud Storage object and returns it as a list of Metadata objects.

    Args:
        uri (str):  A Google Cloud Storage URI in the format "gs://bucket_name/object_name"

    Returns:
        list[Metadata]: A list of Metadata objects, where each object represents a single key-value 
                        pair of the object's metadata.

    Raises:
        ValueError: If the provided URI is not a valid Google Cloud Storage URI. 
        GoogleCloudError: If there is an error communicating with the Google Cloud Storage service.
    
    Example:
        >>> uri = "gs://my-bucket/data.csv"
        >>> metadata_list = get_metadata(uri)
        >>> for item in metadata_list:
        ...     print(item.key, item.value)
        ...
        content-type text/csv
        cache-control no-cache
        ... 
    """
    metadata = []
    bucket_name, blob_name = parse_gcs_uri(uri)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)
    for key, value in zip(blob.metadata.keys(), blob.metadata.values()):
        metadata.append(Metadata(key=key, value=value))
    return metadata


def extract_snippets(result) -> list[str]:
    """Extracts snippets from a given result object.

    Args:
        result: A JSON object containing the data to extract snippets from.
                Assumes the 'result' object has a specific nested structure:
                    result.document.derived_struct_data["snippets"]

    Returns:
        list[str]: A list of strings, where each string is a snippet extracted 
                   from the result.
    """
    snippets = []
    for snippet in result.document.derived_struct_data["snippets"]:
        snippets.append(snippet["snippet"])
    return snippets


def extract_answers_segments(result, field: str) -> list[ExtractiveAnswer] | list[ExtractiveSegment]:
    """Processes extractions from a result object, handling potential missing fields.

    Args:
        result: A JSON object containing data with a specific nested structure:
                result.document.derived_struct_data[field]
        field (str): The name of the field within 'derived_struct_data' to process.
                     Determines the type of object to create (ExtractiveAnswer or ExtractiveSegment).

    Returns:
        list: A list of either ExtractiveAnswer or ExtractiveSegment objects, 
              populated with data from the extractions.
    """
    response = []
    for extraction in result.document.derived_struct_data[field]:
        try:
            content = extraction["content"]
        except:
            content = None
        try:
            page_number = extraction["pageNumber"]
        except:
            page_number = None

        item = ExtractiveAnswer(content=content, page_number=page_number) if field == "extractive_answers" else ExtractiveSegment(
            content=content, page_number=page_number)

        response.append(item)

    return response


@app.post("/")
async def search(request: Request, api_key: str = Security(get_api_key)) -> Response:
    """Handles search requests for the application.

    Args:
        request (Request): Contains the incoming search query and other request data.
        api_key (str):  An API key for authentication (retrieved using the get_api_key function).

    Returns:
        Response: A structured response object containing:
            * summary (str): An optional summary of the search results (if available).
            * documents (list):  A list of Document objects representing search results. 
    """
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=request.query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )
    pager = search_client.search(request)

    documents = []
    for result in pager.results:
        try:
            title = result.document.derived_struct_data["title"]
        except:
            title = None
        try:
            link = result.document.derived_struct_data["link"]
        except:
            link = None
        try:
            snippets = extract_snippets(result)
        except:
            snippets = None
        try:
            extractive_answers = extract_answers_segments(
                result, "extractive_answers")
        except:
            extractive_answers = None
        try:
            extractive_segments = extract_answers_segments(
                result, "extractive_segments")
        except:
            extractive_segments = None
        try:
            metadata = get_metadata(link)
        except:
            metadata = None

        document = Document(
            title=title,
            link=link,
            snippets=snippets,
            extractive_answers=extractive_answers,
            extractive_segments=extractive_segments,
            metadata=metadata
        )

        documents.append(document)

    try:
        summary = pager.summary.summary_text
    except:
        summary = None

    response = Response(
        summary=summary,
        documents=documents
    )
    return response

if __name__ == "__main__":
    port = int(os.environ["PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port)
