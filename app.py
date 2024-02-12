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

print(path, protocol)

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


class Document(BaseModel):
    title: str
    link: str
    snippets: list[str]


class Response(BaseModel):
    summary: str | None = None
    documents: list[Document] | None = None


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

        document = Document(
            title=title,
            link=link,
            snippets=snippets
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
