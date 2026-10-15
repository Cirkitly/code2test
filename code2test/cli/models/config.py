"""
Persistent user settings for the Code2Test CLI.

Stored in ~/.codewiki/config.json (the location is kept from CodeWiki, which
Code2Test grew out of, so existing configurations keep working). The API key
itself is kept in the system keychain, not in this file.
"""

from dataclasses import dataclass

from code2test.cli.utils.validation import validate_model_name


@dataclass
class Configuration:
    """
    Code2Test configuration.

    Attributes:
        main_model: pydantic-ai model string used for test generation,
            e.g. "anthropic:claude-sonnet-5-5"; empty when not set
    """

    main_model: str = ""

    def validate(self):
        """Raise ConfigurationError if a set field is invalid."""
        if self.main_model:
            validate_model_name(self.main_model)

    def to_dict(self) -> dict:
        return {"main_model": self.main_model}

    @classmethod
    def from_dict(cls, data: dict) -> "Configuration":
        # Files written by older versions hold more settings; only main_model is used
        return cls(main_model=data.get("main_model", "") or "")

    def is_complete(self) -> bool:
        """True when a model is set."""
        return bool(self.main_model)
