from os import environ


def get_env(variable, *, default=None, convert=None):
    """
    :type variable: str
    :type default: None | str | bytes | int | float | list
    :type convert: None | (None | str | bytes | int | float | list) -> (None | str | bytes | int | float | list)
    :rtype: None | str | bytes | int | float | list
    """
    value = environ.get("GOLD_DIGGER_" + variable.upper(), default)

    if value is not None and convert:
        return convert(value)
    else:
        return value
