import re
from typing import Any
from dataclasses import fields
from chainless._utils.exception import ChainlessError
from chainless.models import ModelNames


def dataclasses_no_defaults_repr(self: Any) -> str:
    """Exclude fields with values equal to the field default."""
    kv_pairs = (
        f'{f.name}={getattr(self, f.name)!r}' for f in fields(self) if f.repr and getattr(self, f.name) != f.default
    )
    return f'{self.__class__.__qualname__}({", ".join(kv_pairs)})'

def validate_name(name: str, entity: str = "name"):
    """
    Validates that the given name is in a safe format (e.g. step1, step_1, Step1).
    Rejects spaces, special chars except underscore.

    Args:
        name (str): Name to validate.
        entity (str): What is being validated (for error messages).

    Raises:
        ValueError: If the name format is invalid.
    """
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(
            f"Invalid {entity}: '{name}'. Must match ^[A-Za-z_][A-Za-z0-9_]*$"
        )


def validate_model(value, agent_name: str):
    """
    Normalize and validate model input.
    Accepts:
        - ModelNames enum → returns enum.value
        - string → returns string
    Rejects:
        - any other type
    """
    # Enum → normalize to string
    if isinstance(value, ModelNames):
        return value.value

    # string → direct accept
    if isinstance(value, str):
        return value

    # illegal types
    raise ChainlessError(
        message=(
            f"Invalid model provided to agent '{agent_name}'. "
            f"Model must be either a string or a ModelNames enum.\n"
            f"Received type: {type(value).__name__!r} with value: {value!r}"
        ),
        error_code="InvalidModel",
    )
