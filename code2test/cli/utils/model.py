"""
Model selection shared by CLI commands.
"""

import os

from code2test.cli.config_manager import ConfigManager


def resolve_model(display) -> str:
    """
    Pick the pydantic-ai model string to use and export API keys for the agents.

    Order: CODE2TEST_MODEL env var, configured main model, Azure env config,
    Google API key, then OpenAI gpt-4o-mini.
    """
    # Load configuration
    config_manager = ConfigManager()
    config_manager.load()

    # Set API key in environment for agents
    api_key = config_manager.get_api_key()
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        # Support for Gemini/Google models which might look for these keys
        os.environ["GEMINI_API_KEY"] = api_key
        os.environ["GOOGLE_API_KEY"] = api_key

    # Get configured model
    cli_config = config_manager.get_config()
    main_model = cli_config.main_model if cli_config and cli_config.main_model else None

    # Explicit override, e.g. CODE2TEST_MODEL=anthropic:claude-sonnet-5-5 or "test" for an offline dry run
    if os.environ.get("CODE2TEST_MODEL"):
        main_model = os.environ["CODE2TEST_MODEL"]

    # If no model configured, infer from env/keys
    if not main_model:
        llm_backend = os.environ.get("LLM_BACKEND", "").lower()
        azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

        # Check for Azure configuration first (explicit override)
        if llm_backend == "azure" or (azure_deployment and os.environ.get("AZURE_OPENAI_ENDPOINT")):
            if azure_deployment:
                main_model = f"azure:{azure_deployment}"
                # Ensure API version is available for clients that need it
                if os.environ.get("AZURE_OPENAI_API_VERSION"):
                    os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]
                else:
                    # Default to a version that supports tool_choice='required'
                    # See: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#chat-completions
                    default_version = "2024-06-01"
                    if not os.environ.get("OPENAI_API_VERSION"):
                        os.environ["OPENAI_API_VERSION"] = default_version
                        display.info(f"Using default Azure API version: {default_version}")
                display.info(f"Detected Azure configuration, using deployment: {azure_deployment}")
            else:
                display.warning("Azure backend detected but AZURE_OPENAI_DEPLOYMENT is missing.")
                main_model = "openai:gpt-4o-mini"

        # Then check for Google API Key
        elif api_key and api_key.startswith("AIza"):
            # Google API key detected
            main_model = "google-gla:gemini-2.0-flash-exp"
            display.info("Detected Google API key, using Gemini 2.0 Flash")

        else:
            main_model = "openai:gpt-4o-mini"
            display.info("No model configured; using openai:gpt-4o-mini. "
                         "Set CODE2TEST_MODEL or run 'code2test config set --main-model' to choose another.")

    return main_model
