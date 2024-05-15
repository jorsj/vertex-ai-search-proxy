import os
import uvicorn
import re
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional

from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.api_core.client_options import ClientOptions
from google.cloud import storage

api_keys = [
    os.environ["API_KEY"]
]

project = os.environ["GOOGLE_CLOUD_PROJECT"]
location = os.environ["DATA_STORE_LOCATION"]

client_options = (
    ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
    if location != "global"
    else None
)

search_client = discoveryengine.SearchServiceClient(
    client_options=client_options
)
storage_client = storage.Client()

# Initialize request argument(s)

app = FastAPI(docs_url=None, redoc_url=None)
api_key_header = APIKeyHeader(name="X-API-Key")


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    """Parses a Google Cloud Storage URI.

    Args:
        uri: The Google Cloud Storage URI to parse.

    Returns:
        A tuple containing the bucket name and object name.
    
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
        api_key_header: The API key value extracted from the request header 
                        using the 'api_key_header' Security dependency.

    Returns:
        The validated API key.

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
    """Represents a search request."""
    query: str
    include_citations: Optional[bool] = Field(default=False)
    language_code: str
    summary_result_count: Optional[int] = Field(default=3)
    return_extractive_segment_score: Optional[bool] = Field(default=True)
    return_snippet: Optional[bool] = Field(default=True)
    ignore_adversarial_query: Optional[bool] = Field(default=True)
    ignore_non_summary_seeking_query: Optional[bool] = Field(default=True)
    max_extractive_answer_count: Optional[int] = Field(default=3)
    max_extractive_segment_count: Optional[int] = Field(default=3)
    num_previous_segments: Optional[int] = Field(default=0)
    num_next_segments: Optional[int] = Field(default=0)
    page_size: Optional[int] = Field(default=3)

class ExtractiveAnswer (BaseModel):
    """Represents an extractive answer."""
    content: str | None = None
    page_number: int | None = None


class ExtractiveSegment (BaseModel):
    """Represents an extractive segment."""
    content: str | None = None
    page_number: int | None = None


class Metadata(BaseModel):
    """Represents a metadata key-value pair."""
    key: str | None
    value: str | None


class Document(BaseModel):
    """Represents a document in the search results."""
    title: str | None = None
    link: str | None = None
    snippets: list[str] | None = None
    extractive_answers: list[ExtractiveAnswer] | None = None
    extractive_segments: list[ExtractiveSegment] | None = None
    metadata: list[Metadata] | None


class Response(BaseModel):
    """Represents a search response."""
    summary: str | None = None
    documents: list[Document] | None = None


@app.get("/healthcheck")
async def healthcheck() -> str:
    """
    Provides a simple health check endpoint.

    Returns:
        str: The string "OK" to signal operational status.
    """
    return "OK"


def get_metadata(uri: str) -> list[Metadata]:
    """
    Extracts metadata from a Google Cloud Storage object.
    
    Args:
        uri: A Google Cloud Storage URI in the format "gs://bucket_name/object_name".

    Returns:
        A list of Metadata objects representing the object's metadata.

    Raises:
        ValueError: If the provided URI is not a valid Google Cloud Storage URI. 
        GoogleCloudError: If there is an error communicating with the Google Cloud Storage service.
    """
    metadata = []
    bucket_name, blob_name = parse_gcs_uri(uri)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)
    for key, value in zip(blob.metadata.keys(), blob.metadata.values()):
        metadata.append(Metadata(key=key, value=value))
    return metadata


def extract_snippets(result: dict) -> list[str]:
    """Extracts snippets from a search result.

    Args:
        result: A search result object.

    Returns:
        A list of snippets.
    """
    snippets = []
    for snippet in result.document.derived_struct_data["snippets"]:
        snippets.append(snippet["snippet"])
    return snippets


def extract_answers_segments(result: dict, field: str) -> list[ExtractiveAnswer] | list[ExtractiveSegment]:
    """Extracts extractive answers or segments from a search result.

    Args:
        result: A search result object.
        field: The field to extract, either "extractive_answers" or "extractive_segments".

    Returns:
        A list of ExtractiveAnswer or ExtractiveSegment objects.
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


@app.post("/search/{data_store}")
async def search(data_store: str, request: Request, api_key: str = Security(get_api_key)) -> Response:
    """Handles search requests.

    Args:
        data_store: The data store to search.
        request: The search request.
        api_key: The API key for authentication.

    Returns:
        The search response.
    """
    
    serving_config = search_client.serving_config_path(
        project=project,
        location=location,
        data_store=data_store,
        serving_config="default_config"
    )
    
    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        # For information about snippets, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/snippets
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=request.return_snippet
        ),
        # For information about search summaries, refer to:
        # https://cloud.google.com/generative-ai-app-builder/docs/get-search-summaries
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=request.summary_result_count,
            include_citations=request.include_citations,
            ignore_adversarial_query=request.ignore_adversarial_query,
            ignore_non_summary_seeking_query=request.ignore_non_summary_seeking_query,
            language_code=request.language_code,
            model_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(
                version="preview"
            )
        ),
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_answer_count=request.max_extractive_answer_count,
            max_extractive_segment_count=request.max_extractive_segment_count,
            return_extractive_segment_score=request.return_extractive_segment_score,
            num_previous_segments=request.num_previous_segments,
            num_next_segments=request.num_next_segments
        )
    )
    
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=request.query,
        page_size=request.page_size,
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
