from pydantic import BaseModel
from typing import Any


def to_serializable(obj: Any) -> Any:
    """
    Recursively convert any object (including Pydantic models, custom classes, etc.)
    into a serializable dictionary or primitive type for JSON compatibility.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()

    if isinstance(obj, dict):
        return {key: to_serializable(value) for key, value in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(item) for item in obj]

    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    if hasattr(obj, "__dict__"):
        return to_serializable(vars(obj))

    # Eğer str'e çevrilebiliyorsa en son çare
    try:
        return str(obj)
    except Exception:
        return "<unserializable>"


def clean_output_structure(result: dict) -> dict:
    # Utility function to remove Output Errors etc.
    return to_serializable(result)
