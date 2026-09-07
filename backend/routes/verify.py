from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from services.face_match import compare_faces

router = APIRouter(prefix="/api/verify", tags=["verify"])


@router.post("/face-match")
async def face_match_endpoint(
    reference_image: UploadFile = File(...),
    selfie_image: UploadFile = File(...),
    selfie_live_frames: list[UploadFile] | None = File(default=None),
):
    reference = await reference_image.read(10 * 1024 * 1024 + 1)
    selfie = await selfie_image.read(10 * 1024 * 1024 + 1)
    live_frames = []
    for frame in selfie_live_frames or []:
        live_frames.append(await frame.read(10 * 1024 * 1024 + 1))
    result = await run_in_threadpool(compare_faces, reference, selfie, live_frames)
    if not result.get("success"):
        status_code = 503 if result.get("status") == "MODEL_UNAVAILABLE" else 400
        raise HTTPException(status_code=status_code, detail=result)
    return result
