import os
import uvicorn
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from google.cloud import discoveryengine
from google.api_core.client_options import ClientOptions


api_keys = [
    os.environ["API_KEY"]
]

project = os.environ["GOOGLE_CLOUD_PROJECT"]
location = os.environ["DATA_STORE_LOCATION"]
data_store = os.environ["DATA_STORE_ID"]

try:
    path = os.environ["OUTPUT_PATH_OVERRIDE"]
except:
    path = ""

try:
    protocol = os.environ["OUTPUT_PROTOCOL"].lower()
except:
    protocol = "gs"

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

client = discoveryengine.SearchServiceClient(client_options=client_options)

# Initialize request argument(s)

serving_config = client.serving_config_path(
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
        include_citations=True,
        ignore_adversarial_query=True,
        ignore_non_summary_seeking_query=True,
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


def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
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


class Document(BaseModel):
    title: str | None = None
    link: str | None = None
    snippets: list[str] | None = None
    extractive_answers: list[ExtractiveAnswer] | None = None
    extractive_segments: list[ExtractiveSegment] | None = None


class Response(BaseModel):
    summary: str | None = None
    documents: list[Document] | None = None


@app.get("/healthcheck")
async def healthcheck() -> str:
    return "OK"


@app.post("/")
async def search(request: Request, api_key: str = Security(get_api_key)) -> Response:

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
    pager = client.search(request)

    documents = []
    for result in pager.results:
        try:
            title = result.document.derived_struct_data["title"]
        except:
            title = None
        try:
            if path != "":
                print()
                link = os.path.join(
                    f"{protocol}://",
                    path,
                    os.path.basename(
                        result.document.derived_struct_data["link"])
                )
            else:
                link = result.document.derived_struct_data["link"]
        except:
            link = None
        try:
            snippets = [snippet["snippet"]
                        for snippet in result.document.derived_struct_data["snippets"]]
        except:
            snippets = None
        try:
            extractive_answers = [
                ExtractiveAnswer(
                    content=extractive_answer["content"],
                    page_number=extractive_answer["pageNumber"]
                )
                for extractive_answer in result.document.derived_struct_data["extractive_answers"]
            ]
        except:
            extractive_answers = None

        try:
            extractive_segments = [
                ExtractiveSegment(
                    content=extractive_segment["content"],
                    page_number=extractive_segment["pageNumber"]
                )
                for extractive_segment in result.document.derived_struct_data["extractive_segments"]
            ]
        except:
            extractive_segments = None

        document = Document(
            title=title,
            link=link,
            snippets=snippets,
            extractive_answers=extractive_answers,
            extractive_segments=extractive_segments
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
