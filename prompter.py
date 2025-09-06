import time
from constants import PATIENCE


class Prompter:
    def __init__(self, signals, llms, modules=None):
        self.signals = signals
        self.llms = llms
        if modules is None:
            self.modules = {}
        else:
            self.modules = modules

        self.system_ready = False
        self.timeSinceLastMessage = 0.0
        
        # For hybrid tool execution
        self.pending_tool_future = None
        self.last_tool_request = ""
        self.tool_executed_for_current_request = False

    def prompt_now(self):
        # Don't prompt AI if system isn't ready yet
        if not self.signals.stt_ready or not self.signals.tts_ready:
            return False
        # Don't prompt AI when anyone is currently talking
        if self.signals.human_speaking or self.signals.AI_thinking or self.signals.AI_speaking:
            return False
        # Prompt AI if human said something
        if self.signals.new_message:
            return True
        # Prompt AI if there are unprocessed chat messages
        if len(self.signals.recentTwitchMessages) > 0:
            return True
        # Prompt if some amount of seconds has passed without anyone talking
        if self.timeSinceLastMessage > PATIENCE:
            return True

    def chooseLLM(self):
        if "multimodal" in self.modules and self.modules["multimodal"].API.multimodal_now():
            return self.llms["image"]
        else:
            return self.llms["text"]

    def prompt_loop(self):
        print("Prompter loop started")

        while not self.signals.terminate:
            # Set lastMessageTime to now if program is still starting
            if self.signals.last_message_time == 0.0 or (not self.signals.stt_ready or not self.signals.tts_ready):
                self.signals.last_message_time = time.time()
                self.timeSinceLastMessage = 0.0
            else:
                if not self.system_ready:
                    print("SYSTEM READY")
                    self.system_ready = True

            # Calculate and set time since last message
            self.timeSinceLastMessage = time.time() - self.signals.last_message_time
            self.signals.sio_queue.put(("patience_update", {"crr_time": self.timeSinceLastMessage, "total_time": PATIENCE}))

            # Check if previous tool execution completed
            if self.pending_tool_future and self.pending_tool_future.done():
                try:
                    result = self.pending_tool_future.result()
                    print(f"[TOOL LLM] Tool execution completed: {result is not None}")
                    # Clean up executor
                    if hasattr(self.pending_tool_future, 'executor'):
                        self.pending_tool_future.executor.shutdown(wait=False)
                except Exception as e:
                    print(f"[TOOL LLM] Tool execution error: {e}")
                finally:
                    self.pending_tool_future = None

            # Check if toolLLM needs to be triggered by TOOL_TRIGGER token
            if hasattr(self.signals, 'tool_execution_needed') and self.signals.tool_execution_needed:
                if "tool" in self.llms and self.pending_tool_future is None:
                    tool_request = getattr(self.signals, 'tool_trigger_request', '')
                    print(f"[TOOL LLM] Executing tools for request: {tool_request}")
                    self.pending_tool_future = self.llms["tool"].prompt_async()
                    self.signals.tool_execution_needed = False

            # Decide and prompt LLM
            if self.prompt_now():
                print("PROMPTING AI")
                
                # Start main LLM (textLLM will trigger toolLLM if needed)
                print("[MAIN LLM] Starting response generation")
                llmWrapper = self.chooseLLM()
                llmWrapper.prompt()
                
                self.signals.last_message_time = time.time()

            # Sleep for 0.1 seconds before checking again.
            time.sleep(0.1)
