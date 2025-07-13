from emoji import emojize


def with_emoji(text: str) -> str:
    """
    Convert text to emoji representation.
    """
    return emojize(text, language='alias')
