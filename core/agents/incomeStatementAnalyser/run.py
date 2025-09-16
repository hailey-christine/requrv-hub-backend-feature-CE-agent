from langfuse import Langfuse
from core.agents.core.config import AgentConfig, OutputConfig, SystemPrompt
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from settings import settings
from core.services.prisma import prisma
from agents.core.tools import custom_tools

lang_client = Langfuse(
    host=settings.model_dump()["requrv_langfuse_host"],
    public_key=settings.model_dump()["requrv_langfuse_public_key"],
    secret_key=settings.model_dump()["requrv_langfuse_secret_key"],
)


async def agent_startup(user_id: str) -> Agent:
    """Core agent startup function

    Args:
        user_id (str): The user ID that called the agent

    Raises:
        ValueError: User not found
        ValueError: Team key not found

    Returns:
        Agent: The core agent instance
    """

    actual_user = await prisma.user.find_unique(
        where={"id": user_id}, include={"organization": True}
    )
    if not actual_user:
        raise ValueError("User not found")

    team_key = actual_user.organization.team_key if actual_user.organization else None

    if not team_key:
        raise ValueError("Team key not found")

    config = AgentConfig(
        system_prompt=SystemPrompt(
            prompt=lang_client.get_prompt("requrv-hub-core").compile()
        ),
        output_config=OutputConfig(format="text", json_schema=None),
        qdrant_resources=[],
    )

    llm_model = OpenAIModel(
        model_name="requrv-ai",
        provider=OpenAIProvider(
            api_key=team_key,
            base_url=settings.requrv_hive_endpoint,
        ),
    )

    core_agent = Agent(
        system_prompt=config.system_prompt.prompt,
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
        tools=custom_tools,
        toolsets=(
            config.mcp_config.servers if config.mcp_config else []
        ),  # add toolsets if needed - MCP
    )

    return core_agent
