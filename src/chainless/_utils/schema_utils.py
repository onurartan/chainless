import inspect
from pydantic import create_model, BaseModel
from typing import get_type_hints, Callable, Type


def function_to_input_schema(func: Callable) -> Type[BaseModel]:
    """
    Create a Pydantic input schema model from a function signature.

    This utility inspects the given function's parameters and type annotations
    to dynamically construct a Pydantic `BaseModel` where each parameter is
    represented as a typed field. Parameters without explicit type hints default
    to `str`. Parameters without default values are marked as required.

    Args:
        func (Callable): The function whose input signature will be converted
            into a Pydantic model.

    Returns:
        Type[BaseModel]: A dynamically generated Pydantic model representing the
        function's input schema.

    Notes:
        - The `self` parameter is ignored to support instance methods.
        - Missing type annotations fallback to `str`.
        - Required fields use `...` as the Pydantic default.

    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    fields = {}

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        annotation = type_hints.get(name, str)  # fallback: str
        default = param.default if param.default is not inspect.Parameter.empty else ...
        fields[name] = (annotation, default)

    return create_model(f"{func.__name__.title()}Input", **fields)
