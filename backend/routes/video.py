from fastapi import APIRouter, File, UploadFile

from services.video_analysis import analyze_video

router = APIRouter(prefix="/api/analyze", tags=["video"])


@router.post("/video")
async def analyze_video_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    return analyze_video(contents, file.filename)
