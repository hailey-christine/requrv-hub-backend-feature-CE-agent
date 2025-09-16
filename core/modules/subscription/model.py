from pydantic import BaseModel, Field

class CreateSubscriptionInputDto(BaseModel):
    """
    Data Transfer Object for creating a subscription.
    """
    plan_code: str = Field(
        ...,
        description="The plan code for the subscription."
    )
    billable_metric_code: str = Field(
        description="The code for the billable metric associated with the seats."
    )

   
################### OUTPUT #######################



