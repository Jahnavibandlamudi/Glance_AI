from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from typing import Literal

from services.image_analysis import analyze_image, save_feedback_image

router = APIRouter(prefix="/api/analyze", tags=["image"])


@router.post("/image")
async def analyze_image_endpoint(file: UploadFile = File(...), source: Literal['upload', 'camera'] = Form('upload')):
    contents = await file.read(10 * 1024 * 1024 + 1)
    try:
        return await run_in_threadpool(analyze_image, contents, file.filename, source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
