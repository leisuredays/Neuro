#!/usr/bin/env python3
"""
Neuro Dynamic Tool System - AIAvatarKit 스타일 통합 동적 도구 시스템
기존 Neuro 프로젝트와 완전 호환되는 Dynamic Tool 메인 컨트롤러
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Neuro 기존 시스템
from modules.memory import Memory

# 새로운 Dynamic Tool 시스템
from .registry.tool_registry import ToolRegistry, get_global_registry
from .dynamic_tool_manager import DynamicToolManager, ToolSelectionContext, SelectionStrategy
from .luna_tool_integration import LunaToolIntegrator, LunaPersonalityManager
from .tool_vectorizer import ToolVectorizer

# 기본 도구들
from .dynamic.math_tool import MathTool
from .dynamic.weather_tool import WeatherTool
from .dynamic.web_search_tool import WebSearchTool
from .dynamic.youtube_tool import YouTubeTool

# Constants import
from constants import CHROMA_TOOLS_DB_PATH

logger = logging.getLogger(__name__)

class NeuroDynamicSystem:
    """Neuro Dynamic Tool 통합 시스템"""
    
    def __init__(self, signals=None, chroma_path: str = CHROMA_TOOLS_DB_PATH, 
                 enabled: bool = True):
        self.signals = signals
        self.enabled = enabled
        self.chroma_path = Path(chroma_path)
        
        # 핵심 컴포넌트들
        self.registry = get_global_registry()
        self.tool_manager = None
        self.tool_vectorizer = None
        self.luna_integrator = None
        
        # 기존 메모리 시스템과의 연동
        self.memory_system = None
        
        # 시스템 상태
        self.is_initialized = False
        self.initialization_error = None
        
        # 성능 메트릭
        self.system_metrics = {
            "initialization_time": 0.0,
            "total_requests": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "average_response_time": 0.0
        }
    
    async def initialize(self) -> bool:
        """시스템 전체 초기화"""
        if self.is_initialized:
            return True
        
        start_time = time.time()
        
        try:
            logger.info("Initializing Neuro Dynamic Tool System...")
            
            # 1단계: 기본 도구들 등록
            await self._register_default_tools()
            
            # 2단계: 핵심 컴포넌트 초기화
            await self._initialize_core_components()
            
            # 3단계: 도구 벡터화
            await self._setup_tool_vectors()
            
            # 4단계: 기존 시스템과 연동
            await self._integrate_with_existing_system()
            
            # 초기화 완료
            self.is_initialized = True
            initialization_time = time.time() - start_time
            self.system_metrics["initialization_time"] = initialization_time
            
            logger.info(f"Neuro Dynamic Tool System initialized successfully in {initialization_time:.3f}s")
            return True
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"System initialization failed: {e}")
            return False
    
    async def _register_default_tools(self):
        """기본 도구들 등록"""
        logger.info("Registering default tools...")
        
        # 수학 도구
        math_tool = MathTool()
        self.registry.register_tool(math_tool, "computation")
        
        # 날씨 도구 (HTTP 세션은 나중에 설정)
        weather_tool = WeatherTool()
        self.registry.register_tool(weather_tool, "information")
        
        # 웹 검색 도구
        web_search_tool = WebSearchTool()
        self.registry.register_tool(web_search_tool, "information")
        
        # YouTube 도구
        youtube_tool = YouTubeTool()
        self.registry.register_tool(youtube_tool, "entertainment")
        
        # 메모리 도구는 기존 시스템과 연동 (나중에 추가 구현)
        
        logger.info(f"Registered {len(self.registry.tools)} tools")
    
    async def _initialize_core_components(self):
        """핵심 컴포넌트들 초기화"""
        logger.info("Initializing core components...")
        
        # ChromaDB 클라이언트 초기화
        try:
            import chromadb
            chroma_client = chromadb.PersistentClient(path=str(self.chroma_path))
        except ImportError:
            logger.warning("ChromaDB not available, using keyword-only selection")
            chroma_client = None
        
        # Dynamic Tool Manager
        self.tool_manager = DynamicToolManager(
            registry=self.registry,
            chroma_client=chroma_client
        )
        
        # Tool Vectorizer
        if chroma_client:
            self.tool_vectorizer = ToolVectorizer(
                chroma_path=str(self.chroma_path),
                registry=self.registry
            )
        
        # Luna Integrator
        personality_manager = LunaPersonalityManager()
        self.luna_integrator = LunaToolIntegrator(
            tool_manager=self.tool_manager,
            personality_manager=personality_manager
        )
        
        logger.info("Core components initialized")
    
    async def _setup_tool_vectors(self):
        """도구 벡터화 설정"""
        if not self.tool_vectorizer:
            logger.info("Tool vectorization skipped (ChromaDB not available)")
            return
        
        logger.info("Setting up tool vectors...")
        
        # 도구 벡터화 실행
        success = await self.tool_vectorizer.vectorize_all_tools()
        if success:
            logger.info("Tool vectorization completed")
        else:
            logger.warning("Tool vectorization failed, falling back to keyword-only")
    
    async def _integrate_with_existing_system(self):
        """기존 Neuro 시스템과 연동"""
        if not self.signals:
            logger.info("No signals provided, skipping existing system integration")
            return
        
        logger.info("Integrating with existing Neuro system...")
        
        # 기존 메모리 시스템 연동
        try:
            self.memory_system = Memory(self.signals, enabled=True)
            logger.info("Memory system integration completed")
        except Exception as e:
            logger.error(f"Memory system integration failed: {e}")
    
    async def process_user_request(self, user_input: str, user_id: str = "default",
                                 session_id: str = "default", 
                                 conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """사용자 요청 처리 - 메인 진입점"""
        
        if not self.is_initialized:
            return {
                "success": False,
                "error": "System not initialized",
                "initialization_error": self.initialization_error
            }
        
        start_time = time.time()
        self.system_metrics["total_requests"] += 1
        
        try:
            # Luna 통합 시스템으로 요청 처리
            result = await self.luna_integrator.process_user_input(
                user_input=user_input,
                conversation_history=conversation_history or [],
                user_id=user_id,
                session_id=session_id
            )
            
            # 성공 통계 업데이트
            if result.get("success", False):
                self.system_metrics["successful_responses"] += 1
            else:
                self.system_metrics["failed_responses"] += 1
            
            # 응답 시간 통계
            response_time = time.time() - start_time
            self._update_response_time_stats(response_time)
            
            # 추가 시스템 정보 포함
            result.update({
                "system_info": {
                    "dynamic_system_enabled": self.enabled,
                    "vectorization_available": self.tool_vectorizer is not None,
                    "memory_integration": self.memory_system is not None,
                    "response_time": response_time
                }
            })
            
            return result
            
        except Exception as e:
            self.system_metrics["failed_responses"] += 1
            logger.error(f"Request processing failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "luna_response": {
                    "response_text": "어... 뭔가 문제가 생긴 것 같아. 다시 말해줄래?",
                    "used_tools": [],
                    "tool_results": {},
                    "execution_time": time.time() - start_time,
                    "luna_mood": "confused"
                }
            }
    
    def _update_response_time_stats(self, response_time: float):
        """응답 시간 통계 업데이트"""
        total = self.system_metrics["total_requests"]
        current_avg = self.system_metrics["average_response_time"]
        
        # 이동 평균 계산
        self.system_metrics["average_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """시스템 전체 상태 조회"""
        status = {
            "system_info": {
                "initialized": self.is_initialized,
                "enabled": self.enabled,
                "initialization_error": self.initialization_error,
                "chroma_path": str(self.chroma_path)
            },
            "metrics": self.system_metrics.copy(),
            "components": {
                "tool_registry": self.registry.get_registry_status() if self.registry else None,
                "tool_manager": self.tool_manager.get_selection_metrics() if self.tool_manager else None,
                "luna_integrator": self.luna_integrator.get_integration_stats() if self.luna_integrator else None,
                "tool_vectorizer": self.tool_vectorizer.get_vectorization_status() if self.tool_vectorizer else None
            }
        }
        
        return status
    
    async def add_custom_tool(self, tool_instance, group: str = "custom") -> bool:
        """사용자 정의 도구 추가"""
        try:
            # 도구 등록
            success = self.registry.register_tool(tool_instance, group)
            
            if success and self.tool_vectorizer:
                # 벡터화 업데이트
                await self.tool_vectorizer.update_tool_vector(tool_instance.metadata.name)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add custom tool: {e}")
            return False
    
    async def remove_tool(self, tool_name: str) -> bool:
        """도구 제거"""
        try:
            # 레지스트리에서 제거
            success = self.registry.unregister_tool(tool_name)
            
            if success and self.tool_vectorizer:
                # 벡터 정보도 제거
                await self.tool_vectorizer.remove_tool_vector(tool_name)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove tool: {e}")
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """사용 가능한 도구 목록"""
        return self.registry.list_tools(verbose=True)
    
    async def shutdown(self):
        """시스템 종료"""
        logger.info("Shutting down Neuro Dynamic Tool System...")
        
        # 각 컴포넌트 정리 작업 (필요시)
        self.is_initialized = False
        
        logger.info("System shutdown completed")

# 전역 인스턴스 (싱글톤 패턴)
_global_dynamic_system: Optional[NeuroDynamicSystem] = None

def get_neuro_dynamic_system() -> NeuroDynamicSystem:
    """전역 Dynamic System 인스턴스 가져오기"""
    global _global_dynamic_system
    if _global_dynamic_system is None:
        _global_dynamic_system = NeuroDynamicSystem()
    return _global_dynamic_system

def initialize_neuro_dynamic_system(signals=None, **kwargs) -> NeuroDynamicSystem:
    """Neuro Dynamic System 초기화 (기존 시스템과 연동)"""
    global _global_dynamic_system
    _global_dynamic_system = NeuroDynamicSystem(signals=signals, **kwargs)
    return _global_dynamic_system

# 기존 Neuro 시스템과의 호환성을 위한 래퍼 함수들
async def process_with_dynamic_tools(user_input: str, conversation_history: List[Dict] = None,
                                   user_id: str = "default", session_id: str = "default") -> str:
    """Dynamic Tool을 사용한 처리 (기존 시스템 호환)"""
    
    system = get_neuro_dynamic_system()
    
    if not system.is_initialized:
        await system.initialize()
    
    result = await system.process_user_request(
        user_input, user_id, session_id, conversation_history
    )
    
    if result.get("success", False):
        luna_response = result.get("luna_response", {})
        return luna_response.get("response_text", "처리할 수 없습니다.")
    else:
        return result.get("error", "오류가 발생했습니다.")

async def demo_neuro_dynamic_system():
    """Neuro Dynamic System 완전 데모"""
    print("=== Neuro Dynamic Tool System 통합 데모 ===")
    
    # 시스템 초기화
    system = NeuroDynamicSystem()
    print("\n1. 시스템 초기화...")
    init_success = await system.initialize()
    print(f"   초기화 결과: {'성공' if init_success else '실패'}")
    
    if not init_success:
        print(f"   오류: {system.initialization_error}")
        return
    
    # 시스템 상태 확인
    status = await system.get_system_status()
    print(f"\n2. 시스템 상태:")
    print(f"   등록된 도구: {len(system.registry.tools)}개")
    print(f"   벡터화 사용 가능: {status['system_info'].get('vectorization_available', False)}")
    print(f"   초기화 시간: {status['metrics']['initialization_time']:.3f}초")
    
    # 사용 가능한 도구 목록
    tools = system.get_available_tools()
    print(f"\n3. 사용 가능한 도구:")
    for tool in tools:
        print(f"   - {tool['name']} ({tool['type']}) - {tool['description']}")
    
    # 실제 요청 처리 테스트
    test_requests = [
        "2 + 3은 얼마야?",
        "서울 날씨 알려줘",
        "안녕 Luna! 오늘 기분 어때?",
        "10 * 5를 계산하고 날씨도 알려줘"
    ]
    
    print(f"\n4. 요청 처리 테스트:")
    for i, request in enumerate(test_requests, 1):
        print(f"\n   테스트 {i}: '{request}'")
        
        result = await system.process_user_request(request)
        
        if result.get("success", False):
            luna_response = result["luna_response"]
            print(f"   Luna: {luna_response['response_text']}")
            print(f"   사용된 도구: {luna_response['used_tools']}")
            print(f"   실행 시간: {result.get('execution_time', 0):.3f}초")
        else:
            print(f"   오류: {result.get('error', 'Unknown error')}")
    
    # 최종 시스템 통계
    final_status = await system.get_system_status()
    metrics = final_status["metrics"]
    print(f"\n5. 최종 시스템 통계:")
    print(f"   총 요청: {metrics['total_requests']}")
    print(f"   성공한 응답: {metrics['successful_responses']}")
    print(f"   실패한 응답: {metrics['failed_responses']}")
    print(f"   성공률: {metrics['successful_responses']/max(1, metrics['total_requests']):.1%}")
    print(f"   평균 응답 시간: {metrics['average_response_time']:.3f}초")
    
    # 시스템 종료
    await system.shutdown()
    print("\n✅ 데모 완료!")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 데모 실행
    asyncio.run(demo_neuro_dynamic_system())