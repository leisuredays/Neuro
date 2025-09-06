"""
YouTube Tool - Dynamic tool for YouTube video search and playback
Based on weather_tool.py structure for consistency
"""
import logging
import webbrowser
import subprocess
import platform
import os
from typing import Dict, Any
from ..base.tool_base import BaseTool, ToolMetadata, ToolType

logger = logging.getLogger(__name__)

class YouTubeTool(BaseTool):
    """Tool for searching and playing YouTube videos"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="play_youtube_video",
            type=ToolType.DYNAMIC,
            description="Search and play videos on YouTube",
            version="1.0.0"
        )
        super().__init__(metadata)
    
    async def execute(self, query: str, action: str = "play") -> Dict[str, Any]:
        """Execute YouTube video search and play"""
        try:
            if not query or not isinstance(query, str) or len(query.strip()) == 0:
                return {
                    "status": "error",
                    "error": "No search query provided",
                    "query": query
                }
            
            query = query.strip()
            logger.info(f"YouTube tool called with: query='{query}', action='{action}'")
            
            # Create YouTube URL
            if action == "search":
                # Open search results page
                youtube_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                title = f"Search results for '{query}'"
            else:
                # Direct search URL (will show first result)
                youtube_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                title = f"Playing '{query}'"
            
            # Open browser (non-blocking)
            browser_success = self._open_browser(youtube_url)
            
            if browser_success:
                return {
                    "status": "success",
                    "action": action,
                    "title": title,
                    "url": youtube_url,
                    "query": query
                }
            else:
                return {
                    "status": "error", 
                    "error": "Could not open browser",
                    "query": query
                }
                
        except Exception as e:
            logger.error(f"YouTube tool error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "query": query
            }
    
    def _open_browser(self, url: str) -> bool:
        """Open browser with URL (non-blocking)"""
        try:
            system = platform.system().lower()
            is_wsl = os.path.exists('/mnt/c') and system == "linux"
            
            # Platform-specific browser opening
            if system == "windows" or is_wsl:
                if is_wsl:
                    # WSL: Use Windows start command
                    subprocess.Popen(["/mnt/c/Windows/System32/cmd.exe", "/c", "start", url],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
                else:
                    # Windows: Use os.startfile
                    import threading
                    threading.Thread(target=lambda: os.startfile(url), daemon=True).start()
                return True
                
            elif system == "darwin":  # macOS
                subprocess.Popen(["open", url], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
                return True
                
            elif system == "linux":
                subprocess.Popen(["xdg-open", url],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                               start_new_session=True)
                return True
            
            # Fallback: Python webbrowser
            webbrowser.open(url, new=2)
            return True
            
        except Exception as e:
            logger.error(f"Browser opening failed: {e}")
            try:
                # Final fallback
                webbrowser.open(url, new=2)
                return True
            except:
                return False
    
    def get_spec(self) -> Dict[str, Any]:
        """Get OpenAI function calling specification"""
        return {
            "name": "play_youtube_video",
            "description": "Search and play videos on YouTube",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Video title, keywords, or artist name to search for"
                    },
                    "action": {
                        "type": "string", 
                        "enum": ["search", "play"],
                        "description": "Action to perform: search (search only) or play (search and play, default)",
                        "default": "play"
                    }
                },
                "required": ["query"]
            }
        }