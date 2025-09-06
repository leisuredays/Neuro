#!/usr/bin/env python3
"""
Interactive Memory Explorer
ChromaDB의 모든 컬렉션과 데이터를 대화형으로 탐색
"""

import chromadb
from chromadb.config import Settings
import json
import uuid
from typing import List, Dict, Any, Optional

from constants import CHROMA_DB_PATH, CHROMA_SETTINGS


class MemoryExplorer:
    def __init__(self, db_path: str = None):
        """메모리 탐색기 초기화"""
        self.db_path = db_path or CHROMA_DB_PATH
        self.client = chromadb.PersistentClient(
            path=self.db_path, 
            settings=Settings(**CHROMA_SETTINGS)
        )
        self.current_collection = None
        
        print(f"🔍 Memory Explorer initialized - Database: {db_path}")
        self.show_collections()

    def show_collections(self):
        """모든 컬렉션 목록 표시"""
        try:
            collections = self.client.list_collections()
            print(f"\n📚 Available Collections ({len(collections)}):")
            
            if not collections:
                print("  No collections found")
                return
                
            for i, collection in enumerate(collections):
                count = collection.count()
                print(f"  [{i+1}] {collection.name} ({count} items)")
                if hasattr(collection, 'metadata') and collection.metadata:
                    desc = collection.metadata.get('description', '')
                    if desc:
                        print(f"      📝 {desc}")
                        
        except Exception as e:
            print(f"❌ Error listing collections: {e}")

    def select_collection(self, name_or_index):
        """컬렉션 선택"""
        try:
            collections = self.client.list_collections()
            
            # 숫자로 선택한 경우
            if name_or_index.isdigit():
                index = int(name_or_index) - 1
                if 0 <= index < len(collections):
                    collection = collections[index]
                    self.current_collection = self.client.get_collection(collection.name)
                    print(f"✅ Selected: {collection.name} ({self.current_collection.count()} items)")
                    return True
                else:
                    print(f"❌ Invalid index. Use 1-{len(collections)}")
                    return False
            
            # 이름으로 선택한 경우
            else:
                try:
                    self.current_collection = self.client.get_collection(name_or_index)
                    print(f"✅ Selected: {name_or_index} ({self.current_collection.count()} items)")
                    return True
                except Exception:
                    print(f"❌ Collection '{name_or_index}' not found")
                    return False
                    
        except Exception as e:
            print(f"❌ Error selecting collection: {e}")
            return False

    def show_items(self, limit: int = 10, search_query: Optional[str] = None):
        """컬렉션 아이템 표시"""
        if not self.current_collection:
            print("❌ No collection selected")
            return
            
        try:
            if search_query:
                print(f"🔍 Searching for: '{search_query}'")
                results = self.current_collection.query(
                    query_texts=[search_query],
                    n_results=min(limit, self.current_collection.count())
                )
                
                if not results['ids'][0]:
                    print("No results found")
                    return
                    
                for i in range(len(results['ids'][0])):
                    item_id = results['ids'][0][i]
                    document = results['documents'][0][i]
                    metadata = results['metadatas'][0][i] or {}
                    distance = results['distances'][0][i]
                    
                    print(f"\n📄 [{i+1}] ID: {item_id[:12]}...")
                    print(f"   📊 Relevance: {(1-distance)*100:.1f}%")
                    print(f"   📝 Content: {document[:150]}{'...' if len(document) > 150 else ''}")
                    
                    if metadata:
                        print(f"   🏷️  Meta: {metadata}")
            else:
                results = self.current_collection.get()
                total = len(results['ids'])
                
                print(f"📋 Items in {self.current_collection.name} (showing {min(limit, total)} of {total}):")
                
                for i in range(min(limit, total)):
                    item_id = results['ids'][i]
                    document = results['documents'][i]
                    metadata = results['metadatas'][i] or {}
                    
                    print(f"\n📄 [{i+1}] ID: {item_id[:12]}...")
                    print(f"   📝 Content: {document[:150]}{'...' if len(document) > 150 else ''}")
                    
                    if metadata:
                        print(f"   🏷️  Meta: {metadata}")
                        
        except Exception as e:
            print(f"❌ Error showing items: {e}")

    def show_item_detail(self, index_or_id: str):
        """특정 아이템 상세 보기"""
        if not self.current_collection:
            print("❌ No collection selected")
            return
            
        try:
            results = self.current_collection.get()
            
            # 인덱스로 선택
            if index_or_id.isdigit():
                index = int(index_or_id) - 1
                if 0 <= index < len(results['ids']):
                    item_id = results['ids'][index]
                    document = results['documents'][index] 
                    metadata = results['metadatas'][index] or {}
                else:
                    print(f"❌ Invalid index. Use 1-{len(results['ids'])}")
                    return
            else:
                # ID로 검색
                found = False
                for i, id_ in enumerate(results['ids']):
                    if id_.startswith(index_or_id) or id_ == index_or_id:
                        item_id = id_
                        document = results['documents'][i]
                        metadata = results['metadatas'][i] or {}
                        found = True
                        break
                
                if not found:
                    print(f"❌ Item with ID '{index_or_id}' not found")
                    return
            
            print(f"\n🔍 ITEM DETAILS")
            print(f"   🆔 ID: {item_id}")
            print(f"   📝 Content:\n{document}")
            print(f"   🏷️  Metadata: {json.dumps(metadata, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            print(f"❌ Error showing item detail: {e}")

    def delete_item(self, index_or_id: str):
        """아이템 삭제"""
        if not self.current_collection:
            print("❌ No collection selected")
            return False
            
        try:
            results = self.current_collection.get()
            item_id = None
            
            # 인덱스로 선택
            if index_or_id.isdigit():
                index = int(index_or_id) - 1
                if 0 <= index < len(results['ids']):
                    item_id = results['ids'][index]
                else:
                    print(f"❌ Invalid index. Use 1-{len(results['ids'])}")
                    return False
            else:
                # ID로 검색
                for id_ in results['ids']:
                    if id_.startswith(index_or_id) or id_ == index_or_id:
                        item_id = id_
                        break
                
                if not item_id:
                    print(f"❌ Item with ID '{index_or_id}' not found")
                    return False
            
            # 확인 요청
            confirm = input(f"🗑️  Delete item {item_id[:12]}...? (y/N): ").lower()
            if confirm == 'y':
                self.current_collection.delete(ids=[item_id])
                print(f"✅ Deleted item: {item_id[:12]}...")
                return True
            else:
                print("❌ Cancelled")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting item: {e}")
            return False

    def add_item(self, content: str, metadata: Optional[Dict] = None):
        """아이템 추가"""
        if not self.current_collection:
            print("❌ No collection selected")
            return False
            
        try:
            item_id = str(uuid.uuid4())
            self.current_collection.upsert(
                ids=[item_id],
                documents=[content],
                metadatas=[metadata or {}]
            )
            print(f"✅ Added item: {item_id[:12]}... - {content[:50]}{'...' if len(content) > 50 else ''}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding item: {e}")
            return False

    def analyze_collection(self):
        """컬렉션 분석"""
        if not self.current_collection:
            print("❌ No collection selected")
            return
            
        try:
            results = self.current_collection.get()
            total = len(results['ids'])
            
            print(f"\n📊 ANALYSIS: {self.current_collection.name}")
            print(f"   📦 Total items: {total}")
            
            if total == 0:
                return
                
            # 메타데이터 분석
            metadata_types = {}
            content_types = {"tool_data": 0, "conversation": 0, "other": 0}
            
            for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
                # 메타데이터 타입 분석
                if meta:
                    for key, value in meta.items():
                        if key not in metadata_types:
                            metadata_types[key] = {}
                        val_str = str(value)
                        metadata_types[key][val_str] = metadata_types[key].get(val_str, 0) + 1
                
                # 컨텐츠 타입 분석
                if any(keyword in doc for keyword in ['Tool Name:', 'Function:', 'get_weather', 'search_web', 'calculate_math']):
                    content_types["tool_data"] += 1
                elif any(keyword in doc for keyword in ['Luna:', 'John:', 'Chat:', '?', 'favorite']):
                    content_types["conversation"] += 1
                else:
                    content_types["other"] += 1
            
            print(f"\n   📋 Content Types:")
            for content_type, count in content_types.items():
                if count > 0:
                    print(f"      {content_type}: {count} ({count/total*100:.1f}%)")
            
            print(f"\n   🏷️  Metadata Analysis:")
            if not metadata_types:
                print(f"      No metadata found")
            else:
                for key, values in metadata_types.items():
                    print(f"      {key}:")
                    for value, count in values.items():
                        print(f"         {value}: {count}")
                        
        except Exception as e:
            print(f"❌ Error analyzing collection: {e}")

    def show_help(self):
        """도움말 표시"""
        print("""
🔧 COMMANDS:
   collections, c     - Show all collections
   select <name/num>  - Select collection by name or number
   list [limit]       - Show items (default: 10)
   search <query>     - Search items
   detail <num/id>    - Show item details
   delete <num/id>    - Delete item
   add <content>      - Add new item
   analyze, stats     - Analyze current collection
   help, ?            - Show this help
   quit, exit, q      - Exit program

📝 EXAMPLES:
   select 1           - Select first collection
   select neuro_collection - Select by name
   list 20            - Show 20 items
   search "weather"   - Search for weather
   detail 1           - Show details of first item
   delete abc123      - Delete by ID prefix
   add "Luna likes coffee" - Add new memory
""")

    def run(self):
        """대화형 루프 실행"""
        print(f"\n🚀 Welcome to Memory Explorer!")
        print(f"Type 'help' for commands, 'quit' to exit")
        
        while True:
            try:
                collection_name = self.current_collection.name if self.current_collection else "None"
                prompt = f"\n[{collection_name}]> "
                
                command = input(prompt).strip()
                if not command:
                    continue
                    
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if cmd in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif cmd in ['help', '?']:
                    self.show_help()
                elif cmd in ['collections', 'c']:
                    self.show_collections()
                elif cmd == 'select':
                    if arg:
                        self.select_collection(arg)
                    else:
                        print("❌ Usage: select <collection_name_or_number>")
                elif cmd == 'list':
                    limit = 10
                    if arg and arg.isdigit():
                        limit = int(arg)
                    self.show_items(limit)
                elif cmd == 'search':
                    if arg:
                        self.show_items(10, arg)
                    else:
                        print("❌ Usage: search <query>")
                elif cmd == 'detail':
                    if arg:
                        self.show_item_detail(arg)
                    else:
                        print("❌ Usage: detail <item_number_or_id>")
                elif cmd == 'delete':
                    if arg:
                        self.delete_item(arg)
                    else:
                        print("❌ Usage: delete <item_number_or_id>")
                elif cmd == 'add':
                    if arg:
                        self.add_item(arg)
                    else:
                        print("❌ Usage: add <content>")
                elif cmd in ['analyze', 'stats']:
                    self.analyze_collection()
                else:
                    print(f"❌ Unknown command: {cmd}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print(f"\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


if __name__ == "__main__":
    explorer = MemoryExplorer()
    explorer.run()