import copy
import requests
import sseclient
import json
import time
import os
from dotenv import load_dotenv
from constants import *
from modules.injection import Injection


class AbstractLLMWrapper:

    def __init__(self, signals, tts, llmState, modules=None):
        self.signals = signals
        self.llmState = llmState
        self.tts = tts
        self.API = self.API(self)
        if modules is None:
            self.modules = {}
        else:
            self.modules = modules

        load_dotenv()  # 환경변수 다시 로드
        api_key = os.getenv('OPENAI_API_KEY')
        print(f"DEBUG: API Key loaded: {api_key[:10]}..." if api_key else "DEBUG: API Key is None")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        #Below constants must be set by child classes
        self.SYSTEM_PROMPT = None
        self.LLM_ENDPOINT = None
        self.CONTEXT_SIZE = None
        self.tokenizer = None

    # Basic filter to check if a message contains a word in the blacklist
    def is_filtered(self, text):
        # Filter messages with words in blacklist
        if any(bad_word.lower() in text.lower().split() for bad_word in self.llmState.blacklist):
            return True
        else:
            return False

    # Assembles all the injections from all modules into a single prompt by increasing priority
    def assemble_injections(self, injections=None):
        if injections is None:
            injections = []

        # Gather all injections from all modules
        for module in self.modules.values():
            injections.append(module.get_prompt_injection())

        # Let all modules clean up once the prompt injection has been fetched from all modules
        for module in self.modules.values():
            module.cleanup()

        # Sort injections by priority
        injections = sorted(injections, key=lambda x: x.priority)

        # Assemble injections
        prompt = ""
        for injection in injections:
            prompt += injection.text
        return prompt

    def _process_tool_results_naturally(self, tool_results):
        """Tool 결과를 자연스러운 컨텍스트 정보로 변환"""
        context_parts = []
        
        for tool_result in tool_results:
            if isinstance(tool_result, dict):
                # Raw tool result (successful execution)
                if 'raw_result' in tool_result:
                    raw = tool_result['raw_result']
                    if isinstance(raw, dict):
                        status = raw.get('status', 'unknown')
                        if status == 'success' and 'weather' in raw:
                            weather = raw['weather']
                            context_parts.append(f"Current weather in {weather['location']}: {weather['temperature']}, {weather['condition']}, feels like {weather.get('feels_like', 'N/A')}, humidity {weather.get('humidity', 'N/A')}.")
                        elif status == 'success' and 'result' in raw:
                            context_parts.append(f"Retrieved information: {raw['result']}")
                        elif 'result' in raw:
                            context_parts.append(f"Information found: {raw['result']}")
                
                # Tool status messages (failures, no tools, etc.)
                else:
                    status = tool_result.get('status', 'unknown')
                    if status in ['no_tools_needed', 'execution_failed', 'no_tool_calls', 'error']:
                        return "\nThe external lookup couldn't be completed right now. Apologize briefly and provide a helpful alternative response based on your knowledge.\n"
        
        if context_parts:
            return "\nRelevant information found:\n" + "\n".join(context_parts) + "\nUse this information to provide an accurate response.\n"
        
        return None

    def generate_prompt(self):
        messages = copy.deepcopy(self.signals.history)

        # For every message prefix with speaker name unless it is blank
        for message in messages:
            if message["role"] == "user" and message["content"] != "":
                message["content"] = HOST_NAME + ": " + message["content"] + "\n"
            elif message["role"] == "assistant" and message["content"] != "":
                message["content"] = AI_NAME + ": " + message["content"] + "\n"

        while True:
            chat_section = ""
            for message in messages:
                chat_section += message["content"]

            generation_prompt = AI_NAME + ": "

            # Add tool results if available
            tool_injections = []
            if hasattr(self.signals, 'tool_results') and self.signals.tool_results:
                context_info = self._process_tool_results_naturally(self.signals.tool_results)
                if context_info:
                    tool_injections = [Injection(context_info, 30)]  # Between system prompt and message history

            # Store tool injections separately to exclude from memory
            self.temp_tool_injections = tool_injections
            base_injections = [Injection(self.SYSTEM_PROMPT, 10)] + tool_injections + [Injection(chat_section, 100)]
            
            # Clear tool results after using them to prevent accumulation
            if hasattr(self.signals, 'tool_results'):
                self.signals.tool_results = []
            full_prompt = self.assemble_injections(base_injections) + generation_prompt
            wrapper = [{"role": "user", "content": full_prompt}]

            # Find out roughly how many tokens the prompt is
            # Not 100% accurate, but it should be a good enough estimate
            prompt_tokens = len(self.tokenizer.encode(full_prompt))
            # print(prompt_tokens)

            # Maximum 90% context size usage before prompting LLM
            if prompt_tokens < 0.9 * self.CONTEXT_SIZE:
                self.signals.sio_queue.put(("full_prompt", full_prompt))
                # print(full_prompt)
                return full_prompt
            else:
                # If the prompt is too long even with no messages, there's nothing we can do, crash
                if len(messages) < 1:
                    raise RuntimeError("Prompt too long even with no messages")

                # Remove the oldest message from the prompt and try again
                messages.pop(0)
                print("Prompt too long, removing earliest message")

    def prepare_payload(self):
        raise NotImplementedError("Must implement prepare_payload in child classes")

    def prompt(self):
        if not self.llmState.enabled:
            return

        # Text/Image LLM 상태 설정 (Tool LLM은 별도 처리)
        if getattr(self, 'save_to_history', True):
            self.signals.text_llm_thinking = True
        
        self.signals.new_message = False
        self.signals.sio_queue.put(("reset_next_message", None))

        data = self.prepare_payload()
        print(f"DEBUG: Sending request to OpenAI API...")
        print(f"DEBUG: Headers: {self.headers}")
        print(f"DEBUG: Payload: {data}")

        try:
            stream_response = requests.post("https://api.openai.com/v1/chat/completions", headers=self.headers, json=data,
                                            stream=True)
            print(f"DEBUG: Response status: {stream_response.status_code}")
            
            if stream_response.status_code != 200:
                print(f"DEBUG: Response text: {stream_response.text}")
                self.signals.AI_thinking = False
                return
                
            response_stream = sseclient.SSEClient(stream_response)
        except Exception as e:
            print(f"DEBUG: Request failed: {e}")
            self.signals.AI_thinking = False
            return

        AI_message = ''
        for event in response_stream.events():
            # Check to see if next message was canceled
            if self.llmState.next_cancelled:
                continue
                
            # Skip data: [DONE] messages
            if event.data == '[DONE]':
                continue

            try:
                payload = json.loads(event.data)
