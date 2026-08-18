from langchain_core.tools import tool
import logging
from langchain_community.tools.tavily_search import TavilySearchResults
import os

logger = logging.getLogger(__name__)

# Use Tavily Search
search = TavilySearchResults(max_results=3)

@tool
def search_web_general(query: str) -> str:
    """
    Search the broader web for information about Guru Nanak Dev Engineering College (GNDEC), Ludhiana. 
    Use this tool to confirm facts, find historical lists (like past principals), or get real-time info if RAG context lacks it.
    """
    logger.info(f"🕸️ [WEB SEARCH] Executing web search for: {query}")
    try:
        if not os.getenv("TAVILY_API_KEY"):
            return "Web search is disabled. Please set TAVILY_API_KEY."

        # Automatically append GNDEC context if missing to ensure relevant results
        if "gndec" not in query.lower() and "guru nanak" not in query.lower():
            query = f"Guru Nanak Dev Engineering College Ludhiana {query}"
            
        results = search.invoke(query)
        if not results:
            return "No recent results found on the web."
            
        # Tavily returns a list of dicts. We convert to a string.
        res_str = "\n".join([f"[{r.get('url', '')}]: {r.get('content', '')}" for r in results])
        logger.info(f"🕸️ [WEB SEARCH] Results: {res_str[:200]}...")
        return res_str
    except Exception as e:
        logger.error(f"Live search failed: {e}")
        return "Live search failed. Please rely on existing knowledge."
