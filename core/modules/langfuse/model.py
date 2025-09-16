from pydantic import BaseModel, Field

class CreateLangfuseInputDto(BaseModel):
    """
    Data Transfer Object for creating a Langfuse.
    """
    host: str = Field(
        ...,
        description="The host URL for Langfuse.",
        example="https://example.langfuse.com"
    )
    key: str = Field(
        min_length=3
    )
    secret: str = Field(
        min_length=3
    )

class UpdateLangfuseInputDto(BaseModel):
    """
    Data Transfer Object for creating a Langfuse.
    """
    host: str | None = Field(
        None,
        description="The host URL for Langfuse.",
        example="https://example.langfuse.com"
    )
    key: str | None = Field(
        None,
        min_length=3
    )
    secret: str | None = Field(
        None,
        min_length=3
    )
   
################### OUTPUT #######################



