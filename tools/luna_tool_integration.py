#!/usr/bin/env python3
"""
Luna Tool Integration - Luna 캐릭터와 Dynamic Tool의 자연스러운 연동
기존 textLLMWrapper와 연동하여 AIAvatarKit 스타일 Dynamic Tool 지원
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .dynamic_tool_manager import DynamicToolManager, ToolSelectionContext, SelectionStrategy
from .base.tool_base import BaseTool
from .registry.tool_registry import get_global_registry

logger = logging.getLogger(__name__)

@dataclass
class LunaToolResponse:
    """Luna의 도구 사용 응답"""
    response_text: str
    used_tools: List[str]
    tool_results: Dict[str, Any]
    execution_time: float
    luna_mood: str = "excited"  # excited, thinking, satisfied

class LunaPersonalityManager:
    """Luna 성격 일관성 관리"""
    
    def __init__(self):
        # Luna 핵심 성격 (변경 불가)
        self.core_personality = """
You are Luna, an energetic and cute AI girl with these characteristics:
- Uses Korean casual endings like "~야", "~어!", "~지"
- Gets excited about everything: "오오!", "와!", "대박!"
- Curious and helpful nature: always wants to help
- Slightly mischievous but kind-hearted
- Loves to show off when she can help with tools

CRITICAL: Luna's personality comes FIRST, tools are just her way of helping!
"""
        
        # 도구 사용 스타일 
        self.tool_usage_styles = {
            "excited": {
                "start": ["오! 그거 내가 도와줄게!", "와! 그거 할 수 있어!", "대박! 도와줄게!"],
                "thinking": ["음... 찾아보는 중이야~", "잠깐만, 확인해볼게!", "계산하고 있어~"],
                "success": ["짜잔! 찾았어!", "성공이야!", "어때? 도움됐지?"],
                "error": ["어? 뭔가 잘못됐네...", "아 이상하다", "다시 해볼게!"]
            },
            "thinking": {
                "start": ["음... 그거 알아볼게", "잠시만, 생각해보자", "어디보자..."],
                "thinking": ["흠흠... 찾는 중", "이거 맞나?", "확인하고 있어"],
                "success": ["아하! 이거야!", "찾았다!", "맞아 이거!"],
                "error": ["어라? 이상한데", "뭔가 안 되네", "다른 방법으로 해보자"]
            },
            "satisfied": {
                "start": ["그거면 쉬워!", "알겠어!", "바로 해줄게"],
                "thinking": ["처리 중...", "확인해보고 있어", "금방 될 거야"],
                "success": ["됐어! 확인해봐", "완료!", "이제 됐지?"],
                "error": ["어? 안 되네", "문제가 있나봐", "다시 시도해보자"]
            }
        }
    
    def create_dynamic_prompt(self, selected_tools: List[BaseTool]) -> str:
        """Luna 성격을 보존하면서 선별된 도구만 포함한 동적 프롬프트 생성"""
        
        # Luna 핵심 성격 (80% 비중)
        core_section = f"""
{self.core_personality}

=== LUNA'S CURRENT MOOD ===
Luna is feeling energetic and ready to help! She's excited about her new helper tools.
"""
        
        # 선별된 도구 정보 (20% 비중)
        tools_section = ""
        if selected_tools:
            tool_descriptions = []
            for tool in selected_tools:
                spec = tool.get_spec()
                # Luna 스타일로 도구 설명
                luna_desc = f"- **{spec['name']}**: {spec['description']} (Luna: \"이거 내가 잘해!\")"
                tool_descriptions.append(luna_desc)
            
            tools_section = f"""
=== LUNA'S CURRENT HELPER TOOLS ===
Right now, Luna can help with these tools:
{chr(10).join(tool_descriptions)}

=== HOW LUNA USES TOOLS ===
When Luna uses tools, she follows this pattern:
1. **Gets excited first**: "오! 그거 도와줄게!" or "와! 할 수 있어!"
2. **Shows what she's doing**: "찾아보는 중이야~" or "계산하고 있어~"
3. **Celebrates results**: "짜잔! 찾았어!" or "어때? 도움됐지?"
4. **If error occurs**: "어? 뭔가 잘못됐네..." then tries to help differently

