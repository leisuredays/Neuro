"""
Tool Registry - Centralized tool management system
Based on AIAvatarKit mixed_tools_server tool registry
"""
import logging
from typing import Dict, List, Optional, Any
from ..base.tool_base import BaseTool, ToolType, ToolStatus

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Centralized registry for managing all tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tool_groups: Dict[str, List[str]] = {}
    
    def register_tool(self, tool: BaseTool, group: str = "default") -> bool:
        """Register a tool in the registry"""
        try:
            tool_name = tool.metadata.name
            
            # Check if tool already exists
            if tool_name in self.tools:
                logger.warning(f"Tool {tool_name} already registered, replacing...")
            
            # Register the tool
            self.tools[tool_name] = tool
            
            # Add to group
            if group not in self.tool_groups:
                self.tool_groups[group] = []
            if tool_name not in self.tool_groups[group]:
                self.tool_groups[group].append(tool_name)
            
            logger.info(f"Tool {tool_name} registered successfully in group '{group}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool.metadata.name}: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool from the registry"""
        try:
            if tool_name not in self.tools:
                logger.warning(f"Tool {tool_name} not found in registry")
                return False
            
            # Remove from tools
            del self.tools[tool_name]
            
            # Remove from groups
            for group_name, tool_list in self.tool_groups.items():
                if tool_name in tool_list:
                    tool_list.remove(tool_name)
            
            logger.info(f"Tool {tool_name} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister tool {tool_name}: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def get_tools_by_type(self, tool_type: ToolType) -> List[BaseTool]:
        """Get all tools of a specific type"""
        return [tool for tool in self.tools.values() if tool.metadata.type == tool_type]
    
    def get_tools_by_group(self, group: str) -> List[BaseTool]:
        """Get all tools in a specific group"""
        if group not in self.tool_groups:
            return []
        
        tools = []
        for tool_name in self.tool_groups[group]:
            if tool_name in self.tools:
                tools.append(self.tools[tool_name])
        return tools
    
    def get_available_tools(self, tool_type: Optional[ToolType] = None) -> List[BaseTool]:
        """Get list of available tools"""
        available = []
        for name, tool in self.tools.items():
            if tool.metadata.status in [ToolStatus.AVAILABLE, ToolStatus.EXECUTING]:
                if tool_type is None or tool.metadata.type == tool_type:
                    available.append(tool)
        return available
    
    def get_running_tools(self) -> List[Dict[str, Any]]:
        """Get currently running tools with their status"""
        running_tools = []
        for tool in self.tools.values():
            if tool.metadata.execution_status.is_running:
                running_tools.append(tool.get_execution_status())
        return running_tools
    
    def get_tool_specs(self, tool_type: Optional[ToolType] = None) -> List[Dict[str, Any]]:
        """Get tool specifications for LLM"""
        specs = []
        for tool in self.tools.values():
            if tool.metadata.status == ToolStatus.AVAILABLE:
                if tool_type is None or tool.metadata.type == tool_type:
                    specs.append(tool.get_spec())
        return specs
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status and statistics"""
        total_tools = len(self.tools)
        available_tools = len([t for t in self.tools.values() if t.metadata.status == ToolStatus.AVAILABLE])
        static_tools = len([t for t in self.tools.values() if t.metadata.type == ToolType.STATIC])
        dynamic_tools = len([t for t in self.tools.values() if t.metadata.type == ToolType.DYNAMIC])
        
        return {
            "total_tools": total_tools,
            "available_tools": available_tools,
            "static_tools": static_tools,
            "dynamic_tools": dynamic_tools,
            "groups": list(self.tool_groups.keys()),
            "tool_health": self._get_health_summary()
        }
    
    def get_tool_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all tools"""
        metrics = {}
        for name, tool in self.tools.items():
            metrics[name] = tool.get_metrics()
        return metrics
    
    def reset_all_metrics(self):
        """Reset metrics for all tools"""
        for tool in self.tools.values():
            tool.reset_metrics()
        logger.info("All tool metrics reset")
    
    def _get_health_summary(self) -> Dict[str, int]:
        """Get health summary of all tools"""
        health_counts = {
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0
        }
        
        for tool in self.tools.values():
            if tool.metadata.status == ToolStatus.ERROR:
                health_counts["unhealthy"] += 1
            elif tool.metadata.error_count > tool.metadata.usage_count * 0.1:  # 10% error rate
                health_counts["degraded"] += 1
            else:
                health_counts["healthy"] += 1
        
        return health_counts
    
    def list_tools(self, verbose: bool = False) -> List[Dict[str, Any]]:
        """List all registered tools"""
        tool_list = []
        for name, tool in self.tools.items():
            tool_info = {
                "name": name,
                "type": tool.metadata.type.value,
                "status": tool.metadata.status.value,
                "description": tool.metadata.description
            }
            
            if verbose:
                tool_info.update({
                    "version": tool.metadata.version,
                    "usage_count": tool.metadata.usage_count,
                    "error_count": tool.metadata.error_count,
                    "average_response_time": tool.metadata.average_response_time,
                    "last_used": tool.metadata.last_used
                })
            
            tool_list.append(tool_info)
        
        return tool_list

# Global registry instance
_global_registry: Optional[ToolRegistry] = None

def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry

def register_tool(tool: BaseTool, group: str = "default") -> bool:
    """Register a tool in the global registry"""
    return get_global_registry().register_tool(tool, group)

def get_tool(tool_name: str) -> Optional[BaseTool]:
    """Get a tool from the global registry"""
    return get_global_registry().get_tool(tool_name)