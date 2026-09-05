import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from backend.services import image_analysis as service


class ImageAnalysisTests(unittest.TestCase):
    def setUp(self):
        buffer = BytesIO()
        Image.new("RGB", (256, 256), "white").save(buffer, "JPEG")
        self.contents = buffer.getvalue()

    def test_filename_and_source_do_not_override_prediction(self):
        with patch.object(service, "predict", return_value=(0.88, {})):
            for name, source in [("passport.jpg", "upload"), ("ai-generated.jpg", "upload"),
                                 ("live-capture-1.jpg", "camera")]:
                with patch('backend.services.liveness.analyze_liveness', return_value={'status': 'NOT_ASSESSED'}):
                    result = service.analyze_image(self.contents, name, source)
                self.assertEqual(result["verdict"], "LIKELY_AI_GENERATED")
                self.assertEqual(result["ai_probability"], 0.88)
                self.assertEqual(result["details"]["facial_biometric_analysis"]["liveness_status"], "NOT_ASSESSED")

    def test_probabilities_are_not_constant(self):
        for probability, verdict in [(0.12, "LIKELY_GENUINE"), (0.5, "UNCERTAIN"), (0.92, "LIKELY_AI_GENERATED")]:
            with patch.object(service, "predict", return_value=(probability, {})):
                result = service.analyze_image(self.contents, "image.jpg")
                self.assertEqual(result["verdict"], verdict)
                self.assertEqual(result["ai_probability"], probability)

    def test_missing_model_never_falls_back_to_heuristics(self):
        with patch.object(service, "predict", side_effect=FileNotFoundError("model")):
            with self.assertLogs(service.__name__, level="ERROR"):
                result = service.analyze_image(self.contents, "fake.jpg")
        self.assertEqual(result["verdict"], "UNCERTAIN")
        self.assertIsNone(result["ai_probability"])
        self.assertIsNone(result["confidence"])

    def test_invalid_image_rejected(self):
        with self.assertRaises(ValueError):
            service.analyze_image(b"not an image", "image.jpg")


if __name__ == "__main__":
    unittest.main()
