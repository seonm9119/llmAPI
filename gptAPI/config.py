import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GPT_MODEL = os.environ.get("GPT_MODEL", "gpt-5-mini").strip()
GPT_TIMEOUT = float(os.environ.get("GPT_TIMEOUT", "90"))
VIEWER_MAX_SCHEMA_CHARS = int(os.environ.get("VIEWER_MAX_SCHEMA_CHARS", "24000"))
VIEWER_ADAPTER_CACHE_PATH = os.environ.get("VIEWER_ADAPTER_CACHE_PATH", "/app/cache/viewer_adapter_cache.json")
