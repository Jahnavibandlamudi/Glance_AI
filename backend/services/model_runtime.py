"""Shared guards for local ML model loading."""
from threading import Lock


MODEL_LOAD_LOCK = Lock()
