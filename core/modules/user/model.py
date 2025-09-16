from pydantic import BaseModel, Field



################### OUTPUT #######################


class CheckoutOutputDto(BaseModel):
    url: str = Field(
        ...,
        description="The URL for the checkout session.",
        example="https://checkout.example.com/session/1234567890"
    )
