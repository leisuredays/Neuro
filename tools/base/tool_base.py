"""
Base tool classes and interfaces
Based on AIAvatarKit mixed_tools_server tool architecture
"""
import time
import logging
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Awaitable

logger = logging.getLogger(__name__)

class ToolType(Enum):
    STATIC = "static"           # 항상 사용 가능 (예: 메모리 검색)
    DYNAMIC = "dynamic"         # 상황별 로드 (예: 날씨, 웹검색)

class ToolStatus(Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    EXECUTING = "executing"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class ToolExecutionStatus:
    """Real-time tool execution status"""
    is_running: bool = False
    progress: float = 0.0
    current_step: Optional[str] = None
    start_time: Optional[float] = None
    estimated_completion: Optional[float] = None
    user_request: Optional[str] = None
    
@dataclass
class ToolMetadata:
    name: str
    type: ToolType
    description: str
    version: str = "1.0.0"
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ToolStatus = ToolStatus.AVAILABLE
    last_used: Optional[float] = None
    usage_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0
    execution_status: ToolExecutionStatus = field(default_factory=ToolExecutionStatus)

class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
        self._performance_history = []
        self._progress_callback: Optional[Callable[[str], Awaitable[None]]] = None
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Tool execution logic - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_spec(self) -> Dict[str, Any]:
        """Get tool specification in OpenAI function calling format"""
        pass
    
    def get_instruction(self) -> str:
        """Get tool usage instruction"""
        return self.metadata.description
    
    async def execute_with_monitoring(self, user_request: str = "", **kwargs) -> Dict[str, Any]:
        """Execute tool with performance monitoring and real-time status updates"""
        start_time = time.time()
        
        try:
            # Initialize execution status
            self.metadata.execution_status.is_running = True
            self.metadata.execution_status.start_time = start_time
            self.metadata.execution_status.user_request = user_request
            self.metadata.execution_status.progress = 0.0
            self.metadata.execution_status.current_step = "초기화 중..."
            
            # Estimate completion time based on average response time
            if self.metadata.average_response_time > 0:
                self.metadata.execution_status.estimated_completion = start_time + self.metadata.average_response_time
            else:
                self.metadata.execution_status.estimated_completion = start_time + 3.0  # Default 3 seconds
            
            # Update usage stats
            self.metadata.usage_count += 1
            self.metadata.last_used = start_time
            self.metadata.status = ToolStatus.EXECUTING
            
            # Update progress: Starting execution
            self.metadata.execution_status.progress = 0.2
            self.metadata.execution_status.current_step = f"{self.metadata.name} 실행 중..."
            
            if self._progress_callback:
                await self._progress_callback(f"Executing {self.metadata.name}...")
            
            # Execute tool
            result = await self.execute(**kwargs)
            
            # Update performance metrics
            execution_time = time.time() - start_time
            self._performance_history.append(execution_time)
            
            # Calculate average response time
            if self._performance_history:
                self.metadata.average_response_time = sum(self._performance_history) / len(self._performance_history)
            
            # Keep only recent performance history
            if len(self._performance_history) > 50:
                self._performance_history = self._performance_history[-50:]
            
            # Finalize execution status
            self.metadata.execution_status.progress = 1.0
            self.metadata.execution_status.current_step = "완료"
            self.metadata.execution_status.is_running = False
            self.metadata.status = ToolStatus.AVAILABLE
            
            if self._progress_callback:
                await self._progress_callback(f"{self.metadata.name} completed successfully")
            
            logger.info(f"Tool {self.metadata.name} executed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            # Update error stats
            self.metadata.error_count += 1
            self.metadata.status = ToolStatus.ERROR
            
            # Update execution status for error
            self.metadata.execution_status.is_running = False
            self.metadata.execution_status.current_step = f"오류: {str(e)}"
            self.metadata.execution_status.progress = 0.0
            
            error_result = {
                "error": str(e),
                "tool_name": self.metadata.name,
                "execution_time": time.time() - start_time
            }
            
            if self._progress_callback:
                await self._progress_callback(f"Error in {self.metadata.name}: {str(e)}")
            
            logger.error(f"Tool {self.metadata.name} failed: {e}")
            return error_result
    
    def set_progress_callback(self, callback: Callable[[str], Awaitable[None]]):
        """Set progress callback for real-time updates"""
        self._progress_callback = callback
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        status = self.metadata.execution_status
        return {
            "tool_name": self.metadata.name,
            "is_running": status.is_running,
            "progress": status.progress,
            "current_step": status.current_step,
            "user_request": status.user_request,
            "elapsed_time": time.time() - status.start_time if status.start_time else 0.0,
            "estimated_completion": status.estimated_completion,
            "status": self.metadata.status.value
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tool performance metrics"""
        return {
            "usage_count": self.metadata.usage_count,
            "error_count": self.metadata.error_count,
            "error_rate": self.metadata.error_count / max(self.metadata.usage_count, 1),
            "average_response_time": self.metadata.average_response_time,
            "last_used": self.metadata.last_used,
            "status": self.metadata.status.value,
            "execution_status": self.get_execution_status()
        }
    
    def reset_metrics(self):
        """Reset tool metrics"""
        self.metadata.usage_count = 0
        self.metadata.error_count = 0
        self.metadata.average_response_time = 0.0
        self.metadata.last_used = None
        self._performance_history = []