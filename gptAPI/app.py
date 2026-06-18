from fastapi import FastAPI

from config import GPT_MODEL
from routes.viewer import router as viewer_router
from routes.brain_mri import router as brain_mri_router
from routes.resume import router as resume_router
from routes.archive import router as archive_router

app = FastAPI(title="GPT API")

app.include_router(viewer_router)
app.include_router(brain_mri_router)
app.include_router(resume_router)
app.include_router(archive_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": "openai",
        "model": GPT_MODEL,
    }
