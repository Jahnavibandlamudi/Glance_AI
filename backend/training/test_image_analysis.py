import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from backend.services import image_analysis as service
from backend.services import liveness


class ImageAnalysisTests(unittest.TestCase):
    def setUp(self):
        buffer = BytesIO()
        Image.new("RGB", (256, 256), "white").save(buffer, "JPEG")
        self.contents = buffer.getvalue()

    def test_filename_and_source_do_not_override_prediction(self):
        with patch.object(service, "predict", return_value=(0.88, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                for name, source in [("passport.jpg", "upload"), ("ai-generated.jpg", "upload")]:
                    with patch('backend.services.liveness.analyze_liveness_sequence', return_value={'status': 'NOT_ASSESSED', 'live_confirmed': False}):
                        result = service.analyze_image(self.contents, name, source)
                    self.assertEqual(result["verdict"], "LIKELY_AI_GENERATED")
                    self.assertEqual(result["ai_probability"], 0.88)
                    self.assertEqual(result["details"]["facial_biometric_analysis"]["liveness_status"], "NOT_ASSESSED")

    def test_probabilities_are_not_constant(self):
        for probability, verdict in [(0.12, "LIKELY_GENUINE"), (0.5, "LIKELY_AI_GENERATED"),
                                     (0.53, "LIKELY_AI_GENERATED"), (0.92, "LIKELY_AI_GENERATED")]:
            with patch.object(service, "predict", return_value=(probability, {})):
                with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                    result = service.analyze_image(self.contents, "image.jpg")
                    self.assertEqual(result["verdict"], verdict)
                    self.assertEqual(result["ai_probability"], probability)

    def test_identity_upload_context_requires_review_when_otherwise_genuine(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                for name in ["passport size photo.jpeg", "student ID card.jpeg", "aadhar full.jpeg"]:
                    result = service.analyze_image(self.contents, name, "upload")
                    self.assertEqual(result["verdict"], "UNCERTAIN")
                    self.assertTrue(result["details"]["forensic_analysis"]["metadata"]["identity_upload_context"])

    def test_identity_upload_context_does_not_hide_ai_detection(self):
        with patch.object(service, "predict", return_value=(0.51, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                result = service.analyze_image(self.contents, "passport size photo.jpeg", "upload")
        self.assertEqual(result["verdict"], "LIKELY_AI_GENERATED")

    def test_ordinary_real_photo_stays_genuine(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                result = service.analyze_image(self.contents, "formal pic.jpeg", "upload")
        self.assertEqual(result["verdict"], "LIKELY_GENUINE")
        self.assertFalse(result["details"]["forensic_analysis"]["metadata"]["identity_upload_context"])

    def test_high_synthetic_domain_score_handles_photo_detector_blind_spot(self):
        with patch.object(service, "predict", return_value=(0.11, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.99, {"thresholds": {"high_synthetic_min_probability": 0.98}})):
                result = service.analyze_image(self.contents, "image.jpg")
        self.assertEqual(result["verdict"], "LIKELY_AI_GENERATED")
        self.assertEqual(result["confidence"], 99.0)
        self.assertEqual(result["details"]["ai_generated_image_detection"]["metrics"]["synthetic_domain_probability"], 0.99)

    def test_missing_model_never_falls_back_to_heuristics(self):
        with patch.object(service, "predict", side_effect=FileNotFoundError("model")):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                with self.assertLogs(service.__name__, level="ERROR"):
                    result = service.analyze_image(self.contents, "fake.jpg")
        self.assertEqual(result["verdict"], "UNCERTAIN")
        self.assertIsNone(result["ai_probability"])
        self.assertIsNone(result["confidence"])

    def test_camera_genuine_requires_confirmed_liveness(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                with patch('backend.services.liveness.analyze_liveness_sequence', return_value={
                    'status': 'ASSESSED',
                    'prediction': 'LIVE_NOT_CONFIRMED',
                    'live_probability': 0.91,
                    'spoof_probability': 0.09,
                    'live_confirmed': False,
                    'message': 'Live presence is uncertain.',
                }):
                    result = service.analyze_image(self.contents, "live.jpg", "camera", [self.contents] * 3)
        self.assertEqual(result["verdict"], "UNCERTAIN")
        self.assertIn("live presence could not be verified", result["message"])

    def test_camera_ai_score_requires_liveness_or_strong_synthetic_evidence(self):
        with patch.object(service, "predict", return_value=(0.83, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.2, {})):
                with patch('backend.services.liveness.analyze_liveness_sequence', return_value={
                    'status': 'ASSESSED',
                    'prediction': 'LIVE_NOT_CONFIRMED',
                    'live_probability': 0.55,
                    'spoof_probability': 0.45,
                    'live_confirmed': False,
                    'message': 'Live presence is uncertain.',
                }):
                    result = service.analyze_image(self.contents, "live.jpg", "camera", [self.contents] * 3)
        self.assertEqual(result["verdict"], "UNCERTAIN")
        self.assertIn("live presence could not be verified", result["message"])

    def test_camera_strong_synthetic_evidence_stays_ai(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.99, {"thresholds": {"high_synthetic_min_probability": 0.98}})):
                with patch('backend.services.liveness.analyze_liveness_sequence', return_value={
                    'status': 'ASSESSED',
                    'prediction': 'LIKELY_LIVE',
                    'live_probability': 0.99,
                    'spoof_probability': 0.01,
                    'live_confirmed': True,
                    'message': 'Live presence confirmed.',
                }):
                    result = service.analyze_image(self.contents, "live.jpg", "camera", [self.contents] * 3)
        self.assertEqual(result["verdict"], "LIKELY_AI_GENERATED")

    def test_camera_genuine_allowed_when_liveness_confirmed(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                with patch('backend.services.liveness.analyze_liveness_sequence', return_value={
                    'status': 'ASSESSED',
                    'prediction': 'LIKELY_LIVE',
                    'live_probability': 0.99,
                    'spoof_probability': 0.01,
                    'live_confirmed': True,
                    'message': 'Live presence confirmed.',
                }):
                    result = service.analyze_image(self.contents, "live.jpg", "camera", [self.contents] * 3)
        self.assertEqual(result["verdict"], "LIKELY_GENUINE")

    def test_camera_liveness_can_resolve_uncertain_model_result(self):
        with patch.object(service, "predict", return_value=(0.5, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                with patch('backend.services.liveness.analyze_liveness_sequence', return_value={
                    'status': 'ASSESSED',
                    'prediction': 'LIKELY_LIVE',
                    'live_probability': 0.71,
                    'spoof_probability': 0.29,
                    'live_confirmed': True,
                    'message': 'Live presence confirmed.',
                }):
                    result = service.analyze_image(self.contents, "live.jpg", "camera", [self.contents] * 3)
        self.assertEqual(result["verdict"], "LIKELY_GENUINE")

    def test_camera_drops_bad_extra_live_frames(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                with patch('backend.services.liveness.analyze_liveness_sequence', return_value={
                    'status': 'ASSESSED',
                    'prediction': 'LIKELY_LIVE',
                    'live_probability': 0.99,
                    'spoof_probability': 0.01,
                    'live_confirmed': True,
                    'message': 'Live presence confirmed.',
                }) as liveness_mock:
                    result = service.analyze_image(
                        self.contents,
                        "live.jpg",
                        "camera",
                        [b"not an image", self.contents, self.contents],
                    )
        self.assertEqual(result["verdict"], "LIKELY_GENUINE")
        self.assertIn("webcam frame(s) could not be decoded", result["details"]["ai_generated_image_detection"]["warnings"][0])
        self.assertEqual(len(liveness_mock.call_args.args[0]), 2)

    def test_camera_liveness_failure_returns_uncertain_not_error(self):
        with patch.object(service, "predict", return_value=(0.12, {})):
            with patch.object(service, "predict_synthetic_domain", return_value=(0.01, {})):
                with patch('backend.services.liveness.analyze_liveness_sequence', side_effect=RuntimeError("camera model failed")):
                    with self.assertLogs(service.__name__, level="ERROR"):
                        result = service.analyze_image(self.contents, "live.jpg", "camera", [self.contents] * 3)
        self.assertEqual(result["verdict"], "UNCERTAIN")
        self.assertEqual(result["details"]["liveness"]["status"], "UNAVAILABLE")
        self.assertIn("Live presence could not be verified", result["details"]["liveness"]["message"])

    def test_liveness_sequence_allows_one_weak_frame(self):
        frame = Image.new("RGB", (256, 256), "white")
        results = [
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.8},
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.7},
            {'status': 'NO_FACE', 'live_probability': None},
        ]
        with patch.object(liveness, "analyze_liveness", side_effect=results):
            with patch.object(liveness, "_frame_motion", return_value=0.5):
                result = liveness.analyze_liveness_sequence([frame, frame, frame])
        self.assertTrue(result["live_confirmed"])
        self.assertEqual(result["assessed_frame_count"], 2)

    def test_liveness_sequence_accepts_high_confidence_live_without_large_motion(self):
        frame = Image.new("RGB", (256, 256), "white")
        results = [
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.94},
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.92},
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.95},
        ]
        with patch.object(liveness, "analyze_liveness", side_effect=results):
            with patch.object(liveness, "_frame_motion", return_value=0.0):
                result = liveness.analyze_liveness_sequence([frame, frame, frame])
        self.assertTrue(result["live_confirmed"])
        self.assertEqual(result["prediction"], "LIKELY_LIVE")
        self.assertIn("high anti-spoof confidence", result["message"])

    def test_liveness_sequence_keeps_medium_confidence_still_frame_uncertain(self):
        frame = Image.new("RGB", (256, 256), "white")
        results = [
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.74},
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.73},
            {'status': 'ASSESSED', 'prediction': 'LIKELY_LIVE', 'live_probability': 0.75},
        ]
        with patch.object(liveness, "analyze_liveness", side_effect=results):
            with patch.object(liveness, "_frame_motion", return_value=0.0):
                result = liveness.analyze_liveness_sequence([frame, frame, frame])
        self.assertFalse(result["live_confirmed"])
        self.assertEqual(result["prediction"], "POSSIBLE_PRESENTATION_ATTACK")

    def test_invalid_image_rejected(self):
        with self.assertRaises(ValueError):
            service.analyze_image(b"not an image", "image.jpg")


if __name__ == "__main__":
    unittest.main()
