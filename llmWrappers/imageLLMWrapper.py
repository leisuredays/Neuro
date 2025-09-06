import os
import mss, cv2, base64
import numpy as np
import tiktoken
from constants import *
from llmWrappers.abstractLLMWrapper import AbstractLLMWrapper


class ImageLLMWrapper(AbstractLLMWrapper):

    def __init__(self, signals, tts, llmState, modules=None):
        super().__init__(signals, tts, llmState, modules)
        self.SYSTEM_PROMPT = SYSTEM_PROMPT
        self.LLM_ENDPOINT = MULTIMODAL_ENDPOINT
        self.CONTEXT_SIZE = MULTIMODAL_CONTEXT_SIZE
        self.tokenizer = tiktoken.encoding_for_model(MODEL)

        # Use separate API key for image LLM
        self.image_api_key = os.environ.get('OPENAI_IMAGE_API_KEY', os.environ.get('OPENAI_API_KEY'))
        self.headers = {
            "Authorization": f"Bearer {self.image_api_key}",
            "Content-Type": "application/json"
        }

        self.MSS = None

    def screen_shot(self):
        # Create new MSS instance for each call to avoid thread issues
        local_mss = mss.mss()
        
        # Take a screenshot of the main screen
        frame_bytes = local_mss.grab(local_mss.monitors[PRIMARY_MONITOR])

        frame_array = np.array(frame_bytes)
        # resize
        frame_resized = cv2.resize(frame_array, (1920, 1080), interpolation=cv2.INTER_CUBIC)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        result, frame_encoded = cv2.imencode('.jpg', frame_resized, encode_param)
        # base64
        frame_base64 = base64.b64encode(frame_encoded).decode("utf-8")
        return frame_base64

    def prepare_payload(self):
        return {
            "model": "gpt-4o-mini",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.generate_prompt()
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{self.screen_shot()}"
                        }
                    }
                ]
            }],
            "max_tokens": 200,
            "stream": True
        }
