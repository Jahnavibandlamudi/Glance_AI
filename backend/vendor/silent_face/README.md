# Silent Face Anti-Spoofing

MiniFASNet.py and generate_patches.py are unmodified upstream files from
https://github.com/minivision-ai/Silent-Face-Anti-Spoofing
at commit b6d5f04ad78778917853b25c778acef6d5626d15. See LICENSE (Apache-2.0).

Weights and the RetinaFace detector are stored in backend/models/antispoof.
They come from resources/anti_spoof_models and resources/detection_model
at that same upstream commit. No camera images are sent to an external service.

Integration follows upstream BGR 0..255 input, 2.7x/4x crops, and class 1=live.
The image-generation model and this presentation-attack model are independent.
Neither verifies identity. Passive liveness scores are not calibrated or
validated for the user's webcam and must not grant access automatically.

Smoke testing: blank input reports NO_FACE; upstream image_F1 is classified
as possible replay and image_T1 as likely live. image_F2 is classified as likely
live despite its F filename. These three samples are not an accuracy benchmark.
