#!/usr/bin/env python3
"""
Tool Vectorizer - 도구 정보를 ChromaDB에 벡터화하여 저장하고 검색
기존 Neuro 메모리 시스템과 연동하여 도구 시맨틱 검색 지원
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings

from constants import CHROMA_DB_PATH, CHROMA_TOOLS_COLLECTION, CHROMA_COLLECTION_METADATA, CHROMA_SETTINGS
from .base.tool_base import BaseTool, ToolType
from .registry.tool_registry import ToolRegistry, get_global_registry

logger = logging.getLogger(__name__)

class ToolVectorizer:
    """도구 정보 벡터화 및 검색 관리자"""
    
    def __init__(self, chroma_path: str = None, registry: Optional[ToolRegistry] = None):
        self.chroma_path = chroma_path or CHROMA_DB_PATH
        self.registry = registry or get_global_registry()
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(**CHROMA_SETTINGS)
        )
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_TOOLS_COLLECTION,
            metadata=CHROMA_COLLECTION_METADATA[CHROMA_TOOLS_COLLECTION]
        )
        
        # 도구 카테고리 및 키워드 매핑
        self.tool_categories = {
            "computation": {
                "keywords": ["계산", "수학", "math", "calculate", "더하기", "빼기", "곱하기", "나누기", "덧셈", "뺄셈", "곱셈", "나눗셈"],
                "description": "Mathematical calculations and computations",
                "use_cases": ["basic arithmetic", "advanced math", "equation solving"]
            },
            "information": {
                "keywords": ["날씨", "weather", "온도", "기온", "비", "눈", "맑음", "흐림", "습도", "바람"],
                "description": "Weather and environmental information",
                "use_cases": ["current weather", "weather forecast", "temperature check"]
            },
            "search": {
                "keywords": ["검색", "search", "찾아", "알려줘", "정보", "뉴스", "웹", "인터넷", "구글"],
                "description": "Web search and information retrieval", 
                "use_cases": ["web search", "news lookup", "information gathering"]
            },
            "memory": {
                "keywords": ["기억", "memory", "과거", "전에", "예전", "말했", "얘기했", "대화", "기록"],
                "description": "Conversation memory and history search",
                "use_cases": ["past conversations", "memory recall", "context retrieval"]
            },
            "entertainment": {
                "keywords": ["음악", "music", "노래", "게임", "game", "재미", "놀이"],
                "description": "Entertainment and media tools",
                "use_cases": ["music playback", "game interaction", "entertainment"]
            },
            "utility": {
                "keywords": ["도구", "tool", "유틸", "util", "시간", "time", "타이머", "timer"],
                "description": "General utility and helper tools",
                "use_cases": ["time management", "utility functions", "helper tools"]
            }
        }
        
        # 벡터화 통계
        self.vectorization_stats = {
            "total_tools_vectorized": 0,
            "last_update": None,
            "search_count": 0,
            "average_search_time": 0.0
        }
    
    async def vectorize_all_tools(self) -> bool:
        """등록된 모든 도구를 벡터화하여 ChromaDB에 저장"""
        try:
            logger.info("Starting tool vectorization process...")
            
            vectorized_count = 0
            
            for tool_name, tool in self.registry.tools.items():
                success = await self._vectorize_single_tool(tool_name, tool)
                if success:
                    vectorized_count += 1
            
            # 통계 업데이트
            self.vectorization_stats["total_tools_vectorized"] = vectorized_count
            self.vectorization_stats["last_update"] = time.time()
            
            logger.info(f"Successfully vectorized {vectorized_count} tools")
            return True
            
        except Exception as e:
            logger.error(f"Tool vectorization failed: {e}")
            return False
    
    async def _vectorize_single_tool(self, tool_name: str, tool: BaseTool) -> bool:
        """단일 도구를 벡터화하여 저장"""
        try:
            # 도구 설명 문서 생성
            tool_document = self._generate_tool_document(tool_name, tool)
            
            # 메타데이터 생성
            metadata = self._generate_tool_metadata(tool_name, tool)
            
            # ChromaDB에 저장 (upsert로 업데이트/삽입)
            self.collection.upsert(
                ids=[f"tool_{tool_name}"],
                documents=[tool_document],
                metadatas=[metadata]
            )
            
            logger.debug(f"Vectorized tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to vectorize tool {tool_name}: {e}")
            return False
    
    def _generate_tool_document(self, tool_name: str, tool: BaseTool) -> str:
        """도구의 검색용 문서 생성"""
        spec = tool.get_spec()
        
        # 카테고리 정보 가져오기
        category_info = self._get_tool_category_info(tool_name, tool)
        
        # 문서 구성
        document_parts = [
            f"Tool Name: {tool_name}",
            f"Description: {tool.metadata.description}",
            f"Function: {spec.get('name', tool_name)}",
            f"Purpose: {spec.get('description', tool.metadata.description)}",
            f"Type: {tool.metadata.type.value}",
            f"Category: {category_info['category']}",
            f"Keywords: {', '.join(category_info['keywords'])}",
            f"Use Cases: {', '.join(category_info['use_cases'])}"
        ]
        
        # 파라미터 정보 추가
        if 'parameters' in spec and 'properties' in spec['parameters']:
            properties = spec['parameters']['properties']
            param_descriptions = []
            for param_name, param_info in properties.items():
                param_desc = f"{param_name}: {param_info.get('description', 'parameter')}"
                param_descriptions.append(param_desc)
            
            document_parts.append(f"Parameters: {', '.join(param_descriptions)}")
        
        return "\n".join(document_parts)
    
    def _generate_tool_metadata(self, tool_name: str, tool: BaseTool) -> Dict[str, Any]:
        """도구의 메타데이터 생성"""
        category_info = self._get_tool_category_info(tool_name, tool)
        
        return {
            "type": "tool_description",
            "tool_name": tool_name,
            "tool_type": tool.metadata.type.value,
            "category": category_info["category"],
            "keywords": ",".join(category_info["keywords"]),
            "version": tool.metadata.version,
            "status": tool.metadata.status.value,
            "vectorized_at": time.time()
        }
    
    def _get_tool_category_info(self, tool_name: str, tool: BaseTool) -> Dict[str, Any]:
        """도구의 카테고리 정보 추론"""
        tool_name_lower = tool_name.lower()
        description_lower = tool.metadata.description.lower()
        
        # 도구 이름과 설명으로 카테고리 매칭
        for category, config in self.tool_categories.items():
            for keyword in config["keywords"]:
                if keyword in tool_name_lower or keyword in description_lower:
                    return {
                        "category": category,
                        "keywords": config["keywords"],
                        "use_cases": config["use_cases"]
                    }
        
        # 매칭되지 않으면 기본값
        return {
            "category": "utility",
            "keywords": ["도구", "tool", "유틸"],
            "use_cases": ["general utility"]
        }
    
    async def search_relevant_tools(self, query: str, max_results: int = 6, 
                                  tool_type: Optional[ToolType] = None) -> List[Dict[str, Any]]:
        """쿼리에 기반한 관련 도구 검색"""
        start_time = time.time()
        
        try:
            # ChromaDB에서 도구 검색
            where_clause = {"type": "tool_description"}
            if tool_type:
                where_clause["tool_type"] = tool_type.value
            
            results = self.collection.query(
                query_texts=[query],
                n_results=max_results * 2,  # 여유있게 가져와서 필터링
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # 결과 처리
            relevant_tools = []
            for i in range(len(results["ids"][0])):
                tool_info = {
                    "tool_name": results["metadatas"][0][i]["tool_name"],
                    "category": results["metadatas"][0][i]["category"],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i],  # 유사도 계산
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i]
                }
                
                # 실제 등록된 도구인지 확인
                tool = self.registry.get_tool(tool_info["tool_name"])
                if tool and tool.metadata.status.value == "available":
                    tool_info["tool_object"] = tool
                    relevant_tools.append(tool_info)
            
            # 유사도 기준 정렬
            relevant_tools.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 최대 개수 제한
            relevant_tools = relevant_tools[:max_results]
            
            # 통계 업데이트
            search_time = time.time() - start_time
            self._update_search_stats(search_time)
            
            logger.info(f"Found {len(relevant_tools)} relevant tools for query: '{query}'")
            return relevant_tools
            
        except Exception as e:
            logger.error(f"Tool search failed: {e}")
            return []
    
    def _update_search_stats(self, search_time: float):
        """검색 통계 업데이트"""
        self.vectorization_stats["search_count"] += 1
        count = self.vectorization_stats["search_count"]
        current_avg = self.vectorization_stats["average_search_time"]
        
        # 이동 평균 계산
        self.vectorization_stats["average_search_time"] = (
            (current_avg * (count - 1) + search_time) / count
        )
    
    async def get_tool_recommendations(self, conversation_history: List[Dict], 
                                    current_input: str, max_tools: int = 5) -> List[Dict[str, Any]]:
        """대화 히스토리와 현재 입력을 기반한 도구 추천"""
        
        # 대화 히스토리에서 컨텍스트 추출
        context_keywords = set()
        
        for message in conversation_history[-5:]:  # 최근 5개 메시지
            content = message.get("content", "").lower()
            for category, config in self.tool_categories.items():
                for keyword in config["keywords"]:
                    if keyword in content:
                        context_keywords.add(keyword)
        
        # 현재 입력과 컨텍스트 결합
        combined_query = current_input
        if context_keywords:
            combined_query += " " + " ".join(context_keywords)
        
        # 도구 검색
        recommendations = await self.search_relevant_tools(combined_query, max_tools)
        
        # 컨텍스트 점수 추가
        for rec in recommendations:
            context_score = 0
            tool_keywords = rec["metadata"]["keywords"].split(",")
            for keyword in tool_keywords:
                if keyword.strip() in context_keywords:
                    context_score += 0.1
            
            rec["context_score"] = context_score
            rec["final_score"] = rec["similarity"] + context_score
        
        # 최종 점수로 재정렬
        recommendations.sort(key=lambda x: x["final_score"], reverse=True)
        
        return recommendations
    
    def get_vectorization_status(self) -> Dict[str, Any]:
        """벡터화 상태 및 통계 정보"""
        return {
            "vectorization_stats": self.vectorization_stats.copy(),
            "registered_tools": len(self.registry.tools),
            "chroma_collection_count": self.collection.count(),
            "tool_categories": list(self.tool_categories.keys())
        }
    
    async def update_tool_vector(self, tool_name: str) -> bool:
        """특정 도구의 벡터 정보 업데이트"""
        tool = self.registry.get_tool(tool_name)
        if not tool:
            logger.warning(f"Tool {tool_name} not found in registry")
            return False
        
        return await self._vectorize_single_tool(tool_name, tool)
    
    async def remove_tool_vector(self, tool_name: str) -> bool:
        """도구 벡터 정보 삭제"""
        try:
            self.collection.delete(ids=[f"tool_{tool_name}"])
            logger.info(f"Removed vector for tool: {tool_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove tool vector {tool_name}: {e}")
            return False
    
    def list_vectorized_tools(self) -> List[Dict[str, Any]]:
        """벡터화된 도구 목록 조회"""
        try:
            results = self.collection.get(
                where={"type": "tool_description"},
                include=["metadatas"]
            )
            
            tools = []
            for i, tool_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                tools.append({
                    "id": tool_id,
                    "tool_name": metadata["tool_name"],
                    "category": metadata["category"],
                    "tool_type": metadata["tool_type"],
                    "vectorized_at": metadata.get("vectorized_at", "unknown")
                })
            
            return tools
            
        except Exception as e:
            logger.error(f"Failed to list vectorized tools: {e}")
            return []

# 편의 함수들
def create_tool_vectorizer(chroma_path: str = "./memories/chroma.db") -> ToolVectorizer:
    """Tool Vectorizer 인스턴스 생성"""
    return ToolVectorizer(chroma_path)

async def demo_tool_vectorization():
    """Tool Vectorization 데모"""
    print("=== Tool Vectorization 데모 ===")
    
    # 벡터화 시스템 초기화
    vectorizer = create_tool_vectorizer()
    
    # 1. 도구 벡터화
    print("\n1. 도구 벡터화 중...")
    success = await vectorizer.vectorize_all_tools()
    print(f"   벡터화 결과: {'성공' if success else '실패'}")
    
    # 2. 벡터화 상태 확인
    status = vectorizer.get_vectorization_status()
    print(f"\n2. 벡터화 상태:")
    print(f"   벡터화된 도구 수: {status['vectorization_stats']['total_tools_vectorized']}")
    print(f"   등록된 도구 수: {status['registered_tools']}")
    print(f"   컬렉션 총 아이템: {status['chroma_collection_count']}")
    
    # 3. 벡터화된 도구 목록
    vectorized_tools = vectorizer.list_vectorized_tools()
    print(f"\n3. 벡터화된 도구 목록:")
    for tool in vectorized_tools:
        print(f"   - {tool['tool_name']} ({tool['category']})")
    
    # 4. 도구 검색 테스트
    test_queries = [
        "수학 계산 해줘",
        "날씨 알려줘", 
        "무엇인가 검색해줘",
        "과거 대화 기억나?"
    ]
    
    print(f"\n4. 도구 검색 테스트:")
    for query in test_queries:
        results = await vectorizer.search_relevant_tools(query, max_results=3)
        print(f"\n   쿼리: '{query}'")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['tool_name']} (유사도: {result['similarity']:.3f})")
    
    # 5. 성능 통계
    status = vectorizer.get_vectorization_status()
    stats = status["vectorization_stats"]
    print(f"\n5. 성능 통계:")
    print(f"   검색 횟수: {stats['search_count']}")
    print(f"   평균 검색 시간: {stats['average_search_time']:.3f}초")

if __name__ == "__main__":
    asyncio.run(demo_tool_vectorization())