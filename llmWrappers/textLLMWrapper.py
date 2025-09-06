import os
import tiktoken
from constants import *
from llmWrappers.abstractLLMWrapper import AbstractLLMWrapper


class TextLLMWrapper(AbstractLLMWrapper):

    def __init__(self, signals, tts, llmState, modules=None):
        super().__init__(signals, tts, llmState, modules)
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.LLM_ENDPOINT = LLM_ENDPOINT
        self.CONTEXT_SIZE = CONTEXT_SIZE
        self.tokenizer = tiktoken.encoding_for_model(MODEL)

    def prepare_payload(self):
        return {
            "model": MODEL,
            "messages": [{
                "role": "user",
                "content": self.generate_prompt()
            }],
            "max_tokens": 200,
            "stream": True,
            "stop": STOP_STRINGS
        }