# Debug logging disabled
                
                # OpenAI API structure: check if delta and content exist
                if 'choices' in payload and len(payload['choices']) > 0:
                    delta = payload['choices'][0].get('delta', {})
                    chunk = delta.get('content', '')
                    
                    if chunk:  # Only add non-empty chunks
                        AI_message += chunk
                        # 실시간 전송 제거 - 최종 답변만 전송
                        
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                # Skip empty or malformed data without printing debug message
                if event.data.strip() and event.data != "[DONE]":
                    print(f"DEBUG: Error parsing event data: {e}")
                continue

        if self.llmState.next_cancelled:
            self.llmState.next_cancelled = False
            self.signals.sio_queue.put(("reset_next_message", None))
            self.signals.AI_thinking = False
            return

        # Check for TOOL_TRIGGER token in response FIRST (before any output)
        tool_triggered = False
        if getattr(self, 'save_to_history', True) and '[TOOL_TRIGGER:' in AI_message:
            import re
            # Extract tool trigger request
            match = re.search(r'\[TOOL_TRIGGER:(.*?)\]', AI_message)
            if match:
                tool_request = match.group(1).strip()
                print(f"[TEXT LLM] Tool trigger detected: {tool_request}")
                
                # Remove the trigger token from the displayed message
                AI_message = re.sub(r'\[TOOL_TRIGGER:.*?\]', '', AI_message).strip()
                tool_triggered = True
                
                # Set signals for toolLLM
                self.signals.tool_trigger_request = tool_request
                self.signals.tool_execution_needed = True

        print("AI OUTPUT: " + AI_message)
        self.signals.last_message_time = time.time()
        self.signals.AI_speaking = True
        
        # Text/Image LLM thinking 종료
        if getattr(self, 'save_to_history', True):
            self.signals.text_llm_thinking = False

        if self.is_filtered(AI_message):
            AI_message = "Filtered."
            self.signals.sio_queue.put(("reset_next_message", None))

        # Only save to history if not explicitly disabled (for Tool LLM) - save clean message
        if getattr(self, 'save_to_history', True):
            self.signals.history.append({"role": "assistant", "content": AI_message})
        
        # Send clean message to WebSocket server (without TOOL_TRIGGER tokens)
        if hasattr(self.signals, 'ws_server') and self.signals.ws_server:
            self.signals.ws_server.send_ai_response_sync(AI_message)
        
        self.tts.play(AI_message)

    class API:
        def __init__(self, outer):
            self.outer = outer

        def get_blacklist(self):
            return self.outer.llmState.blacklist

        def set_blacklist(self, new_blacklist):
            self.outer.llmState.blacklist = new_blacklist
            with open('blacklist.txt', 'w') as file:
                for word in new_blacklist:
                    file.write(word + "\n")

            # Notify clients
            self.outer.signals.sio_queue.put(('get_blacklist', new_blacklist))

        def set_LLM_status(self, status):
            self.outer.llmState.enabled = status
            if status:
                self.outer.signals.AI_thinking = False
            self.outer.signals.sio_queue.put(('LLM_status', status))

        def get_LLM_status(self):
            return self.outer.llmState.enabled

        def cancel_next(self):
            self.outer.llmState.next_cancelled = True
            # OpenAI API doesn't have a stop generation endpoint
            pass
