from pydantic import BaseModel
from typing import Any
from enum import Enum

def to_serializable(obj: Any) -> Any:
    """
    Recursively converts any object (Pydantic models, Enums, dicts, lists, etc.)
    into a fully JSON-serializable form.
    - Enum -> .value
    - BaseModel -> dict with all fields serialized recursively
    - Custom objects -> vars() recursively
    """
    if isinstance(obj, Enum):
        return obj.value  # critical: always serialize enum to value

    if isinstance(obj, BaseModel):
        # recursively serialize the dict from model_dump
        return {k: to_serializable(v) for k, v in obj.model_dump().items()}

    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(item) for item in obj]

    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    if hasattr(obj, "__dict__"):
        return to_serializable(vars(obj))

    try:
        return str(obj)
    except Exception:
        return "<unserializable>"

def clean_output_structure(result: Any) -> dict:
    """
    Cleans a Flow/Agent result into a fully JSON-serializable dictionary.
    All Enums converted to values, all models flattened.
    """
    return to_serializable(result)
