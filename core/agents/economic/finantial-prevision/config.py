from pydantic import BaseModel, Field
from pydantic_ai.mcp import MCPServerStreamableHTTP
from typing import List, Dict, Optional

class QdrantResource(BaseModel):
    collection_name: str = Field(..., description="Name of the Qdrant collection")


class OutputConfig(BaseModel):
    format: str = Field(..., description="Output format: 'plain' or 'json'")
    json_schema: Optional[Dict] = Field(
        None, description="JSON schema for structured output"
    )


class McpConfig(BaseModel):
    servers: List[MCPServerStreamableHTTP] = Field(
        ..., description="List of MCP servers for retrieval"
    )


class AgentConfig(BaseModel):
    system_prompt: str
    qdrant_resources: List[QdrantResource]
    output_config: OutputConfig
    mcp_config: Optional[McpConfig] = None
