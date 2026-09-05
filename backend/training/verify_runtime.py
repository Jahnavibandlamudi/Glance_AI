"""Exercise the running HTTP service with real files and invalid input."""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def post(contents, filename="image.jpg", source="upload"):
    boundary = "GlanceVerificationBoundary"
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="source"\r\n\r\n{source}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            'Content-Type: image/jpeg\r\n\r\n').encode() + contents + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request("http://127.0.0.1:8010/api/analyze/image", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main():
    dataset = Path("backend/data/raw/140k/real_vs_fake/real-vs-fake/test")
    probabilities = []
    for label in ("real", "fake"):
        for path in list((dataset / label).glob("*.jpg"))[:3]:
            started = time.perf_counter()
            result = post(path.read_bytes())
            assert result["model_status"] == "READY"
            assert result["details"]["ai_generated_image_detection"]["metrics"]["visual_detector_feature_model"] == "efficientnet_b0"
            probabilities.append(result["ai_probability"])
            print(label, path.name, result["verdict"], result["ai_probability"], round(time.perf_counter()-started, 3), flush=True)
    assert len(set(probabilities)) > 1
    contents = next((dataset / "fake").glob("*.jpg")).read_bytes()
    ordinary, passport, camera = post(contents), post(contents, "passport.jpg"), post(contents, "live-capture-1.jpg", "camera")
    assert ordinary["ai_probability"] == passport["ai_probability"] == camera["ai_probability"]
    assert camera["details"]["liveness"]["status"] != "UNAVAILABLE"
    print("Camera check:", camera["details"]["liveness"], flush=True)
    try:
        post(b"invalid image")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("Invalid image accepted")
    schema = json.load(urllib.request.urlopen("http://127.0.0.1:8010/openapi.json"))
    assert not any("video" in path for path in schema["paths"])
    print("HTTP validation, filename/source invariance, variable predictions, camera inference and video removal: PASS")


if __name__ == "__main__":
    main()
