from fastapi import FastAPI

from config import GPT_MODEL
from routes.viewer import router as viewer_router

app = FastAPI(title="GPT API")

app.include_router(viewer_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "openai",
        "model": GPT_MODEL,
    }
