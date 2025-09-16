import dotenv
import os

dotenv.load_dotenv()


def check_environment_variables(env_vars):
    """
    Check if the specified environment variables are configured.

    :param env_vars: List of environment variable names to check.
    :raises ValueError: If any environment variable is not configured.
    """
    missing_vars = [var for var in env_vars if os.getenv(var) is None]
    if missing_vars:
        raise ValueError(
            f"The following environment variables are not configured: {', '.join(missing_vars)}"
        )
