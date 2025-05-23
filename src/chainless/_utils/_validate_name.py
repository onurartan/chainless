import re


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
