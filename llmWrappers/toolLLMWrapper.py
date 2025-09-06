import os
import json
import requests
import sseclient
import tiktoken
import asyncio
from constants import *
from llmWrappers.abstractLLMWrapper import AbstractLLMWrapper

# Dynamic Tool System Integration
from tools.neuro_dynamic_system import NeuroDynamicSystem, initialize_neuro_dynamic_system
from tools.dynamic_tool_manager import ToolSelectionContext, SelectionStrategy


class ToolLLMWrapper(AbstractLLMWrapper):
    """Tool LLM that doesn't save its prompts to history"""

    def __init__(self, signals, tts, llmState, modules=None):
        super().__init__(signals, tts, llmState, modules)
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.LLM_ENDPOINT = LLM_ENDPOINT
        self.CONTEXT_SIZE = CONTEXT_SIZE
        self.tokenizer = tiktoken.encoding_for_model(MODEL)
        
        # Use separate API key for tool LLM
        self.tool_api_key = os.environ.get('OPENAI_TOOL_API_KEY', os.environ.get('OPENAI_API_KEY'))
        self.headers = {
            "Authorization": f"Bearer {self.tool_api_key}",
            "Content-Type": "application/json"
        }
        
        # Initialize Dynamic Tool System
        self.dynamic_system = initialize_neuro_dynamic_system(signals=signals)
        self._is_dynamic_system_ready = False
        
        # Flag to prevent history saving
        self.save_to_history = False

    async def get_dynamic_tools_for_context(self, user_input: str):
        """Get dynamic tools based on user input context"""
        if not self._is_dynamic_system_ready:
            await self._ensure_dynamic_system_ready()
        
        try:
            # Create selection context
            context = ToolSelectionContext(
                user_input=user_input,
                conversation_history=self.signals.history[-5:] if hasattr(self.signals, 'history') else [],
                max_tools=6,
                strategy=SelectionStrategy.HYBRID
            )
            
            # Get relevant tools
            selected_tools = await self.dynamic_system.tool_manager.select_relevant_tools(context)
            
            # Convert to OpenAI function format
            openai_tools = []
            for tool in selected_tools:
                spec = tool.get_spec()
                openai_tools.append({
                    "type": "function",
                    "function": spec
                })
            
            print(f"[TOOL LLM] Selected {len(openai_tools)} dynamic tools for context: {user_input[:50]}...")
            return openai_tools
            
        except Exception as e:
            print(f"[TOOL LLM] Error getting dynamic tools: {e}")
            return self._get_fallback_tools()
    
    def _get_fallback_tools(self):
        """Fallback static tools if dynamic system fails"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get the current time and date",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    async def prepare_payload(self):
        # Get dynamic tools based on tool request context
        tool_request = getattr(self.signals, 'tool_trigger_request', '')
        
        # Use tool request as context, fallback to recent user input
        context_for_tools = tool_request
        if not context_for_tools and hasattr(self.signals, 'history') and self.signals.history:
            for msg in reversed(self.signals.history):
                if msg["role"] == "user":
                    context_for_tools = msg["content"]
                    break
        
        dynamic_tools = await self.get_dynamic_tools_for_context(context_for_tools)
        
        return {
            "model": MODEL,
            "messages": [{
                "role": "user",
                "content": self.generate_tool_prompt()
            }],
            "max_tokens": 200,
            "stream": True,
            "stop": STOP_STRINGS,
            "tools": dynamic_tools,
            "tool_choice": "auto"
        }

    def generate_tool_prompt(self):
        """Generate specialized prompt for executing tools based on tool trigger request"""
        
        # Get the specific tool request from the trigger
        tool_request = getattr(self.signals, 'tool_trigger_request', '')
        
        # Get recent conversation context (in chronological order)
        recent_messages = []
        if hasattr(self.signals, 'history') and self.signals.history:
            # Get last 4 messages in chronological order (not reversed)
            for msg in self.signals.history[-4:]:
                if msg["role"] == "user" and msg["content"].strip():
                    recent_messages.append(f"User: {msg['content']}")
                elif msg["role"] == "assistant" and msg["content"].strip():
                    # Clean any TOOL_TRIGGER tokens from display
                    clean_content = msg['content']
                    if '[TOOL_TRIGGER:' in clean_content:
                        import re
                        clean_content = re.sub(r'\[TOOL_TRIGGER:.*?\]', '', clean_content).strip()
                    recent_messages.append(f"Luna: {clean_content}")
        
        conversation_context = "\n".join(recent_messages) if recent_messages else "No recent conversation"
        
        tool_prompt = f"""You are a tool execution assistant. Luna has requested tool execution with a specific request.

