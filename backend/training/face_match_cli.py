import argparse
from pathlib import Path

from backend.services.face_match import compare_faces


def main():
    parser = argparse.ArgumentParser(description="Compare two face images without printing embeddings.")
    parser.add_argument("reference_image", type=Path)
    parser.add_argument("selfie_image", type=Path)
    args = parser.parse_args()

    result = compare_faces(args.reference_image.read_bytes(), args.selfie_image.read_bytes())
    if not result.get("success"):
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        raise SystemExit(1)
    print(f"Model: {result['details']['model']}")
    print(f"Metric: {result['details']['metric']}")
    print(f"Similarity: {result['similarity']}")
    print(f"Display score: {result['match_score']}")
    print(f"Decision: {result['decision']}")


if __name__ == "__main__":
    main()
