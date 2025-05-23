import inspect


async def _call_callback(callback, *args, **kwargs):
    if inspect.iscoroutinefunction(callback):
        await callback(*args, **kwargs)
    else:
        callback(*args, **kwargs)

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
    kw_params = [
        p
        for p in params
        if p.kind
        in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]

    max_pos_args = len(pos_params)

    filtered_args = args[:max_pos_args]

    param_names = [p.name for p in params]
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in param_names}

    if inspect.iscoroutinefunction(callback):
        return await callback(*filtered_args, **filtered_kwargs)
    else:
        return callback(*filtered_args, **filtered_kwargs)


def _validate_callback(callback, expected_args: list, name: str):

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
