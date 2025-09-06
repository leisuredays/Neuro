import queue


class Signals:
    def __init__(self):
        # 기존 통합 상태 (하위 호환성)
        self._human_speaking = False
        self._AI_speaking = False
        self._AI_thinking = False
        
        # 개별 LLM 상태
        self._text_llm_thinking = False
        self._tool_llm_thinking = False
        self._image_llm_thinking = False
        
        self._last_message_time = 0.0
        self._new_message = False
        self._tts_ready = False
        self._stt_ready = False
        self._recentTwitchMessages = []
        self._history = []

        # This flag indicates to all threads that they should immediately terminate
        self._terminate = False

        self.sio_queue = queue.SimpleQueue()

    @property
    def human_speaking(self):
        return self._human_speaking

    @human_speaking.setter
    def human_speaking(self, value):
        self._human_speaking = value
        self.sio_queue.put(('human_speaking', value))
        if value:
            print("SIGNALS: Human Talking Start")
        else:
            print("SIGNALS: Human Talking Stop")

    @property
    def AI_speaking(self):
        return self._AI_speaking

    @AI_speaking.setter
    def AI_speaking(self, value):
        self._AI_speaking = value
        self.sio_queue.put(('AI_speaking', value))
        if value:
            print("SIGNALS: AI Talking Start")
        else:
            print("SIGNALS: AI Talking Stop")

    @property
    def AI_thinking(self):
        return self._AI_thinking

    @AI_thinking.setter
    def AI_thinking(self, value):
        self._AI_thinking = value
        self.sio_queue.put(('AI_thinking', value))
        if value:
            print("SIGNALS: AI Thinking Start")
        else:
            print("SIGNALS: AI Thinking Stop")

    @property
    def last_message_time(self):
        return self._last_message_time

    @last_message_time.setter
    def last_message_time(self, value):
        self._last_message_time = value

    @property
    def new_message(self):
        return self._new_message

    @new_message.setter
    def new_message(self, value):
        self._new_message = value
        if value:
            print("SIGNALS: New Message")

    @property
    def tts_ready(self):
        return self._tts_ready

    @tts_ready.setter
    def tts_ready(self, value):
        self._tts_ready = value

    @property
    def stt_ready(self):
        return self._stt_ready

    @stt_ready.setter
    def stt_ready(self, value):
        self._stt_ready = value

    @property
    def recentTwitchMessages(self):
        return self._recentTwitchMessages

    @recentTwitchMessages.setter
    def recentTwitchMessages(self, value):
        self._recentTwitchMessages = value
        self.sio_queue.put(('recent_twitch_messages', value))

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, value):
        self._history = value

    @property
    def terminate(self):
        return self._terminate

    @terminate.setter
    def terminate(self, value):
        self._terminate = value

    # 개별 LLM 상태 관리
    @property
    def text_llm_thinking(self):
        return self._text_llm_thinking

    @text_llm_thinking.setter
    def text_llm_thinking(self, value):
        self._text_llm_thinking = value
        self.sio_queue.put(('text_llm_thinking', value))
        if value:
            print("SIGNALS: Text LLM Thinking Start")
        else:
            print("SIGNALS: Text LLM Thinking Stop")
        self._update_combined_thinking()

    @property
    def tool_llm_thinking(self):
        return self._tool_llm_thinking

    @tool_llm_thinking.setter
    def tool_llm_thinking(self, value):
        self._tool_llm_thinking = value
        self.sio_queue.put(('tool_llm_thinking', value))
        if value:
            print("SIGNALS: Tool LLM Thinking Start")
        else:
            print("SIGNALS: Tool LLM Thinking Stop")
        self._update_combined_thinking()

    @property
    def image_llm_thinking(self):
        return self._image_llm_thinking

    @image_llm_thinking.setter
    def image_llm_thinking(self, value):
        self._image_llm_thinking = value
        self.sio_queue.put(('image_llm_thinking', value))
        if value:
            print("SIGNALS: Image LLM Thinking Start")
        else:
            print("SIGNALS: Image LLM Thinking Stop")
        self._update_combined_thinking()

    def _update_combined_thinking(self):
        """개별 LLM 상태를 기반으로 통합 AI_thinking 상태 업데이트"""
        new_thinking = (self._text_llm_thinking or 
                       self._tool_llm_thinking or 
                       self._image_llm_thinking)
        
        if new_thinking != self._AI_thinking:
            self._AI_thinking = new_thinking
            self.sio_queue.put(('AI_thinking', new_thinking))
            if new_thinking:
                print("SIGNALS: AI Thinking Start (Combined)")
            else:
                print("SIGNALS: AI Thinking Stop (Combined)")

    def get_thinking_status(self):
        """현재 thinking 상태 요약"""
        active = []
        if self._text_llm_thinking:
            active.append("text")
        if self._tool_llm_thinking:
            active.append("tool")
        if self._image_llm_thinking:
            active.append("image")
        
        return {
            "combined": self._AI_thinking,
            "active_llms": active,
            "text": self._text_llm_thinking,
            "tool": self._tool_llm_thinking,
            "image": self._image_llm_thinking
        }
