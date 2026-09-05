"""Download pinned upstream anti-spoofing assets and verify their hashes."""
import hashlib
import urllib.request
from pathlib import Path

REVISION = "b6d5f04ad78778917853b25c778acef6d5626d15"
BASE = f"https://raw.githubusercontent.com/minivision-ai/Silent-Face-Anti-Spoofing/{REVISION}/resources"
FILES = {
    "anti_spoof_models/2.7_80x80_MiniFASNetV2.pth": "a5eb02e1843f19b5386b953cc4c9f011c3f985d0ee2bb9819eea9a142099bec0",
    "anti_spoof_models/4_0_0_80x80_MiniFASNetV1SE.pth": "84ee1d37d96894d5e82de5a57df044ef80a58be2b218b5ed7cdfd875ec2f5990",
    "detection_model/Widerface-RetinaFace.caffemodel": "d08338a2c207df16a9c566f767fea67fb43ba6fff76ce11e938fe3fabefb9402",
    "detection_model/deploy.prototxt": "9fe2f141b4baee039ed9442da2833e216af40a6ff3e639e7b39258812bcda808",
}


def main():
    folder = Path(__file__).resolve().parents[1] / "models" / "antispoof"
    folder.mkdir(parents=True, exist_ok=True)
    for path, digest in FILES.items():
        target = folder / Path(path).name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            print(f"Verified {target.name}")
            continue
        with urllib.request.urlopen(f"{BASE}/{path}", timeout=60) as response:
            contents = response.read()
        if hashlib.sha256(contents).hexdigest() != digest:
            raise ValueError(f"Hash mismatch for {path}")
        target.write_bytes(contents)
        print(f"Installed {target.name}")


if __name__ == "__main__":
    main()
