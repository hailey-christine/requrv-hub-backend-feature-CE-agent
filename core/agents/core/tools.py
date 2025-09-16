from pydantic_ai import Tool


def current_time() -> str:
    """Get the current time in HH:MM:SS format.

    Returns:
        str: current time as a string
    """
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


custom_tools = [Tool(current_time)]
