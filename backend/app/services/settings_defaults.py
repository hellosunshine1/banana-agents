DEFAULT_LLM_CONFIGS = {
    "DeepSeek V4 Flash": {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "interface_format": "DeepSeek",
        "model_name": "deepseek-v4-flash",
        "temperature": 0.7,
        "max_tokens": 8192,
        "timeout": 600,
    },
    "OpenAI GPT": {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "interface_format": "OpenAI",
        "model_name": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 8192,
        "timeout": 600,
    },
}

DEFAULT_EMBEDDING_CONFIGS = {
    "OpenAI": {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "interface_format": "OpenAI",
        "model_name": "text-embedding-3-small",
        "retrieval_k": 4,
        "timeout": 600,
    },
}

DEFAULT_CHOOSE_CONFIGS = {
    "architecture_llm": "DeepSeek V4 Flash",
    "chapter_outline_llm": "DeepSeek V4 Flash",
    "prompt_draft_llm": "DeepSeek V4 Flash",
    "final_chapter_llm": "DeepSeek V4 Flash",
    "consistency_review_llm": "DeepSeek V4 Flash",
}


def default_app_settings_payload() -> dict:
    return {
        "llm_configs": DEFAULT_LLM_CONFIGS,
        "embedding_configs": DEFAULT_EMBEDDING_CONFIGS,
        "choose_configs": DEFAULT_CHOOSE_CONFIGS,
    }
