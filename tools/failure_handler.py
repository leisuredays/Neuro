#!/usr/bin/env python3
"""
Tool Failure Handler - 확장 가능한 도구 실패 처리 시스템
모든 tool 실패에 대해 적절한 fallback 응답을 생성
"""

import logging
import random
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """도구 실패 유형"""
    EXECUTION_ERROR = "execution_error"       # 실행 중 오류
    NETWORK_ERROR = "network_error"           # 네트워크 관련 오류  
    INVALID_PARAMETERS = "invalid_parameters" # 잘못된 매개변수
    SERVICE_UNAVAILABLE = "service_unavailable" # 서비스 이용 불가
    TIMEOUT = "timeout"                       # 시간 초과
    UNKNOWN = "unknown"                       # 알 수 없는 오류

class ToolFailureHandler:
    """도구 실패 처리 및 fallback 응답 생성기"""
    
    def __init__(self):
        # Tool별 특화된 fallback 메시지
        self.tool_specific_messages = {
            "play_youtube_video": {
                FailureType.EXECUTION_ERROR: [
                    "Hmm, having trouble opening that video right now - try searching YouTube directly!",
                    "YouTube's being a bit cranky today, you might want to search for it manually!",
                    "Oops, couldn't get that video to play - maybe check YouTube directly?"
                ],
                FailureType.NETWORK_ERROR: [
                    "Network's acting up - you'll have to hunt down that video yourself!",
                    "Can't reach YouTube right now, but I'm sure that song is worth finding!"
                ],
                FailureType.INVALID_PARAMETERS: [
                    "Need a bit more info about what you want to play!",
                    "Could you be more specific about which video you're looking for?"
                ]
            },
            "get_weather": {
                FailureType.EXECUTION_ERROR: [
                    "Weather service is having a cloudy day - try checking your weather app!",
                    "Can't get the forecast right now, but looking outside usually works!",
                    "Weather data is MIA - maybe peek out the window?"
                ],
                FailureType.NETWORK_ERROR: [
                    "Can't reach the weather service - time for the old-fashioned window check!"
                ]
            },
            "calculate_math": {
                FailureType.EXECUTION_ERROR: [
                    "Math brain is taking a break - try a calculator!",
                    "Numbers aren't cooperating today - calculator to the rescue!",
                    "My math circuits are fried - better grab a calculator!"
                ]
            },
            "search_web": {
                FailureType.EXECUTION_ERROR: [
                    "Search isn't working right now - try Google directly!",
                    "Web search is being stubborn - manual hunting time!",
                    "Search engine's on strike - you'll have to investigate yourself!"
                ]
            }
        }
        
        # 일반적인 fallback 메시지 (tool별 특화 메시지가 없을 때)
        self.generic_messages = {
            FailureType.EXECUTION_ERROR: [
                "Oops, that didn't work as expected - might need to try a different approach!",
                "Hit a snag there - you might want to handle this one manually!",
                "Something went wrong on my end - better tackle this yourself!",
                "That tool's acting up - manual mode might be your best bet!"
            ],
            FailureType.NETWORK_ERROR: [
                "Connection issues are cramping my style - try again later!",
                "Network's being moody - you might have better luck in a bit!",
                "Can't reach the service right now - manual approach recommended!"
            ],
            FailureType.INVALID_PARAMETERS: [
                "Need a bit more detail to help you with that!",
                "Could use some clarification on what you're looking for!",
                "That request needs a bit more specificity!"
            ],
            FailureType.SERVICE_UNAVAILABLE: [
                "That service is taking a nap - try again later!",
                "Service is temporarily down - manual approach recommended!",
                "That tool's offline right now - you'll have to handle this one!"
            ],
            FailureType.TIMEOUT: [
                "That took way too long - the service might be overloaded!",
                "Request timed out - try again or handle it manually!",
                "Too slow on the response - better try a different approach!"
            ],
            FailureType.UNKNOWN: [
                "Something mysterious happened - better handle this manually!",
                "Ran into an unknown issue - you might have better luck doing it yourself!",
                "Hit an unexpected snag - time for the manual approach!"
            ]
        }
    
    def handle_failure(self, tool_name: str, error_info: Dict[str, Any], 
                      user_request: str = "") -> Dict[str, Any]:
        """
        도구 실패를 처리하고 적절한 fallback 응답 생성
        
        Args:
            tool_name: 실패한 도구 이름
            error_info: 오류 정보 (exception, error_type 등)
            user_request: 사용자의 원래 요청
            
        Returns:
            fallback 응답 정보
        """
        try:
            # 실패 유형 분석
            failure_type = self._analyze_failure_type(error_info)
            
            # Fallback 메시지 선택
            message = self._get_fallback_message(tool_name, failure_type)
            
            # 응답 구성
            response = {
                "success": False,
                "fallback_response": message,
                "failure_info": {
                    "tool_name": tool_name,
                    "failure_type": failure_type.value,
                    "user_request": user_request,
                    "error_summary": str(error_info.get("exception", "Unknown error"))
                },
                "suggested_action": self._get_suggested_action(tool_name, failure_type),
                "luna_mood": self._get_luna_mood(failure_type)
            }
            
            logger.info(f"Generated fallback for {tool_name} failure: {failure_type.value}")
            return response
            
        except Exception as e:
            logger.error(f"Error in failure handler: {e}")
            return self._get_emergency_fallback(tool_name, user_request)
    
    def _analyze_failure_type(self, error_info: Dict[str, Any]) -> FailureType:
        """오류 정보를 분석해서 실패 유형 결정"""
        error_msg = str(error_info.get("exception", "")).lower()
        error_type = error_info.get("error_type", "").lower()
        
        if "network" in error_msg or "connection" in error_msg:
            return FailureType.NETWORK_ERROR
        elif "timeout" in error_msg or "timed out" in error_msg:
            return FailureType.TIMEOUT
        elif "parameter" in error_msg or "invalid" in error_msg:
            return FailureType.INVALID_PARAMETERS
        elif "service" in error_msg or "unavailable" in error_msg:
            return FailureType.SERVICE_UNAVAILABLE
        elif error_msg and error_msg != "unknown error":
            return FailureType.EXECUTION_ERROR
        else:
            return FailureType.UNKNOWN
    
    def _get_fallback_message(self, tool_name: str, failure_type: FailureType) -> str:
        """도구와 실패 유형에 맞는 fallback 메시지 선택"""
        # Tool별 특화 메시지 우선
        if tool_name in self.tool_specific_messages:
            tool_messages = self.tool_specific_messages[tool_name]
            if failure_type in tool_messages:
                return random.choice(tool_messages[failure_type])
        
        # 일반적인 메시지로 fallback
        if failure_type in self.generic_messages:
            return random.choice(self.generic_messages[failure_type])
        
        # 마지막 수단
        return "Something went wrong - you might want to handle this manually!"
    
    def _get_suggested_action(self, tool_name: str, failure_type: FailureType) -> str:
        """실패 상황에 대한 제안 액션"""
        action_map = {
            "play_youtube_video": "Try searching YouTube directly in your browser",
            "get_weather": "Check your weather app or look outside",
            "calculate_math": "Use a calculator app or device",
            "search_web": "Try Google or your preferred search engine"
        }
        
        return action_map.get(tool_name, "Try handling this manually or retry later")
    
    def _get_luna_mood(self, failure_type: FailureType) -> str:
        """실패 유형에 따른 Luna의 감정 상태"""
        mood_map = {
            FailureType.EXECUTION_ERROR: "apologetic",
            FailureType.NETWORK_ERROR: "frustrated", 
            FailureType.INVALID_PARAMETERS: "confused",
            FailureType.SERVICE_UNAVAILABLE: "disappointed",
            FailureType.TIMEOUT: "impatient",
            FailureType.UNKNOWN: "puzzled"
        }
        
        return mood_map.get(failure_type, "neutral")
    
    def _get_emergency_fallback(self, tool_name: str, user_request: str) -> Dict[str, Any]:
        """모든 것이 실패했을 때의 비상 fallback"""
        return {
            "success": False,
            "fallback_response": "Welp, that didn't go as planned - you'll have to handle this one yourself!",
            "failure_info": {
                "tool_name": tool_name,
                "failure_type": "emergency_fallback",
                "user_request": user_request,
                "error_summary": "Multiple failure handling errors"
            },
            "suggested_action": "Try handling this manually",
            "luna_mood": "sheepish"
        }
    
    def add_tool_messages(self, tool_name: str, messages: Dict[FailureType, List[str]]):
        """새로운 도구의 특화 메시지 추가 (확장성)"""
        self.tool_specific_messages[tool_name] = messages
        logger.info(f"Added failure messages for tool: {tool_name}")
    
    def add_generic_messages(self, failure_type: FailureType, messages: List[str]):
        """일반적인 메시지 추가 (확장성)"""
        if failure_type not in self.generic_messages:
            self.generic_messages[failure_type] = []
        self.generic_messages[failure_type].extend(messages)
        logger.info(f"Added generic messages for failure type: {failure_type.value}")

# 전역 실패 핸들러 인스턴스
_global_failure_handler: Optional[ToolFailureHandler] = None

def get_failure_handler() -> ToolFailureHandler:
    """전역 실패 핸들러 인스턴스 가져오기"""
    global _global_failure_handler
    if _global_failure_handler is None:
        _global_failure_handler = ToolFailureHandler()
    return _global_failure_handler

def handle_tool_failure(tool_name: str, error_info: Dict[str, Any], 
                       user_request: str = "") -> Dict[str, Any]:
    """편의 함수: 도구 실패 처리"""
    handler = get_failure_handler()
    return handler.handle_failure(tool_name, error_info, user_request)