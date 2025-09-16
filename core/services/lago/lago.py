from fastapi import HTTPException
from lago_python_client import Client
from lago_python_client.exceptions import LagoApiError
from lago_python_client.models import Customer, Subscription, Event

from core.settings import settings

setting = settings.model_dump()

lago_client = Client(
    api_key=setting["requrv_lago_api_key"], api_url=setting["requrv_lago_endpoint"]
)


def create_customer(customer: Customer):
    try:
        costumer = lago_client.customers.create(customer)
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)

    return costumer


def get_customer(customer_id: str):
    try:
        custumer = lago_client.customers.find(customer_id)
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)

    return custumer


def get_customer_portal(customer_id: str):
    try:
        return lago_client.customers.portal_url(customer_id)
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)
    

def get_checkout_url(customer_id: str):
    try:
        return lago_client.customers.checkout_url(customer_id)
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)


def delete_customer(customer_id: str):
    try:
        return lago_client.customers.destroy(customer_id)
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)


def user_has_active_subscription(customer_id: str):
    try:
        subscriptions = lago_client.subscriptions.find_all({'external_customer_id': customer_id, 'status': 'active'})["subscriptions"]
        if not subscriptions or len(subscriptions) == 0:
            return False
        return True
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)
    

def regenerate_checkout_url(customer_id: str):
    try:
        return lago_client.customers.checkout_url(customer_id)
    except LagoApiError as e:
        print(e)
        raise HTTPException(status_code=400, detail=e.response)
    

def create_a_subscription(subscription: Subscription):
    try:
        subscription = lago_client.subscriptions.create(subscription)
        return subscription
    except LagoApiError as e:
        raise HTTPException(status_code=400, detail=e.response)
    

def send_usage_event(event: Event):
    try:
        event_response = lago_client.events.create(event)
        return event_response
    except LagoApiError as e:
        raise HTTPException(status_code=400, detail=e.response)
    
def get_subscriptions_by_customer(customer_id: str):
    try:
        subscriptions = lago_client.subscriptions.find_all({'external_customer_id': customer_id})["subscriptions"]
        if not subscriptions or len(subscriptions) == 0:
            return []
        return subscriptions
    except LagoApiError as e:
        print(e)
        raise ValueError(e.response)
    
def update_subscription(subscription_id: str, subscription: Subscription):
    try:
        print("Updating subscription in lago with data:")
        # print(subscription)
        print("Subscription ID: ", subscription_id)
        updated_subscription = lago_client.subscriptions.update(subscription, subscription_id)
        print("Subscription updated successfully in lago")
        return updated_subscription
    except LagoApiError as e:
        print(e)
        raise ValueError(e.response)