RECENT CONVERSATION:
{conversation_context}

TOOL REQUEST: "{tool_request}"

YOUR TASK:
Analyze the tool request and execute the appropriate tools to fulfill it. The request describes what the user needs.

INSTRUCTIONS:
1. Understand what "{tool_request}" is asking for
2. Select and execute the most appropriate tools available to fulfill this request
3. If the request is clear and specific, execute the relevant tools
4. If the request is too vague or no tools are needed, respond "NO_TOOLS_NEEDED"

EXAMPLES:
- Request: "get current weather" → Execute weather tool
- Request: "search for minecraft tutorials" → Execute search/web tool  
- Request: "calculate complex math problem" → Execute calculator/math tool
- Request: "find information about AI news" → Execute search/news tool
- Request: "play music" → Execute audio/music tool
- Request: "take a screenshot" → Execute screen capture tool

Execute the appropriate tools based on the request: "{tool_request}" """

        return tool_prompt

    async def _ensure_dynamic_system_ready(self):
        """Ensure dynamic tool system is initialized"""
        if not self._is_dynamic_system_ready:
            try:
                await self.dynamic_system.initialize()
                self._is_dynamic_system_ready = True
                print("[TOOL LLM] Dynamic tool system initialized")
            except Exception as e:
                print(f"[TOOL LLM] Failed to initialize dynamic system: {e}")

    async def handle_tool_calls(self, tool_calls):
        """Handle tool function calls using dynamic tool system"""
        if not self._is_dynamic_system_ready:
            await self._ensure_dynamic_system_ready()
        
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = tool_call["function"]["arguments"]
            
            try:
                # Parse JSON arguments if needed
                if isinstance(function_args, str):
                    try:
                        function_args = json.loads(function_args)
                    except:
                        function_args = {}
                
                # Get tool from dynamic system
                tool = self.dynamic_system.registry.get_tool(function_name)
                
                if tool:
                    # Execute using dynamic tool system
                    print(f"[TOOL LLM] Executing dynamic tool: {function_name}")
                    tool_result = await tool.execute_with_monitoring(
                        user_request=f"Tool call: {function_name}",
                        **function_args
                    )
                    
                    # Format result
                    if "error" in tool_result:
                        result = f"Tool error: {tool_result['error']}"
                    else:
                        result = str(tool_result.get("result", tool_result))
                        
                else:
                    # Fallback for unknown tools
                    result = await self._handle_fallback_tool(function_name, function_args)
                
            except Exception as e:
                result = f"Tool execution error: {str(e)}"
                print(f"[TOOL LLM] Tool execution failed: {e}")
            
            # Store both OpenAI format and raw result for signals
            results.append({
                "tool_call_id": tool_call["id"],
                "role": "tool", 
                "content": result,
                "raw_result": tool_result  # Store the raw result for textLLM
            })
            
            print(f"[TOOL LLM] Executed {function_name}: {result[:100]}...")
        
        return results
    
    async def _handle_fallback_tool(self, function_name: str, function_args: dict) -> str:
        """Handle fallback tools not in dynamic system"""
        if function_name == "get_current_time":
            import datetime
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return f"Current time: {current_time}"
        else:
            return f"Unknown tool: {function_name}"

    def prompt(self):
        """Override prompt method to handle tool results without sending to user"""
        # Run async method in new event loop since this is called from sync context
        import threading
        try:
            # Check if we're already in an async context
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context
            asyncio.create_task(self._async_prompt())
        except RuntimeError:
            # No running event loop, create new one in thread
            thread = threading.Thread(target=self._run_async_prompt, daemon=True)
            thread.start()
    
    def _run_async_prompt(self):
        """Run async prompt in new event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_prompt())
        finally:
            loop.close()
    
    def prompt_async(self):
        """Async version that returns Future for hybrid execution"""
        from concurrent.futures import ThreadPoolExecutor
        import concurrent.futures
        
        # Create a future that will be resolved when tool execution completes
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ToolLLM-Async")
        future = executor.submit(self._sync_prompt_wrapper)
        
        # Store executor reference to prevent garbage collection
        future.executor = executor
        
        return future
    
    def _sync_prompt_wrapper(self):
        """Synchronous wrapper for async prompt - used by prompt_async"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._async_prompt())
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"[TOOL LLM] Error in async execution: {e}")
            return None
    
    async def _async_prompt(self):
        """Async version of prompt method"""
        if not self.llmState.enabled:
            return

        self.signals.tool_llm_thinking = True
        self.signals.new_message = False
        
        # Don't put in sio_queue to avoid WebSocket broadcasts
        # self.signals.sio_queue.put(("reset_next_message", None))

        data = await self.prepare_payload()
        
        # Log the prompt being sent to Tool LLM
        print(f"[TOOL LLM] Payload: {data}")
        if 'messages' in data and len(data['messages']) > 0:
            print(f"[TOOL LLM] Prompt content: {data['messages'][0]['content'][:500]}{'...' if len(data['messages'][0]['content']) > 500 else ''}")
            print(f"[TOOL LLM] Available tools: {[tool['function']['name'] for tool in data.get('tools', [])]}")

        try:
            stream_response = requests.post("https://api.openai.com/v1/chat/completions", 
                                          headers=self.headers, json=data,
                                          verify=False, stream=True)
            response_stream = sseclient.SSEClient(stream_response)

            AI_message = ''
            tool_calls = []
            
            for event in response_stream.events():
                if self.llmState.next_cancelled:
                    continue

                try:
                    payload = json.loads(event.data)
                    
                    if 'choices' in payload and len(payload['choices']) > 0:
                        delta = payload['choices'][0].get('delta', {})
                        
                        # Handle tool calls
                        if 'tool_calls' in delta:
                            for tool_call in delta['tool_calls']:
                                if len(tool_calls) <= tool_call['index']:
                                    tool_calls.extend([None] * (tool_call['index'] + 1 - len(tool_calls)))
                                
                                if tool_calls[tool_call['index']] is None:
                                    tool_calls[tool_call['index']] = tool_call
                                else:
                                    # Merge tool call data
                                    existing = tool_calls[tool_call['index']]
                                    if 'function' in tool_call and 'arguments' in tool_call['function']:
                                        if 'function' not in existing:
                                            existing['function'] = {}
                                        if 'arguments' not in existing['function']:
                                            existing['function']['arguments'] = ''
                                        existing['function']['arguments'] += tool_call['function']['arguments']
                        
                        # Handle regular content
                        chunk = delta.get('content', '')
                        if chunk:
                            AI_message += chunk
                            
                except Exception as e:
                    # Skip empty or malformed data without printing debug message
                    if hasattr(self, '_last_error') and str(e) == str(self._last_error):
                        pass  # Don't repeat same error
                    else:
                        print(f"DEBUG: Error parsing event data: {e}")
                        self._last_error = e
                    continue

            if self.llmState.next_cancelled:
                self.llmState.next_cancelled = False
                self.signals.tool_llm_thinking = False
                return

            # Check if LLM decided no tools are needed
            if "NO_TOOLS_NEEDED" in AI_message:
                print("[TOOL LLM] No tools needed - skipping execution")
                # Signal that tool execution failed/was skipped
                self.signals.tool_results = [{"status": "no_tools_needed", "message": "No external tools were needed for this request"}]
                self.signals.new_message = True  # Trigger textLLM to provide fallback response
                self.signals.tool_llm_thinking = False
                return

            # Process tool calls if any
            if tool_calls:
                tool_results = await self.handle_tool_calls([tc for tc in tool_calls if tc is not None])
                
                # Replace tool results (don't accumulate old results)
                self.signals.tool_results = tool_results
                    
                print(f"[TOOL LLM] Executed {len(tool_results)} tool calls")
                
                # Trigger new message to prompt main LLM with tool results
                if tool_results:
                    print("[TOOL LLM] Triggering new message with tool results")
                    self.signals.new_message = True
                else:
                    # No successful tool results - notify textLLM of failure
                    self.signals.tool_results = [{"status": "execution_failed", "message": "Tool execution failed or returned no results"}]
                    self.signals.new_message = True
            else:
                # No tool calls made - notify textLLM
                self.signals.tool_results = [{"status": "no_tool_calls", "message": "No tool calls were generated by the LLM"}]
                self.signals.new_message = True
            
            # Don't send to user - tool LLM works behind the scenes
            # Also don't save to history to prevent tool metadata pollution
            self.signals.tool_llm_thinking = False
            
        except Exception as e:
            print(f"[TOOL LLM] Error: {e}")
            # Signal tool execution error to textLLM
            self.signals.tool_results = [{"status": "error", "message": f"Tool execution error: {str(e)}"}]
            self.signals.new_message = True
            self.signals.tool_llm_thinking = False