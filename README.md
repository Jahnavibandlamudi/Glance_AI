# Glance AI

Glance is a local KYC evidence review app for image authenticity, live capture review, and face-match identity similarity.

## Face Match

Face Match compares a reference or ID photograph with a live selfie. It detects exactly one face in each image, creates a face embedding for each detected face, normalizes the embeddings, and compares them using cosine similarity.

This does not prove legal identity. It only estimates whether the two visible facial representations are similar enough for a KYC review workflow.

## Model Used

Face Match uses `facenet-pytorch` with `InceptionResnetV1(pretrained="vggface2")` and MTCNN face detection.

This was selected because the project already uses PyTorch locally and the environment is Windows with Python 3.14, where dlib-based face-recognition packages are fragile. FaceNet provides a real pretrained face-embedding path without a paid external API.

The pretrained VGGFace2 weights are downloaded by `facenet-pytorch` on first model initialization and cached locally by PyTorch.

## Similarity Metric

Embeddings are L2-normalized and compared with cosine similarity.

The API returns:

- `similarity`: raw cosine similarity from the embeddings.
- `match_score`: a UI display score calculated as `clamp((similarity + 1) / 2, 0, 1) * 100`.

`match_score` is not a calibrated probability.

## Thresholds

Initial defaults:

- `FACE_MATCH_THRESHOLD=0.78`
- `FACE_REVIEW_THRESHOLD=0.62`

Decision rules:

- `similarity >= FACE_MATCH_THRESHOLD`: `MATCH`
- `FACE_REVIEW_THRESHOLD <= similarity < FACE_MATCH_THRESHOLD`: `REVIEW`
- `similarity < FACE_REVIEW_THRESHOLD`: `MISMATCH`

These thresholds must be calibrated with a representative validation dataset before production use.

## Privacy

The face-match API processes images in memory.

It does not:

- permanently save uploaded ID photos
- permanently save selfies
- return embeddings
- log embeddings

## Install Dependencies

```bash
python -m pip install -r backend/requirements.txt
```

If `facenet-pytorch` dependency resolution conflicts with this newer Torch/Python setup, install it without changing existing Torch packages:

```bash
python -m pip install facenet-pytorch --no-deps
```

## Start Backend

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

Health:

```bash
curl http://127.0.0.1:8010/api/health
```

## Start Frontend

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5175
```

Open:

```text
http://127.0.0.1:5175/
```

## Face Match API

```bash
curl -X POST http://127.0.0.1:8010/api/verify/face-match ^
  -F "reference_image=@path/to/id-photo.jpg" ^
  -F "selfie_image=@path/to/live-selfie.jpg"
```

## CLI Test

```bash
python -m backend.training.face_match_cli path/to/id-photo.jpg path/to/selfie.jpg
```

The CLI prints model, metric, similarity, display score, and decision. It does not print embeddings.

## Limitations

Face Match, AI-image detection, and liveness are separate evidence categories. Do not blindly average them.

Remaining production work:

- calibrate thresholds on a representative dataset
- validate liveness on the actual webcam/device setup
- collect spoof samples such as screen replay and printed photos
- add human review policy for `REVIEW` and `MISMATCH` outcomes
