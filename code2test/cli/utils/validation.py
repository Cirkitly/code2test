"""
Input validation for CLI configuration values.
"""

from code2test.cli.utils.errors import ConfigurationError


def validate_api_key(api_key: str, min_length: int = 10) -> str:
    """
    Validate API key format.

    Args:
        api_key: API key to validate
        min_length: Minimum key length

    Returns:
        Validated API key

    Raises:
        ConfigurationError: If API key is invalid
    """
    if not api_key or not api_key.strip():
        raise ConfigurationError("API key cannot be empty")

    api_key = api_key.strip()

    if len(api_key) < min_length:
        raise ConfigurationError(f"API key too short (minimum {min_length} characters)")

    return api_key


def validate_model_name(model: str) -> str:
    """
    Validate model name format.

    Args:
        model: Model name to validate

    Returns:
        Validated model name

    Raises:
        ConfigurationError: If model name is invalid
    """
    if not model or not model.strip():
        raise ConfigurationError("Model name cannot be empty")

    return model.strip()


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Mask API key for display, showing only first and last few characters.

    Args:
        api_key: API key to mask
        visible_chars: Number of visible characters at start and end

    Returns:
        Masked API key (e.g., "sk-1234...5678")
    """
    if not api_key:
        return "Not set"

    if len(api_key) <= visible_chars * 2:
        # Key too short, mask everything except edges
        return f"{api_key[:2]}...{api_key[-2:]}"

    return f"{api_key[:visible_chars]}...{api_key[-visible_chars:]}"
