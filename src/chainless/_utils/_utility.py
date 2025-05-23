import inspect
from pydantic import create_model, BaseModel
from typing import get_type_hints, Callable, Type


def function_to_input_schema(func: Callable) -> Type[BaseModel]:
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