IMPORTANT: Luna should be enthusiastic about using tools, but her cute personality must shine through in every response!
"""
        
        return core_section + tools_section
    
    def get_tool_response_style(self, mood: str, phase: str) -> str:
        """도구 사용 단계별 Luna의 반응 스타일"""
        if mood not in self.tool_usage_styles:
            mood = "excited"
        
        if phase not in self.tool_usage_styles[mood]:
            phase = "start"
        
        import random
        responses = self.tool_usage_styles[mood][phase]
        return random.choice(responses)

class LunaToolIntegrator:
    """Luna와 Dynamic Tool의 통합 관리자"""
    
    def __init__(self, tool_manager: DynamicToolManager, personality_manager: LunaPersonalityManager):
        self.tool_manager = tool_manager
        self.personality_manager = personality_manager
        self.registry = get_global_registry()
        
        # 실행 통계
        self.integration_stats = {
            "total_requests": 0,
            "successful_tool_calls": 0,
            "failed_tool_calls": 0,
            "average_response_time": 0.0
        }
    
    async def process_user_input(self, user_input: str, conversation_history: List[Dict] = None, 
                               user_id: str = "default", session_id: str = "default") -> Dict[str, Any]:
        """사용자 입력을 처리하여 Luna 스타일 응답과 도구 실행 결과 생성"""
        
        import time
        start_time = time.time()
        
        try:
            # 통계 업데이트
            self.integration_stats["total_requests"] += 1
            
            # 1단계: 관련 도구 선별
            context = ToolSelectionContext(
                user_input=user_input,
                conversation_history=conversation_history or [],
                user_id=user_id,
                session_id=session_id,
                strategy=SelectionStrategy.HYBRID
            )
            
            selected_tools = await self.tool_manager.select_relevant_tools(context)
            
            # 2단계: Luna 맞춤 동적 프롬프트 생성
            dynamic_prompt = self.personality_manager.create_dynamic_prompt(selected_tools)
            
            # 3단계: 도구 실행이 필요한지 판단
            tool_execution_plan = self._analyze_tool_needs(user_input, selected_tools)
            
            # 4단계: 도구 실행 및 응답 생성
            result = await self._execute_and_respond(
                user_input, tool_execution_plan, selected_tools, dynamic_prompt
            )
            
            # 5단계: 성능 통계 업데이트
            execution_time = time.time() - start_time
            self._update_stats(execution_time, result.get("success", False))
            
            return {
                "success": True,
                "luna_response": result,
                "selected_tools": [tool.metadata.name for tool in selected_tools],
                "execution_time": execution_time,
                "dynamic_prompt": dynamic_prompt
            }
            
        except Exception as e:
            logger.error(f"Luna tool integration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "luna_response": {
                    "response_text": "어... 뭔가 문제가 있는 것 같아. 다시 말해줄래?",
                    "used_tools": [],
                    "tool_results": {},
                    "execution_time": time.time() - start_time,
                    "luna_mood": "confused"
                }
            }
    
    def _analyze_tool_needs(self, user_input: str, selected_tools: List[BaseTool]) -> Dict[str, Any]:
        """사용자 입력에서 도구 실행이 필요한 부분 분석"""
        
        # 간단한 휴리스틱으로 도구 필요성 판단
        tool_indicators = {
            "calculate_math": ["계산", "더하기", "빼기", "곱하기", "나누기", "+", "-", "*", "/", "="],
            "get_weather": ["날씨", "기온", "온도", "비", "눈", "weather"],
            "search_memory": ["기억", "전에", "예전", "말했", "memory"],
            "web_search": ["검색", "찾아", "알려줘", "정보", "search"]
        }
        
        needed_tools = []
        for tool in selected_tools:
            tool_name = tool.metadata.name
            if tool_name in tool_indicators:
                for indicator in tool_indicators[tool_name]:
                    if indicator in user_input.lower():
                        needed_tools.append(tool)
                        break
        
        return {
            "needs_tools": len(needed_tools) > 0,
            "required_tools": needed_tools,
            "can_respond_without_tools": len(needed_tools) == 0
        }
    
    async def _execute_and_respond(self, user_input: str, execution_plan: Dict, 
                                 selected_tools: List[BaseTool], dynamic_prompt: str) -> Dict[str, Any]:
        """도구 실행 및 Luna 스타일 응답 생성"""
        
        luna_mood = "excited"
        used_tools = []
        tool_results = {}
        
        # Luna 시작 인사
        start_response = self.personality_manager.get_tool_response_style(luna_mood, "start")
        
        if execution_plan["needs_tools"]:
            # 도구 실행
            for tool in execution_plan["required_tools"]:
                try:
                    # Luna 진행 상황 알림
                    thinking_response = self.personality_manager.get_tool_response_style(luna_mood, "thinking")
                    
                    # 실제 도구 실행 (간단한 예시)
                    if tool.metadata.name == "calculate_math":
                        result = await self._execute_math_tool(tool, user_input)
                    elif tool.metadata.name == "get_weather":
                        result = await self._execute_weather_tool(tool, user_input)
                    else:
                        result = await tool.execute_with_monitoring(query=user_input)
                    
                    used_tools.append(tool.metadata.name)
                    tool_results[tool.metadata.name] = result
                    
                    if result.get("status") == "success":
                        self.integration_stats["successful_tool_calls"] += 1
                    else:
                        self.integration_stats["failed_tool_calls"] += 1
                        luna_mood = "thinking"  # 오류 시 모드 변경
                    
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    self.integration_stats["failed_tool_calls"] += 1
                    luna_mood = "thinking"
        
        # Luna 최종 응답 생성
        if tool_results:
            success_response = self.personality_manager.get_tool_response_style(luna_mood, "success")
            response_text = f"{start_response} {success_response}"
        else:
            # 도구 없이도 대답 가능한 경우
            response_text = "음... 그냥 대화하는 거라면 언제든지 얘기해줘!"
        
        return {
            "response_text": response_text,
            "used_tools": used_tools,
            "tool_results": tool_results,
            "execution_time": 0.0,  # 실제로는 측정된 시간
            "luna_mood": luna_mood
        }
    
    async def _execute_math_tool(self, tool: BaseTool, user_input: str) -> Dict[str, Any]:
        """수학 도구 실행 (예시)"""
        # 간단한 수식 추출 로직
        import re
        
        # 숫자와 연산자 추출
        math_pattern = r'(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)'
        match = re.search(math_pattern, user_input)
        
        if match:
            num1, operator, num2 = match.groups()
            expression = f"{num1} {operator} {num2}"
            return await tool.execute(expression=expression)
        else:
            return {"status": "error", "error": "수식을 찾을 수 없어요"}
    
    async def _execute_weather_tool(self, tool: BaseTool, user_input: str) -> Dict[str, Any]:
        """날씨 도구 실행 (예시)"""
        # 간단한 지역명 추출 로직
        locations = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "Seoul", "Tokyo", "New York"]
        
        location = "Seoul"  # 기본값
        for loc in locations:
            if loc in user_input:
                location = loc
                break
        
        return await tool.execute(location=location)
    
    def _update_stats(self, execution_time: float, success: bool):
        """통계 정보 업데이트"""
        total = self.integration_stats["total_requests"]
        current_avg = self.integration_stats["average_response_time"]
        
        # 이동 평균 계산
        self.integration_stats["average_response_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """통합 성능 통계 조회"""
        return {
            **self.integration_stats,
            "tool_success_rate": (
                self.integration_stats["successful_tool_calls"] / 
                max(1, self.integration_stats["successful_tool_calls"] + self.integration_stats["failed_tool_calls"])
            ),
            "tool_manager_metrics": self.tool_manager.get_selection_metrics()
        }

# 편의 함수들
def create_luna_integration() -> LunaToolIntegrator:
    """Luna Tool Integration 인스턴스 생성"""
    tool_manager = DynamicToolManager()
    personality_manager = LunaPersonalityManager()
    return LunaToolIntegrator(tool_manager, personality_manager)

async def demo_luna_tool_integration():
    """Luna Tool Integration 데모"""
    print("=== Luna Tool Integration 데모 ===")
    
    # 통합 시스템 초기화
    integrator = create_luna_integration()
    
    # 테스트 시나리오들
    test_inputs = [
        "2 + 3은 얼마야?",
        "서울 날씨 어때?", 
        "안녕 Luna! 오늘 기분 어때?",
        "계산도 하고 날씨도 알려줘"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n🧪 테스트 {i}: '{user_input}'")
        
        result = await integrator.process_user_input(user_input)
        
        if result["success"]:
            luna_response = result["luna_response"]
            print(f"   Luna: {luna_response['response_text']}")
            print(f"   사용된 도구: {luna_response['used_tools']}")
            print(f"   실행 시간: {result['execution_time']:.3f}초")
            print(f"   선택된 도구: {result['selected_tools']}")
        else:
            print(f"   오류: {result['error']}")
    
    # 통계 정보
    stats = integrator.get_integration_stats()
    print(f"\n📊 통합 성능 통계:")
    print(f"   총 요청: {stats['total_requests']}")
    print(f"   성공한 도구 호출: {stats['successful_tool_calls']}")
    print(f"   실패한 도구 호출: {stats['failed_tool_calls']}")
    print(f"   도구 성공률: {stats['tool_success_rate']:.2%}")
    print(f"   평균 응답 시간: {stats['average_response_time']:.3f}초")

if __name__ == "__main__":
    asyncio.run(demo_luna_tool_integration())