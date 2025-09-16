from pydantic import BaseModel, Field

class CreateVectorDbInputDto(BaseModel):
    """
    Data Transfer Object for creating a VectorDb.
    """
    url: str = Field(
        description="The host URL for VectorDb.",
        example="https://example.vector-db.com"
    )
    user: str = Field(
        min_length=3
    )
    key: str = Field(
        min_length=3
    )
    region: str | None = Field(
        None,
        min_length=3
    )

class UpdateVectorDbInputDto(BaseModel):
    """
    Data Transfer Object for creating a VectorDb.
    """
    url: str | None = Field(
        None,
        description="The host URL for VectorDb.",
        example="https://example.vector-db.com"
    )
    user: str | None = Field(
        None,
        min_length=3
    )
    key: str | None = Field(
        None,
        min_length=3
    )
    region: str | None = Field(
        None,
        min_length=3
    )
   
################### OUTPUT #######################



