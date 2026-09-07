from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from typing import Literal
import logging

from services.image_analysis import analyze_image, save_feedback_image

router = APIRouter(prefix="/api/analyze", tags=["image"])
logger = logging.getLogger(__name__)


@router.post("/image")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    source: Literal['upload', 'camera'] = Form('upload'),
    live_frames: list[UploadFile] | None = File(default=None),
):
    contents = await file.read(10 * 1024 * 1024 + 1)
    frame_contents = []
    for frame in live_frames or []:
        frame_contents.append(await frame.read(10 * 1024 * 1024 + 1))
    try:
        return await run_in_threadpool(analyze_image, contents, file.filename, source, frame_contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Image analysis failed")
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {exc}") from exc


@router.post("/image/feedback")
async def save_image_feedback_endpoint(
    label: str = Form(...),
    file: UploadFile = File(...),
):
    contents = await file.read(10 * 1024 * 1024 + 1)
    try:
        return save_feedback_image(contents, file.filename, label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
