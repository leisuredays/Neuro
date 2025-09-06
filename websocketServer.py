import asyncio
import websockets
import json
import time
from constants import WEBSOCKET_PORT


class WebSocketServer:
    def __init__(self, signals=None):
        self.clients = set()
        self.chat_messages = []
        self.signals = signals
        self.ws_queue = asyncio.Queue() if signals else None
        
    async def register_client(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")
        
    async def unregister_client(self, websocket):
        """Unregister a client"""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")
        
    async def broadcast(self, message):
        """Send message to all connected clients"""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
            
    def parse_chat_message(self, data):
        """Parse and validate chat message format"""
        required_fields = ['type', 'text', 'user_id', 'timestamp']
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in data:
                return None, f"Missing required field: {field}"
                
        # Validate message type
        if data['type'] != 'chat':
            return None, f"Invalid message type: {data['type']}"
            
        # Validate text content
        if not isinstance(data['text'], str) or len(data['text'].strip()) == 0:
            return None, "Text field must be a non-empty string"
            
        # Validate user_id
        if not isinstance(data['user_id'], str) or len(data['user_id'].strip()) == 0:
            return None, "User ID must be a non-empty string"
            
        # Validate timestamp
        if not isinstance(data['timestamp'], (int, float)):
            return None, "Timestamp must be a number"
            
        return data, None
        
    async def handle_chat_message(self, chat_data):
        """Handle parsed chat message"""
        # Add server timestamp
        chat_data['server_timestamp'] = int(time.time())
        
        # Store message
        self.chat_messages.append(chat_data)
        
        # Keep only last 100 messages
        if len(self.chat_messages) > 100:
            self.chat_messages = self.chat_messages[-100:]
            
        print(f"Chat from {chat_data['user_id']}: {chat_data['text']}")
        
        # Send message to LLM system (similar to STT)
        if self.signals:
            # Add to conversation history like STT does
            formatted_message = f"{chat_data['user_id']}: {chat_data['text']}"
            self.signals.history.append({"role": "user", "content": formatted_message})
            self.signals.last_message_time = time.time()
            
            # Trigger LLM processing if AI is not currently speaking or thinking
            if not self.signals.AI_speaking and not self.signals.AI_thinking:
                self.signals.new_message = True
        
        # Broadcast to all clients
        response = {
            "type": "chat_broadcast",
            "data": chat_data
        }
        await self.broadcast(json.dumps(response))
        
        return True
            
    async def handle_client(self, websocket, path):
        """Handle client connection and messages"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                # Check for termination signal
                if self.signals and self.signals.terminate:
                    break
                    
                try:
                    data = json.loads(message)
                    print(f"Received: {data}")
                    
                    # Handle different message types
                    if data.get('type') == 'chat':
                        # Parse and handle chat message
                        parsed_data, error = self.parse_chat_message(data)
                        if error:
                            error_response = {
                                "type": "error",
                                "message": f"Chat parsing error: {error}"
                            }
                            await websocket.send(json.dumps(error_response))
                        else:
                            await self.handle_chat_message(parsed_data)
                    else:
                        # Echo other message types back to all clients
                        response = {
                            "type": "echo",
                            "data": data,
                            "timestamp": int(time.time())
                        }
                        await self.broadcast(json.dumps(response))
                    
                except json.JSONDecodeError:
                    error_response = {
                        "type": "error",
                        "message": "Invalid JSON format"
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def broadcast_ai_response(self, full_message):
        """Broadcast complete AI response in Unity-compatible format"""
        if self.clients:
            message = {
                "type": "ai_response",
                "text": full_message,
                "timestamp": time.time()
            }
            print(f"[WS PUSH] AI response to {len(self.clients)} clients: {len(full_message)} chars")
            await self.broadcast(json.dumps(message))
    
    def send_ai_response_sync(self, ai_message):
        """Synchronous method to send AI response from other threads"""
        if self.clients:
            message = {
                "type": "ai_response", 
                "text": ai_message,
                "timestamp": time.time()
            }
            print(f"[WS PUSH] AI response to {len(self.clients)} clients: {len(ai_message)} chars")
            
            # Create coroutine and run in background
            import threading
            if threading.current_thread() == threading.main_thread():
                # If called from main thread, create task
                asyncio.create_task(self.broadcast(json.dumps(message)))
            else:
                # If called from other thread, use thread-safe approach
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.broadcast(json.dumps(message)))
                finally:
                    loop.close()
    
    async def monitor_ai_responses(self):
        """Monitor for AI responses through sio_queue - send complete messages only"""
        if not self.signals:
            return
            
        current_ai_message = ""
        
        while not (self.signals and self.signals.terminate):
            try:
                await asyncio.sleep(0.05)  # More frequent polling
                
                # Monitor sio_queue for complete messages only
                while not self.signals.sio_queue.empty():
                    event, data = self.signals.sio_queue.get()
                    
                    if event == "next_chunk":
                        # Accumulate chunks but don't broadcast yet
                        current_ai_message += data
                        
                    elif event == "reset_next_message":
                        # AI response complete - send full message at once
                        if current_ai_message.strip():
                            await self.broadcast_ai_response(current_ai_message)
                        current_ai_message = ""
                        
                    elif event == "ai_response_complete":
                        # Direct complete AI message from LLM wrapper
                        await self.broadcast_ai_response(data)
                        
                    elif event == "AI_thinking":
                        # Broadcast AI thinking status
                        message = {
                            "type": "ai_status",
                            "data": {"thinking": data, "speaking": self.signals.AI_speaking},
                            "timestamp": time.time()
                        }
                        print(f"[WS PUSH] AI thinking status to {len(self.clients)} clients: {data}")
                        await self.broadcast(json.dumps(message))
                        
                    elif event == "AI_speaking":
                        # Broadcast AI speaking status
                        message = {
                            "type": "ai_status", 
                            "data": {"thinking": self.signals.AI_thinking, "speaking": data},
                            "timestamp": time.time()
                        }
                        print(f"[WS PUSH] AI speaking status to {len(self.clients)} clients: {data}")
                        await self.broadcast(json.dumps(message))
                        
                    elif event == "full_prompt":
                        # Broadcast the full prompt being sent to AI
                        message = {
                            "type": "ai_prompt",
                            "data": data,
                            "timestamp": time.time()
                        }
                        print(f"[WS PUSH] AI prompt to {len(self.clients)} clients: {len(data)} chars")
                        await self.broadcast(json.dumps(message))
                        
            except Exception as e:
                print(f"AI response monitoring error: {e}")
                await asyncio.sleep(0.1)
            
    def start_server(self):
        """Start the WebSocket server"""
        print(f"Starting WebSocket server on port {WEBSOCKET_PORT}")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            start_server = websockets.serve(
                self.handle_client,
                "localhost",
                WEBSOCKET_PORT
            )
            
            server = loop.run_until_complete(start_server)
            print(f"WebSocket server running on ws://localhost:{WEBSOCKET_PORT}")
            
            # Start AI response monitoring
            if self.signals:
                loop.create_task(self.monitor_ai_responses())
            
            # Run until termination signal
            while not (self.signals and self.signals.terminate):
                try:
                    loop.run_until_complete(asyncio.sleep(0.1))
                except KeyboardInterrupt:
                    break
                    
        except Exception as e:
            print(f"WebSocket server error: {e}")
        finally:
            # Graceful shutdown
            print("WebSocket server shutting down...")
            if 'server' in locals():
                server.close()
                loop.run_until_complete(server.wait_closed())
            loop.close()


if __name__ == "__main__":
    # For standalone testing
    server = WebSocketServer()
    server.start_server()