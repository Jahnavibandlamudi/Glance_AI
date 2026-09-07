import sys
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
for _path in (_PROJECT_ROOT, _BACKEND_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from routes.image import router as image_router
from routes.verify import router as verify_router

app = FastAPI(title="Glance_AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(image_router)
app.include_router(verify_router)


@app.on_event("startup")
def warm_local_models():
    """Load local ML models before the first user request hits a timeout."""
    try:
        from PIL import Image
        from services.image_analysis import predict, predict_synthetic_domain

        warmup_image = Image.new("RGB", (256, 256), "white")
        predict(warmup_image)
        predict_synthetic_domain(warmup_image)
    except Exception:
        logging.getLogger(__name__).exception("Image model warmup failed")
    try:
        from services.face_match import load_face_models
        from services.liveness import load_models

        load_face_models()
        load_models()
    except Exception:
        logging.getLogger(__name__).exception("Identity model warmup failed")


@app.get("/")
def root():
    return {"status": "ok", "service": "Glance_AI"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}
