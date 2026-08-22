"""Bounded image contracts shared by vision nodes."""

from __future__ import annotations

import numpy as np

MAX_IMAGE_PIXELS = 32_000_000
SUPPORTED_IMAGE_KINDS = {"u", "f"}
SUPPORTED_CHANNELS = {1, 3}


def validate_image(
    value: object,
    *,
    name: str = "Image",
    max_pixels: int = MAX_IMAGE_PIXELS,
) -> np.ndarray:
    """Return an image after enforcing the bounded runtime contract."""
    if not isinstance(value, np.ndarray):
        raise ValueError(f"{name} must be a NumPy array.")
    if value.ndim not in {2, 3} or value.size == 0:
        raise ValueError(f"{name} must be a non-empty two- or three-dimensional image.")
    if value.ndim == 3 and value.shape[2] not in SUPPORTED_CHANNELS:
        raise ValueError(f"{name} must have one or three channels.")
    if value.shape[0] * value.shape[1] > max_pixels:
        raise ValueError(f"{name} exceeds the {max_pixels:,}-pixel limit.")
    if value.dtype.kind not in SUPPORTED_IMAGE_KINDS or value.dtype.itemsize > 8:
        raise ValueError(f"{name} dtype is unsupported.")
    if not np.all(np.isfinite(value)):
        raise ValueError(f"{name} values must be finite.")
    if value.dtype.kind == "f" and (float(value.min()) < 0.0 or float(value.max()) > 1.0):
        raise ValueError(f"{name} floating values must be between zero and one.")
    return value


def require_matching_images(first: np.ndarray, second: np.ndarray, *, first_name: str, second_name: str) -> None:
    """Require matching image metadata for pairwise vision operations."""
    if first.shape != second.shape:
        raise ValueError(f"{first_name} and {second_name} shape must match.")
    if first.dtype != second.dtype:
        raise ValueError(f"{first_name} and {second_name} dtype must match.")


def bounded_map(value: np.ndarray) -> np.ndarray:
    """Convert an anomaly map to finite float32 values in [0, 1]."""
    return np.nan_to_num(np.clip(value, 0.0, 1.0), nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)


def bounded_score(value: object) -> float:
    """Return a finite score clamped to [0, 1]."""
    score = float(value)
    if not np.isfinite(score):
        raise ValueError("Score must be finite.")
    return float(np.clip(score, 0.0, 1.0))