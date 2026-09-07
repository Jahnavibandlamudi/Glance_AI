import unittest
from io import BytesIO
from unittest.mock import patch

import numpy as np
from PIL import Image

from backend.services import face_match


def image_bytes(size=(256, 256), color="white"):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, "JPEG")
    return buffer.getvalue()


class FaceMatchTests(unittest.TestCase):
    def test_same_person_match_from_embeddings(self):
        embedding = np.array([1.0, 0.0, 0.0], dtype="float32")
        with patch.object(face_match, "detect_face_embedding", return_value=face_match.FaceEmbeddingResult(1, embedding)):
            with patch.object(face_match, "analyze_liveness_sequence", return_value={"live_confirmed": True, "prediction": "LIKELY_LIVE"}):
                result = face_match.compare_faces(image_bytes(), image_bytes(), [image_bytes()] * 3)
        self.assertTrue(result["success"])
        self.assertEqual(result["decision"], "MATCH")
        self.assertEqual(result["similarity"], 1.0)
        self.assertTrue(result["liveness"]["live_confirmed"])

    def test_same_person_without_liveness_is_review(self):
        embedding = np.array([1.0, 0.0, 0.0], dtype="float32")
        with patch.object(face_match, "detect_face_embedding", return_value=face_match.FaceEmbeddingResult(1, embedding)):
            with patch.object(face_match, "analyze_liveness_sequence", return_value={"live_confirmed": False, "prediction": "LIVE_NOT_CONFIRMED"}):
                result = face_match.compare_faces(image_bytes(), image_bytes(), [image_bytes()] * 3)
        self.assertTrue(result["success"])
        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(result["risk_level"], "MEDIUM")

    def test_different_people_mismatch_from_embeddings(self):
        reference = face_match.FaceEmbeddingResult(1, np.array([1.0, 0.0, 0.0], dtype="float32"))
        selfie = face_match.FaceEmbeddingResult(1, np.array([0.0, 1.0, 0.0], dtype="float32"))
        with patch.object(face_match, "detect_face_embedding", side_effect=[reference, selfie]):
            with patch.object(face_match, "analyze_liveness_sequence", return_value={"live_confirmed": False, "prediction": "LIVE_NOT_CONFIRMED"}):
                result = face_match.compare_faces(image_bytes(), image_bytes(), [image_bytes()] * 3)
        self.assertTrue(result["success"])
        self.assertEqual(result["decision"], "MISMATCH")
        self.assertEqual(result["risk_level"], "HIGH")

    def test_review_band_from_embeddings(self):
        reference = face_match.FaceEmbeddingResult(1, np.array([1.0, 0.0, 0.0], dtype="float32"))
        selfie = face_match.FaceEmbeddingResult(1, np.array([0.7, 0.71414286, 0.0], dtype="float32"))
        with patch.object(face_match, "detect_face_embedding", side_effect=[reference, selfie]):
            with patch.object(face_match, "analyze_liveness_sequence", return_value={"live_confirmed": False, "prediction": "LIVE_NOT_CONFIRMED"}):
                result = face_match.compare_faces(image_bytes(), image_bytes(), [image_bytes()] * 3)
        self.assertTrue(result["success"])
        self.assertEqual(result["decision"], "REVIEW")

    def test_no_face(self):
        with patch.object(face_match, "detect_face_embedding", return_value=face_match.FaceEmbeddingResult(0)):
            result = face_match.compare_faces(image_bytes(), image_bytes())
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "NO_FACE")

    def test_multiple_faces(self):
        with patch.object(face_match, "detect_face_embedding", return_value=face_match.FaceEmbeddingResult(2)):
            result = face_match.compare_faces(image_bytes(), image_bytes())
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "MULTIPLE_FACES")

    def test_invalid_image(self):
        result = face_match.compare_faces(b"not an image", image_bytes())
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "INVALID_IMAGE")

    def test_very_small_image(self):
        result = face_match.compare_faces(image_bytes((80, 80)), image_bytes())
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "IMAGE_TOO_SMALL")


if __name__ == "__main__":
    unittest.main()
