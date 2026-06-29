import importlib.util
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


BASE_DIR = Path(__file__).resolve().parent
GPT_API_DIR = BASE_DIR / "gptAPI"
QWEN_7B_DIR = BASE_DIR / "qwen2x5_7b"
QWEN_VLM_DIR = BASE_DIR / "qwen2x5-vl-3b"


def prepend_import_path(import_path):
    import_path_text = str(import_path)
    if import_path_text not in sys.path:
        sys.path.insert(0, import_path_text)
        return True
    return False


prepend_import_path(GPT_API_DIR)

from config import GPT_MODEL
from routes.archive import router as archive_router
from routes.brain_mri import router as brain_mri_router
from routes.resume import router as resume_router
from routes.viewer import router as viewer_router


app = FastAPI(title="llm-api", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(viewer_router)
app.include_router(brain_mri_router)
app.include_router(resume_router)
app.include_router(archive_router)


def load_api_module(module_name, api_file_path, import_dirs):
    previous_prompts_module = sys.modules.pop("prompts", None)
    inserted_import_paths = []

    try:
        for import_dir in reversed(import_dirs):
            if prepend_import_path(import_dir):
                inserted_import_paths.append(str(import_dir))

        module_spec = importlib.util.spec_from_file_location(module_name, api_file_path)
        api_module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = api_module
        module_spec.loader.exec_module(api_module)
        return api_module
    finally:
        for import_path_text in inserted_import_paths:
            if import_path_text in sys.path:
                sys.path.remove(import_path_text)

        sys.modules.pop("prompts", None)
        if previous_prompts_module is not None:
            sys.modules["prompts"] = previous_prompts_module


def include_external_api_routes(external_app):
    for external_route in external_app.router.routes:
        if getattr(external_route, "path", "") == "/health":
            continue
        app.router.routes.append(external_route)


def include_api_file_routes(module_name, api_file_path, import_dirs):
    api_module = load_api_module(module_name, api_file_path, import_dirs)
    include_external_api_routes(api_module.app)


include_api_file_routes("qwen2x5_vlm_api", QWEN_VLM_DIR / "api.py", [QWEN_VLM_DIR])
include_api_file_routes("gpt_keyvalue_api", GPT_API_DIR / "keyvalue" / "api.py", [GPT_API_DIR / "keyvalue", GPT_API_DIR])
include_api_file_routes(
    "qwen2x5_keyvalue_api",
    QWEN_7B_DIR / "keyvalue" / "api.py",
    [QWEN_7B_DIR / "keyvalue", QWEN_7B_DIR],
)
include_api_file_routes(
    "qwen2x5_mrv_solution_api",
    QWEN_7B_DIR / "mrv_solution" / "api.py",
    [QWEN_7B_DIR / "mrv_solution", QWEN_7B_DIR],
)


@app.get("/health")
def health():
    return {
        "service": "llm-api",
        "status": "ok",
        "providers": {
            "openai": {
                "model": GPT_MODEL,
            },
            "ollama": {
                "base_url": get_ollama_base_url(),
                "models": {
                    "text": get_ollama_text_model_id(),
                    "vlm": get_ollama_vlm_model_id(),
                },
            },
        },
    }


def get_ollama_base_url():
    return os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").strip().rstrip("/")


def get_ollama_text_model_id():
    return os.environ.get("OLLAMA_TEXT_MODEL_ID", "qwen2.5:7b").strip() or "qwen2.5:7b"


def get_ollama_vlm_model_id():
    return os.environ.get("OLLAMA_VLM_MODEL_ID", "qwen2.5vl:3b").strip() or "qwen2.5vl:3b"
