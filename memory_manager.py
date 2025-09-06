#!/usr/bin/env python3
"""
Memory Management Tool
메모리를 조회, 추가, 삭제할 수 있는 독립적인 관리 도구
"""

import chromadb
from chromadb.config import Settings
import json
import uuid
from typing import List, Dict, Any, Optional
import argparse

from constants import CHROMA_DB_PATH, CHROMA_MEMORIES_COLLECTION, CHROMA_TOOLS_COLLECTION, CHROMA_SETTINGS, CHROMA_COLLECTION_METADATA


class MemoryManager:
    def __init__(self, db_path: str = None):
        """메모리 관리자 초기화"""
        self.db_path = db_path or CHROMA_DB_PATH
        self.client = chromadb.PersistentClient(
            path=self.db_path, 
            settings=Settings(**CHROMA_SETTINGS)
        )
        
        # 메인 메모리 컬렉션 (대화 메모리용)
        self.memory_collection = self.client.get_or_create_collection(
            name=CHROMA_MEMORIES_COLLECTION,
            metadata=CHROMA_COLLECTION_METADATA[CHROMA_MEMORIES_COLLECTION]
        )
        
        # 도구 메타데이터 컬렉션 (도구 검색용)
        self.tools_collection = self.client.get_or_create_collection(
            name=CHROMA_TOOLS_COLLECTION,
            metadata=CHROMA_COLLECTION_METADATA[CHROMA_TOOLS_COLLECTION]
        )
        
        print(f"Memory Manager initialized:")
        print(f"  - Memories: {self.memory_collection.count()} items")
        print(f"  - Tools: {self.tools_collection.count()} items")

    def list_memories(self, limit: int = 20, query: Optional[str] = None) -> List[Dict]:
        """메모리 목록 조회"""
        print(f"\n=== CONVERSATION MEMORIES ({self.memory_collection.count()} total) ===")
        
        if query:
            results = self.memory_collection.query(
                query_texts=[query],
                n_results=min(limit, self.memory_collection.count())
            )
            memories = []
            for i in range(len(results['ids'][0])):
                memories.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
        else:
            results = self.memory_collection.get()
            memories = []
            count = min(limit, len(results['ids']))
            for i in range(count):
                memories.append({
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i] or {}
                })
        
        for i, memory in enumerate(memories):
            print(f"\n[{i+1}] ID: {memory['id'][:8]}...")
            print(f"Content: {memory['content'][:100]}{'...' if len(memory['content']) > 100 else ''}")
            print(f"Type: {memory['metadata'].get('type', 'unknown')}")
            if 'distance' in memory:
                print(f"Relevance: {1 - memory['distance']:.3f}")
        
        return memories

    def list_tools(self, limit: int = 20) -> List[Dict]:
        """도구 메타데이터 조회"""
        print(f"\n=== TOOL METADATA ({self.tools_collection.count()} total) ===")
        
        results = self.tools_collection.get()
        tools = []
        count = min(limit, len(results['ids']))
        
        for i in range(count):
            tools.append({
                'id': results['ids'][i],
                'content': results['documents'][i],
                'metadata': results['metadatas'][i] or {}
            })
        
        for i, tool in enumerate(tools):
            print(f"\n[{i+1}] ID: {tool['id'][:8]}...")
            print(f"Content: {tool['content'][:150]}{'...' if len(tool['content']) > 150 else ''}")
            metadata = tool['metadata']
            if 'tool_name' in metadata:
                print(f"Tool: {metadata['tool_name']} ({metadata.get('tool_type', 'unknown')})")
        
        return tools

    def add_memory(self, content: str, memory_type: str = "manual") -> str:
        """메모리 추가"""
        memory_id = str(uuid.uuid4())
        self.memory_collection.upsert(
            ids=[memory_id],
            documents=[content],
            metadatas=[{"type": memory_type, "source": "manual"}]
        )
        print(f"Added memory: {memory_id[:8]}... - {content[:50]}{'...' if len(content) > 50 else ''}")
        return memory_id

    def delete_memory(self, memory_id: str) -> bool:
        """메모리 삭제"""
        try:
            self.memory_collection.delete(ids=[memory_id])
            print(f"Deleted memory: {memory_id[:8]}...")
            return True
        except Exception as e:
            print(f"Failed to delete memory {memory_id[:8]}...: {e}")
            return False

    def delete_tool(self, tool_id: str) -> bool:
        """도구 메타데이터 삭제"""
        try:
            self.tools_collection.delete(ids=[tool_id])
            print(f"Deleted tool: {tool_id[:8]}...")
            return True
        except Exception as e:
            print(f"Failed to delete tool {tool_id[:8]}...: {e}")
            return False

    def clear_tools(self) -> bool:
        """모든 도구 메타데이터 삭제"""
        try:
            # Get all tool IDs
            results = self.tools_collection.get()
            if results['ids']:
                self.tools_collection.delete(ids=results['ids'])
                print(f"Cleared {len(results['ids'])} tool metadata entries")
            else:
                print("No tool metadata to clear")
            return True
        except Exception as e:
            print(f"Failed to clear tools: {e}")
            return False

    def clear_memories_by_type(self, memory_type: str) -> bool:
        """특정 타입의 메모리 모두 삭제"""
        try:
            results = self.memory_collection.get(
                where={"type": memory_type}
            )
            if results['ids']:
                self.memory_collection.delete(ids=results['ids'])
                print(f"Cleared {len(results['ids'])} memories of type '{memory_type}'")
            else:
                print(f"No memories of type '{memory_type}' found")
            return True
        except Exception as e:
            print(f"Failed to clear memories of type '{memory_type}': {e}")
            return False

    def search_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """메모리 검색"""
        print(f"\n=== SEARCHING MEMORIES: '{query}' ===")
        return self.list_memories(limit=limit, query=query)

    def export_memories(self, filepath: str = "./memories/memories_export.json") -> bool:
        """메모리를 JSON으로 내보내기"""
        try:
            results = self.memory_collection.get()
            
            export_data = {
                "collection": "neuro_memories",
                "count": len(results['ids']),
                "memories": []
            }
            
            for i in range(len(results['ids'])):
                export_data["memories"].append({
                    "id": results['ids'][i],
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i] or {}
                })
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"Exported {len(results['ids'])} memories to {filepath}")
            return True
            
        except Exception as e:
            print(f"Failed to export memories: {e}")
            return False

    def import_memories(self, filepath: str) -> bool:
        """JSON에서 메모리 가져오기"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            memories = data.get("memories", [])
            for memory in memories:
                self.memory_collection.upsert(
                    ids=[memory["id"]],
                    documents=[memory["content"]],
                    metadatas=[memory.get("metadata", {})]
                )
            
            print(f"Imported {len(memories)} memories from {filepath}")
            return True
            
        except Exception as e:
            print(f"Failed to import memories: {e}")
            return False

    def stats(self):
        """통계 정보 출력"""
        print("\n=== MEMORY STATISTICS ===")
        print(f"Conversation Memories: {self.memory_collection.count()}")
        print(f"Tool Metadata: {self.tools_collection.count()}")
        
        # 메모리 타입별 통계
        try:
            memory_results = self.memory_collection.get()
            type_counts = {}
            
            for metadata in memory_results['metadatas']:
                if metadata:
                    mem_type = metadata.get('type', 'unknown')
                    type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
            
            print("\nMemory Types:")
            for mem_type, count in type_counts.items():
                print(f"  - {mem_type}: {count}")
                
        except Exception as e:
            print(f"Failed to get memory type statistics: {e}")


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(description="Memory Management Tool")
    parser.add_argument('--db', default=CHROMA_DB_PATH, help="Database path")
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List memories')
    list_parser.add_argument('--limit', type=int, default=20, help='Limit results')
    list_parser.add_argument('--query', help='Search query')
    
    # Tools command
    subparsers.add_parser('tools', help='List tool metadata')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add memory')
    add_parser.add_argument('content', help='Memory content')
    add_parser.add_argument('--type', default='manual', help='Memory type')
    
    # Delete commands
    delete_parser = subparsers.add_parser('delete', help='Delete memory')
    delete_parser.add_argument('id', help='Memory ID')
    
    # Clear commands
    clear_parser = subparsers.add_parser('clear', help='Clear memories')
    clear_parser.add_argument('--tools', action='store_true', help='Clear tool metadata')
    clear_parser.add_argument('--type', help='Clear memories of specific type')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search memories')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Limit results')
    
    # Export/Import commands
    export_parser = subparsers.add_parser('export', help='Export memories')
    export_parser.add_argument('--file', default='./memories/memories_export.json', help='Export file')
    
    import_parser = subparsers.add_parser('import', help='Import memories')
    import_parser.add_argument('file', help='Import file')
    
    # Stats command
    subparsers.add_parser('stats', help='Show statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MemoryManager(args.db)
    
    if args.command == 'list':
        manager.list_memories(args.limit, args.query)
    elif args.command == 'tools':
        manager.list_tools()
    elif args.command == 'add':
        manager.add_memory(args.content, args.type)
    elif args.command == 'delete':
        manager.delete_memory(args.id)
    elif args.command == 'clear':
        if args.tools:
            manager.clear_tools()
        elif args.type:
            manager.clear_memories_by_type(args.type)
        else:
            print("Specify --tools or --type for clear command")
    elif args.command == 'search':
        manager.search_memories(args.query, args.limit)
    elif args.command == 'export':
        manager.export_memories(args.file)
    elif args.command == 'import':
        manager.import_memories(args.file)
    elif args.command == 'stats':
        manager.stats()


if __name__ == "__main__":
    main()