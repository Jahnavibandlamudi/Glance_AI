from fastapi import APIRouter, File, UploadFile

from services.image_analysis import analyze_image

router = APIRouter(prefix="/api/analyze", tags=["image"])


@router.post("/image")
async def analyze_image_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    return analyze_image(contents, file.filename)
