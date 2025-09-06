#!/usr/bin/env python3
"""
Dynamic Tool Manager - AIAvatarKit 스타일 도구 동적 선택 시스템
기존 Neuro 도구 시스템과 ChromaDB를 연동하여 상황에 맞는 도구만 선별
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from constants import CHROMA_TOOLS_COLLECTION
from .base.tool_base import BaseTool, ToolType, ToolStatus
from .registry.tool_registry import ToolRegistry, get_global_registry

logger = logging.getLogger(__name__)

class SelectionStrategy(Enum):
    """도구 선택 전략"""
    KEYWORD_ONLY = "keyword"          # 키워드 기반만
    SEMANTIC_ONLY = "semantic"        # 벡터 검색만  
    HYBRID = "hybrid"                 # 키워드 + 벡터 결합
    SMART = "smart"                   # AI 기반 지능형 선택

@dataclass
class ToolSelectionContext:
    """도구 선택 컨텍스트"""
    user_input: str
    conversation_history: List[Dict[str, Any]]
    user_id: str = "default_user"
    session_id: str = "default_session"
    max_tools: int = 6
    strategy: SelectionStrategy = SelectionStrategy.HYBRID
    prefer_static: bool = True  # STATIC 도구 우선 선택

class DynamicToolManager:
    """AIAvatarKit 스타일 Dynamic Tool 관리자"""
    
    def __init__(self, registry: Optional[ToolRegistry] = None, chroma_client=None):
        self.registry = registry or get_global_registry()
        self.chroma_client = chroma_client
        self.collection = None
        
        # Tool categories definition (English keywords)
        self.tool_categories = {
            "computation": {
                "keywords": ["math", "calculate", "computation", "arithmetic", "add", "subtract", "multiply", "divide", "equation", "solve"],
                "tools": ["calculate_math"]
            },
            "information": {
                "keywords": ["weather", "temperature", "climate", "forecast", "rain", "snow", "sunny", "cloudy", "wind"],
                "tools": ["get_weather"]
            },
            "search": {
                "keywords": ["search", "find", "look up", "information", "news", "web", "query", "discover"],
                "tools": ["web_search"]
            },
            "entertainment": {
                "keywords": ["youtube", "video", "play", "watch"],
                "tools": ["play_youtube_video"]
            },
        }
        
        # Performance metrics
        self.selection_metrics = {
            "total_selections": 0,
            "avg_selection_time": 0.0,
            "strategy_usage": {strategy.value: 0 for strategy in SelectionStrategy}
        }
        
        self._initialize_chroma_collection()
    
    def _initialize_chroma_collection(self):
        """ChromaDB 컬렉션 초기화"""
        if self.chroma_client:
            try:
                self.collection = self.chroma_client.get_or_create_collection(
                    name=CHROMA_TOOLS_COLLECTION
                )
                logger.info(f"ChromaDB tools collection '{CHROMA_TOOLS_COLLECTION}' initialized for dynamic tool selection")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB tools collection: {e}")
    
    async def select_relevant_tools(self, context: ToolSelectionContext) -> List[BaseTool]:
        """컨텍스트 기반 관련 도구 선별"""
        start_time = time.time()
        
        try:
            # 메트릭 업데이트
            self.selection_metrics["total_selections"] += 1
            self.selection_metrics["strategy_usage"][context.strategy.value] += 1
            
            # 전략별 도구 선택
            if context.strategy == SelectionStrategy.KEYWORD_ONLY:
                selected_tools = await self._keyword_selection(context)
            elif context.strategy == SelectionStrategy.SEMANTIC_ONLY:
                selected_tools = await self._semantic_selection(context)
            elif context.strategy == SelectionStrategy.HYBRID:
                selected_tools = await self._hybrid_selection(context)
            else:  # SMART
                selected_tools = await self._smart_selection(context)
            
            # STATIC 도구 우선 처리
            if context.prefer_static:
                selected_tools = self._prioritize_static_tools(selected_tools)
            
            # 최대 개수 제한
            selected_tools = selected_tools[:context.max_tools]
            
            # 성능 메트릭 업데이트
            selection_time = time.time() - start_time
            self._update_metrics(selection_time)
            
            logger.info(f"Selected {len(selected_tools)} tools in {selection_time:.3f}s using {context.strategy.value} strategy")
            
            return selected_tools
            
        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            # 폴백: 기본 도구들 반환
            return self._get_fallback_tools()
    
    async def _keyword_selection(self, context: ToolSelectionContext) -> List[BaseTool]:
        """키워드 기반 도구 선택"""
        user_input_lower = context.user_input.lower()
        matched_tools = set()
        
        # 카테고리별 키워드 매칭
        for category, config in self.tool_categories.items():
            for keyword in config["keywords"]:
                if keyword in user_input_lower:
                    for tool_name in config["tools"]:
                        tool = self.registry.get_tool(tool_name)
                        if tool and tool.metadata.status == ToolStatus.AVAILABLE:
                            matched_tools.add(tool)
        
        # 매칭된 도구가 없으면 기본 도구 반환
        if not matched_tools:
            matched_tools.update(self._get_default_tools())
        
        return list(matched_tools)
    
    async def _semantic_selection(self, context: ToolSelectionContext) -> List[BaseTool]:
        """벡터 기반 시맨틱 검색 도구 선택"""
        if not self.collection:
            logger.warning("ChromaDB collection not available, falling back to keyword selection")
            return await self._keyword_selection(context)
        
        try:
            # 도구 설명 검색
            results = self.collection.query(
                query_texts=[context.user_input],
                n_results=context.max_tools * 2,  # 여유있게 가져와서 필터링
                where={"type": "tool_description"}
            )
            
            selected_tools = []
            for i in range(len(results["ids"][0])):
                tool_name = results["metadatas"][0][i].get("tool_name")
                if tool_name:
                    tool = self.registry.get_tool(tool_name)
                    if tool and tool.metadata.status == ToolStatus.AVAILABLE:
                        selected_tools.append(tool)
            
            return selected_tools
            
        except Exception as e:
            logger.error(f"Semantic selection failed: {e}")
            return await self._keyword_selection(context)  # 폴백
    
    async def _hybrid_selection(self, context: ToolSelectionContext) -> List[BaseTool]:
        """키워드 + 시맨틱 하이브리드 선택"""
        # 키워드 기반 결과
        keyword_tools = set(await self._keyword_selection(context))
        
        # 시맨틱 기반 결과  
        semantic_tools = set(await self._semantic_selection(context))
        
        # 결합 및 우선순위 적용
        combined_tools = []
        
        # 1. 키워드 매칭된 도구들 (높은 우선순위)
        combined_tools.extend(list(keyword_tools))
        
        # 2. 시맨틱 매칭된 도구들 (키워드 매칭과 중복 제거)
        for tool in semantic_tools:
            if tool not in keyword_tools and len(combined_tools) < context.max_tools:
                combined_tools.append(tool)
        
        return combined_tools
    
    async def _smart_selection(self, context: ToolSelectionContext) -> List[BaseTool]:
        """AI 기반 지능형 도구 선택 (미래 확장용)"""
        # 현재는 하이브리드 방식 사용, 추후 LLM 기반 선택 로직으로 확장 가능
        return await self._hybrid_selection(context)
    
    def _prioritize_static_tools(self, tools: List[BaseTool]) -> List[BaseTool]:
        """STATIC 도구를 앞으로 정렬"""
        static_tools = [t for t in tools if t.metadata.type == ToolType.STATIC]
        dynamic_tools = [t for t in tools if t.metadata.type == ToolType.DYNAMIC]
        return static_tools + dynamic_tools
    
    def _get_default_tools(self) -> List[BaseTool]:
        """Default tool set"""
        default_tool_names = ["web_search"]  # Generally useful tools
        default_tools = []
        
        for name in default_tool_names:
            tool = self.registry.get_tool(name)
            if tool and tool.metadata.status == ToolStatus.AVAILABLE:
                default_tools.append(tool)
        
        return default_tools
    
    def _get_fallback_tools(self) -> List[BaseTool]:
        """Fallback tools for error situations"""
        # Return only safe basic tools
        static_tools = self.registry.get_tools_by_type(ToolType.STATIC)
        return static_tools[:3]  # Maximum 3 safe tools
    
    def _update_metrics(self, selection_time: float):
        """Update performance metrics"""
        total = self.selection_metrics["total_selections"]
        current_avg = self.selection_metrics["avg_selection_time"]
        
        # Calculate moving average
        self.selection_metrics["avg_selection_time"] = (
            (current_avg * (total - 1) + selection_time) / total
        )
    
    async def setup_tool_embeddings(self):
        """도구 설명을 벡터 DB에 저장"""
        if not self.collection:
            logger.warning("ChromaDB collection not available")
            return
        
        logger.info("Setting up tool embeddings in ChromaDB...")
        
        try:
            for tool_name, tool in self.registry.tools.items():
                # 도구 설명 생성
                description = self._generate_tool_description(tool)
                
                # 메타데이터 생성
                metadata = {
                    "type": "tool_description",
                    "tool_name": tool_name,
                    "tool_type": tool.metadata.type.value,
                    "category": self._get_tool_category(tool_name),
                    "keywords": ",".join(self._get_tool_keywords(tool_name))
                }
                
                # ChromaDB에 저장
                self.collection.upsert(
                    ids=[f"tool_{tool_name}"],
                    documents=[description],
                    metadatas=[metadata]
                )
            
            logger.info(f"Stored embeddings for {len(self.registry.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to setup tool embeddings: {e}")
    
    def _generate_tool_description(self, tool: BaseTool) -> str:
        """도구 설명 생성 (검색용)"""
        spec = tool.get_spec()
        
        description = f"""
        Tool: {tool.metadata.name}
        Description: {tool.metadata.description}
        Type: {tool.metadata.type.value}
        Function: {spec.get('name', '')}
        Usage: {spec.get('description', '')}
        """
        
        # 카테고리별 키워드 추가
        tool_category = self._get_tool_category(tool.metadata.name)
        if tool_category:
            keywords = self.tool_categories[tool_category]["keywords"]
            description += f"\nKeywords: {', '.join(keywords)}"
        
        return description.strip()
    
    def _get_tool_category(self, tool_name: str) -> Optional[str]:
        """도구의 카테고리 찾기"""
        for category, config in self.tool_categories.items():
            if tool_name in config["tools"]:
                return category
        return None
    
    def _get_tool_keywords(self, tool_name: str) -> List[str]:
        """도구의 키워드 목록 가져오기"""
        category = self._get_tool_category(tool_name)
        if category:
            return self.tool_categories[category]["keywords"]
        return []
    
    def get_selection_metrics(self) -> Dict[str, Any]:
        """선택 성능 메트릭 조회"""
        return {
            "total_selections": self.selection_metrics["total_selections"],
            "average_selection_time": self.selection_metrics["avg_selection_time"],
            "strategy_usage": self.selection_metrics["strategy_usage"].copy(),
            "registered_tools": len(self.registry.tools),
            "available_tools": len(self.registry.get_available_tools())
        }
    
    def get_luna_prompt_tools(self, selected_tools: List[BaseTool]) -> str:
        """Luna 스타일로 도구 설명 생성"""
        if not selected_tools:
            return ""
        
        tool_descriptions = []
        for tool in selected_tools:
            spec = tool.get_spec()
            luna_desc = f"- {spec['name']}: {spec['description']} (Luna가 도와줄 수 있어!)"
            tool_descriptions.append(luna_desc)
        
        return f"""
