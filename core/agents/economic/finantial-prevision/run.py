from langfuse import Langfuse
from core.agents.core.config import AgentConfig, OutputConfig
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from settings import settings
from agents.core.tools import custom_tools
from agents.generic_tools.tools import global_tools

lang_client = Langfuse(
    host=settings.model_dump()["requrv_langfuse_host"],
    public_key=settings.model_dump()["requrv_langfuse_public_key"],
    secret_key=settings.model_dump()["requrv_langfuse_secret_key"],
)


def agent_startup(team_key: str) -> Agent:
    """Core agent startup function

    Args:
        user_id (str): The user ID that called the agent

    Raises:
        ValueError: User not found
        ValueError: Team key not found

    Returns:
        Agent: The core agent instance
    """
    config = AgentConfig(
        system_prompt=lang_client.get_prompt("requrv-hub-core").compile(),
        output_config=OutputConfig(format="plain", json_schema=None),
        qdrant_resources=[],
    )

    llm_model = OpenAIModel(
        model_name="requrv-ai",
        provider=OpenAIProvider(
            api_key=team_key,
            base_url=settings.model_dump()["requrv_openai_base_url"],
        ),
    )

    whole_tools = global_tools + custom_tools

    core_agent = Agent(
        system_prompt=config.system_prompt,
        model=llm_model,
        model_settings={
            "temperature": 0.7,
            "top_p": 0.8,
            "frequency_penalty": 1,
            "extra_body": (
                {"guided_json": config.output_config.json_schema}
                if config.output_config.json_schema
                else {}
            ),
        },  # Recommended settings https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507-FP8#best-practices
        tools=whole_tools,
        toolsets=(
            config.mcp_config.servers if config.mcp_config else []
        ),  # add toolsets if needed - MCP
    )

    return core_agent
