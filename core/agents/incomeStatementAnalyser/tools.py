import requests
from core.settings import settings
from pydantic import BaseModel
from pydantic_ai import Tool
from typing import List


# Define Pydantic models for the web search response
class Profile(BaseModel):
    name: str
    url: str
    long_name: str
    img: str


class Result(BaseModel):
    title: str
    url: str
    is_source_local: bool
    is_source_both: bool
    description: str
    profile: Profile


class WebSearch(BaseModel):
    type: str
    results: List[Result]


class SearchResponse(BaseModel):
    type: str
    web: WebSearch


def current_time() -> str:
    """Get the current time in HH:MM:SS format.

    Returns:
        str: current time as a string
    """
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


def web_search(query: str) -> dict:
    """Search the web for relevant information to answer user questions

    Args:
        query (str): The search query

    Returns:
        str: _search results
    """

    response: SearchResponse = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={
            "X-Subscription-Token": settings.requrv_brave_api_key,
        },
        params={
            "q": query,
            "count": 5,
            "country": "it",
            "search_lang": "it",
        },
    ).json()

    return response.model_dump().get("web", {}).get("results", [])


custom_tools = [Tool(current_time), Tool(web_search)]
