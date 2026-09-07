"""Install FaceNet face-match weights into the local Torch cache."""
from pathlib import Path

import torch

from backend.services.face_match import FACENET_WEIGHTS_FILENAME

URL = "https://github.com/timesler/facenet-pytorch/releases/download/v2.2.9/20180402-114759-vggface2.pt"


def main():
    checkpoint_dir = Path(torch.hub.get_dir()).parent / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = checkpoint_dir / FACENET_WEIGHTS_FILENAME
    if checkpoint.exists():
        print(f"FaceNet weights already installed: {checkpoint}")
        return
    print(f"Downloading FaceNet VGGFace2 weights to: {checkpoint}")
    print("This is about 107 MB and can take a few minutes on a slow connection.")
    torch.hub.download_url_to_file(URL, str(checkpoint))
    print("Face Match model setup complete.")


if __name__ == "__main__":
    main()