=== LUNA'S CURRENT HELPER TOOLS ===
Luna can currently help with:
{chr(10).join(tool_descriptions)}

=== LUNA'S TOOL USAGE STYLE ===
- Gets excited about helping: "오! 그거 도와줄게!"
- Shows process: "찾아보는 중이야~"  
- Celebrates success: "짜잔! 찾았어!"

Remember: Luna's cute personality comes FIRST, tools are just her way of helping!
"""


async def demo_dynamic_tool_selection():
    """Dynamic Tool 선택 데모"""
    print("=== Dynamic Tool Selection 데모 ===")
    
    # 매니저 초기화 (ChromaDB 없이 키워드 기반으로 테스트)
    manager = DynamicToolManager()
    
    # 테스트 시나리오들
    test_scenarios = [
        {
            "input": "2 + 2는 얼마야?",
            "expected": ["calculate_math"],
            "strategy": SelectionStrategy.KEYWORD_ONLY
        },
        {
            "input": "서울 날씨 알려줘",  
            "expected": ["get_weather"],
            "strategy": SelectionStrategy.KEYWORD_ONLY
        },
        {
            "input": "예전에 얘기했던 그거 기억나?",
            "expected": ["search_memory"],
            "strategy": SelectionStrategy.KEYWORD_ONLY
        },
        {
            "input": "계산하고 날씨도 알려줘",
            "expected": ["calculate_math", "get_weather"],
            "strategy": SelectionStrategy.HYBRID
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 테스트 {i}: '{scenario['input']}'")
        
        context = ToolSelectionContext(
            user_input=scenario["input"],
            conversation_history=[],
            strategy=scenario["strategy"],
            max_tools=6
        )
        
        selected_tools = await manager.select_relevant_tools(context)
        selected_names = [tool.metadata.name for tool in selected_tools]
        
        print(f"   선택된 도구: {selected_names}")
        print(f"   예상 도구: {scenario['expected']}")
        print(f"   전략: {scenario['strategy'].value}")
        
        # Luna 스타일 프롬프트 생성
        luna_prompt = manager.get_luna_prompt_tools(selected_tools)
        if luna_prompt:
            print(f"   Luna 프롬프트: (생성됨, {len(luna_prompt)} 문자)")
    
    # 성능 메트릭 출력
    metrics = manager.get_selection_metrics()
    print(f"\n📊 성능 메트릭:")
    print(f"   총 선택 횟수: {metrics['total_selections']}")
    print(f"   평균 선택 시간: {metrics['average_selection_time']:.3f}초")
    print(f"   전략별 사용량: {metrics['strategy_usage']}")


if __name__ == "__main__":
    asyncio.run(demo_dynamic_tool_selection())