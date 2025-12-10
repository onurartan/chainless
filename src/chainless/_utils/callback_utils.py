import inspect


async def call_callback(callback, *args, **kwargs):
    if callback is None:
        return

    sig = inspect.signature(callback)
    params = list(sig.parameters.values())

    pos_params = [
        p
        for p in params
        if p.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    
    # REMOVED
    # kw_params = [
    #     p
    #     for p in params
    #     if p.kind
    #     in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    # ]

    max_pos_args = len(pos_params)

    filtered_args = args[:max_pos_args]

    param_names = [p.name for p in params]
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in param_names}

    if inspect.iscoroutinefunction(callback):
        return await callback(*filtered_args, **filtered_kwargs)
    else:
        return callback(*filtered_args, **filtered_kwargs)


def validate_callback(callback, expected_args: list, name: str):
    """
    Validates that a callback has the exact expected argument names.

    This function ensures that a user-provided callback defines parameters
    that match a required list of argument names in both order and count.
    If the callback does not match the expected signature, a TypeError is raised.

    Args:
        callback (Callable | None):
            The callback to validate. If None, validation is skipped silently.
        expected_args (list[str]):
            A list of expected parameter names, in order.
        name (str):
            A human-readable name for the callback, used in error messages.

    Raises:
        TypeError:
            - If the callback is not callable.
            - If the callback's parameter names do not exactly match the
              expected argument list.

    Example:
        >>> def on_event(user, data): pass
        >>> validate_callback(on_event, ["user", "data"], "on_event")  # OK

        >>> def invalid(a, b, c): pass
        >>> validate_callback(invalid, ["user", "data"], "on_event")
        TypeError: on_event must have arguments: user, data in order
    """

    if callback is None:
        return

    if not callable(callback):
        raise TypeError(f"{name} must be a callable function.")

    sig = inspect.signature(callback)
    params = list(sig.parameters.values())

    actual_arg_names = [param.name for param in params]
    if actual_arg_names != expected_args:
        raise TypeError(
            f"{name} must have arguments: {', '.join(expected_args)} in order"
        )
