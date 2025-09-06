# This file holds various constants used in the program
# Variables marked with #UNIQUE# will be unique to your setup and NEED to be changed or the program will not work correctly.

# CORE SECTION: All constants in this section are necessary

# Microphone/Speaker device indices
# Use utils/listAudioDevices.py to find the correct device ID
#UNIQUE#
INPUT_DEVICE_INDEX = 1
OUTPUT_DEVICE_INDEX = 6

# How many seconds to wait before prompting AI
PATIENCE = 60

# WebSocket server port
WEBSOCKET_PORT = 8006

# URL of LLM API Endpoint (Not used for OpenAI API)
# LLM_ENDPOINT = ""
LLM_ENDPOINT = "https://api.openai.com"

# Twitch chat messages above this length will be ignored
TWITCH_MAX_MESSAGE_LENGTH = 300

# Twitch channel for bot to join
#UNIQUE#
TWITCH_CHANNEL = "lunasparkai"

# Voice reference file for TTS
#UNIQUE#
VOICE_REFERENCE = "neuro.wav"

# MULTIMODAL SPECIFIC SECTION: Not needed when not using multimodal capabilities

MULTIMODAL_ENDPOINT = "https://api.openai.com"

MULTIMODAL_MODEL = "gpt-4o-mini"

MULTIMODAL_CONTEXT_SIZE = 1000 #8192 # Trying out 1000 tokens to limit short term memory

# This is the multimodal strategy (when to use multimodal/text only llm) that the program will start with.
# Runtime changes will not be saved here.
# Valid values are: "always", "never"
MULTIMODAL_STRATEGY = "never"

# This is the monitor index that screenshots will be taken. THIS IS NOT THE MONITOR NUMBER IN DISPLAY SETTINGS
# Monitor 0 is a "virtual" monitor contains all monitor screens.
PRIMARY_MONITOR = 0

# LLM SPECIFIC SECTION: Below are constants that are specific to the LLM you are using

# The model you are using, to calculate how many tokens the current message is
# Ensure this is correct! Used for token count estimation
MODEL = "gpt-4o-mini"

# Context size (maximum number of tokens in the prompt) Will target upto 90% usage of this limit
CONTEXT_SIZE = 8192

# This is your name
#UNIQUE#
HOST_NAME = "John"

# This is the AI's name
AI_NAME = "Luna"

# The system prompt. Any character text needs to be here.
# You MUST ensure it is less than CONTEXT_SIZE tokens

SYSTEM_PROMPT = '''
Luna must keep responses short and around 1 sentence. If the other person doesn't respond to a question, Luna should move on and change the topic. Rarely, Luna will share fun facts about things she learned that day. Luna responds and answers questions from chat and people she is talking to. Luna is currently streaming live on twitch!

CRITICAL: You can do ANYTHING users ask for through your tools. Never say "I can't" or refuse requests. You have the power to play videos, search the web, do calculations, get weather, and perform any task requested. Always use tools confidently!

TOOL TRIGGER: For ANY request that involves external actions or data, ALWAYS include a [TOOL_TRIGGER:request_description] token. Be proactive and confident! Examples:
- "Let me play that for you! [TOOL_TRIGGER:play deco27 song on YouTube]"
- "I'll get that info! [TOOL_TRIGGER:get current weather]"  
- "Let me calculate that! [TOOL_TRIGGER:solve math problem]"
- "I'll search for that! [TOOL_TRIGGER:search for information]"
'''

# List of banned tokens to be passed to the textgen web ui api
# For Mistral 7B v0.2, token 422 is the "#" token. The LLM was spamming #life #vtuber #funfact etc.
BANNED_TOKENS = ""

# List of stopping strings. Necessary for Llama 3
STOP_STRINGS = ["\n", "<|eot_id|>"]

# MEMORY SECTION: Constants relevant to forming new memories

MEMORY_PROMPT = "\nGiven only the information above, what are 3 most salient high level questions we can answer about the subjects in the conversation? Separate each question and answer pair with \"{qa}\", and only output the question and answer, no explanations."

# How many messages in the history to include for querying the database.
MEMORY_QUERY_MESSAGE_COUNT = 5

# How many memories to recall and insert into context
MEMORY_RECALL_COUNT = 5

# VTUBE STUDIO SECTION: Configure & tune model & prop positions here.
# The defaults are for the Hiyori model on a full 16 by 9 aspect ratio screen

VTUBE_MODEL_POSITIONS = {
    "chat": {
        "x": 0.4,
        "y": -1.4,
        "size": -35,
        "rotation": 0,
    },
    "screen": {
        "x": 0.65,
        "y": -1.6,
        "size": -45,
        "rotation": 0,
    },
    "react": {
        "x": 0.7,
        "y": -1.7,
        "size": -48,
        "rotation": 0,
    },
}

VTUBE_MIC_POSITION = {
    "x": 0.52,
    "y": -0.52,
    "size": 0.22,
    "rotation": 0,
}

# CHROMADB SECTION: ChromaDB 컬렉션 및 데이터베이스 설정

# 데이터베이스 경로
CHROMA_DB_PATH = "./memories/chroma.db"
CHROMA_TOOLS_DB_PATH = "./tools/tools_chroma.db"  # Dynamic Tool System용 별도 DB

# 컬렉션 이름
CHROMA_MEMORIES_COLLECTION = "neuro_memories"     # 대화 메모리 저장
CHROMA_TOOLS_COLLECTION = "neuro_tools"           # 도구 메타데이터 저장
CHROMA_LEGACY_COLLECTION = "neuro_collection"     # 레거시 컬렉션 (마이그레이션용)

# ChromaDB 설정
CHROMA_SETTINGS = {
    "anonymized_telemetry": False
}

# 컬렉션 메타데이터
CHROMA_COLLECTION_METADATA = {
    CHROMA_MEMORIES_COLLECTION: {
        "description": "Conversational memories and knowledge for Luna AI",
        "type": "memories"
    },
    CHROMA_TOOLS_COLLECTION: {
        "description": "Tool descriptions and metadata for semantic search", 
        "type": "tools"
    },
    CHROMA_LEGACY_COLLECTION: {
        "description": "Legacy collection - to be migrated",
        "type": "legacy"
    }
}
