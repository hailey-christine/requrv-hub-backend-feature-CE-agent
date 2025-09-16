from typing import List
from pydantic import BaseModel, Field

class InsertSeatIntoSubscriptionInputDto(BaseModel):
    """
    Data Transfer Object for creating a subscription.
    """
    user_ids: List[str] = Field(
        ...,
        description="List of user IDs to associate with the seats."
    )
    subscription_id: str = Field(
        ...,
        description="The ID of the subscription to which the seats will be added."
    )
    billable_metric_code: str = Field(
        description="The code for the billable metric associated with the seats."
    )

class TerminateSeatInputDto(BaseModel):
    subscription_id: str = Field(
        ...,
        description="The ID of the subscription from which the seats will be deleted."
    )
    billable_metric_code: str = Field(
        description="The code for the billable metric associated with the seats."
    )
    user_ids: List[str] = Field(
        ...,
        description="List of user IDs to associate with the seats."
    )
    

class UsersSeatAssociationInputDto(BaseModel):
    user_ids: List[str] = Field(
        ...,
        description="List of user IDs to associate with the seats."
    )
    subscription_id: str = Field(
        ...,
        description="The ID of the subscription to which the seats will be added."
    )
   
################### OUTPUT #######################



