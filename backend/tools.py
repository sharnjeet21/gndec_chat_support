from langchain_core.tools import tool
import logging
from langchain_community.tools import DuckDuckGoSearchRun

logger = logging.getLogger(__name__)
search = DuckDuckGoSearchRun()

@tool
def search_web_general(query: str) -> str:
    """
    Search the broader web for information about Guru Nanak Dev Engineering College (GNDEC), Ludhiana. 
    Use this tool to confirm facts, find historical lists (like past principals), or get real-time info if RAG context lacks it.
    """
    logger.info(f"🕸️ [WEB SEARCH] Executing web search for: {query}")
    try:
        # Automatically append GNDEC context if missing to ensure relevant results
        if "gndec" not in query.lower() and "guru nanak" not in query.lower():
            query = f"Guru Nanak Dev Engineering College Ludhiana {query}"
            
        results = search.invoke(query)
        if not results:
            return "No recent results found on the web."
            
        logger.info(f"🕸️ [WEB SEARCH] Results: {results[:200]}...")
        return results
    except Exception as e:
        logger.error(f"Live search failed: {e}")
        return "Live search failed. Please rely on existing knowledge."
