"""GeoTask Core: Lightweight spatial task representation for LLMs.

STIR was the original prototype name. The project has been renamed to GeoTask.
Old import paths (stir_core.*) are still supported as deprecated aliases.
"""

__version__ = "0.1.0"

from geotask_core.models import PointObject, LineObject, RectObject, StirDocument
from geotask_core.parser import load_geotask, validate_geotask, load_stir, validate_stir
from geotask_core.ops import distance_2d, line_intersects_rect
from geotask_core.runner import run_geotask, run_stir
from geotask_core.normalizer import normalize_model_output
from geotask_core.evaluator import evaluate_model_output

__all__ = [
    "__version__",
    "PointObject",
    "LineObject",
    "RectObject",
    "StirDocument",
    "load_geotask",
    "validate_geotask",
    "load_stir",
    "validate_stir",
    "distance_2d",
    "line_intersects_rect",
    "run_geotask",
    "run_stir",
    "normalize_model_output",
    "evaluate_model_output",
]
