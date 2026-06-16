"""STIR-Core: Lightweight spatial task representation for LLMs."""

__version__ = "0.1.0"

from stir_core.models import PointObject, LineObject, RectObject, StirDocument
from stir_core.parser import load_stir, validate_stir
from stir_core.ops import distance_2d, line_intersects_rect
from stir_core.runner import run_stir
from stir_core.normalizer import normalize_model_output
from stir_core.evaluator import evaluate_model_output

__all__ = [
    "__version__",
    "PointObject",
    "LineObject",
    "RectObject",
    "StirDocument",
    "load_stir",
    "validate_stir",
    "distance_2d",
    "line_intersects_rect",
    "run_stir",
    "normalize_model_output",
    "evaluate_model_output",
]
