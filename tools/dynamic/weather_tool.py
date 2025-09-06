"""
Weather Tool - Dynamic tool for weather information
Based on AIAvatarKit weather_tool implementation
"""
import logging
import requests
from typing import Dict, Any
from ..base.tool_base import BaseTool, ToolMetadata, ToolType

logger = logging.getLogger(__name__)

class WeatherTool(BaseTool):
    """Tool for getting weather information"""
    
    def __init__(self, http_session=None):
        metadata = ToolMetadata(
            name="get_weather",
            type=ToolType.DYNAMIC,
            description="Get current weather information for a specific location",
            version="1.0.0"
        )
        super().__init__(metadata)
    
    async def execute(self, location: str) -> Dict[str, Any]:
        """Get weather information for a location"""
        try:
            # Use synchronous requests to avoid event loop issues
            url = f"https://wttr.in/{location}?format=j1"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            weather_data = response.json()
            
            if "current_condition" in weather_data:
                current = weather_data["current_condition"][0]
                
                weather_info = {
                    "location": location,
                    "temperature": f"{current.get('temp_C', 'N/A')}°C",
                    "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                    "humidity": f"{current.get('humidity', 'N/A')}%",
                    "wind_speed": f"{current.get('windspeedKmph', 'N/A')} km/h",
                    "wind_direction": current.get('winddir16Point', 'N/A'),
                    "feels_like": f"{current.get('FeelsLikeC', 'N/A')}°C",
                    "visibility": f"{current.get('visibility', 'N/A')} km"
                }
                
                return {
                    "status": "success",
                    "weather": weather_info,
                    "location": location
                }
            else:
                return {
                    "status": "error",
                    "error": "Weather data not available for this location",
                    "location": location
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "location": location
            }
    
    def get_spec(self) -> Dict[str, Any]:
        """Get OpenAI function calling specification"""
        return {
            "name": "get_weather",
            "description": "Get current weather information for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name (city, country) for weather lookup"
                    }
                },
                "required": ["location"]
            }
        }