"""
Web Search Tool - Dynamic tool for web searching
Based on AIAvatarKit web_search_tool implementation
"""
import logging
import asyncio
from typing import Dict, Any
from ..base.tool_base import BaseTool, ToolMetadata, ToolType

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    """Tool for searching the web using DuckDuckGo"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="search_web",
            type=ToolType.DYNAMIC,
            description="Search the web for current information using DuckDuckGo",
            version="1.0.0"
        )
        super().__init__(metadata)
    
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web for information"""
        try:
            # Import duckduckgo_search locally to avoid dependency issues
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return {
                    "status": "error",
                    "error": "duckduckgo_search package not installed. Please install with: pip install duckduckgo_search",
                    "query": query
                }
            
            # Perform web search
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            if results:
                search_results = []
                for result in results:
                    search_results.append({
                        "title": result.get("title", ""),
                        "body": result.get("body", ""),
                        "href": result.get("href", "")
                    })
                
                return {
                    "status": "success",
                    "results": search_results,
                    "query": query,
                    "total_found": len(search_results)
                }
            else:
                return {
                    "status": "success",
                    "results": [],
                    "query": query,
                    "total_found": 0,
                    "message": "No search results found"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "query": query
            }
    
    def get_spec(self) -> Dict[str, Any]:
        """Get OpenAI function calling specification"""
        return {
            "name": "search_web",
            "description": "Search the web for current information and news using DuckDuckGo",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant web content"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        }