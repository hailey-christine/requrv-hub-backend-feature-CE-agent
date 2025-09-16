from datetime import timedelta
from datetime import datetime
from typing import Annotated
import uuid
from authx import TokenPayload
from fastapi import APIRouter, Body, Depends, HTTPException
from tomlkit import date
from core.modules.subscription.model import CreateSubscriptionInputDto
from core.settings import auth
from core.services.lago.lago import create_a_subscription, get_subscriptions_by_customer, send_usage_event, update_subscription
from lago_python_client.models import Subscription, Event

from core.services.prisma import prisma
from prisma.models import User
from prisma.enums import PaymentStatus, SeatStatus
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer



subscription_router = APIRouter(prefix="/subscription", tags=["subscription"])
auth_scheme = HTTPBearer()


@subscription_router.post("/active")
async def active_subscription(
    data: Annotated[ CreateSubscriptionInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)) :
    
    user_id = payload.sub

    user: User = await prisma.user.find_unique(where={"id": user_id},include={
        "owner": {
            "include": {
                "subscriptions": True
            }
        },
    })
    

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=404, detail="The user is not an owner of any organisation")
    
    if user.owner.subscriptions and len(user.owner.subscriptions) > 0:
        subscription_db_selected = None
        for sub in user.owner.subscriptions:
            if sub.status == PaymentStatus.ACTIVE:
                raise HTTPException(status_code=403, detail="The organization already has an active subscription")
            if sub.status == PaymentStatus.PENDING:
                raise HTTPException(status_code=403, detail="The organization already has a pending subscription")
            if sub.status == PaymentStatus.SCHEDULED_FOR_TERMINATION:
                subscription_db_selected = sub
                break
        
        if subscription_db_selected:
            # qui faccio il processo di riattivazione della subscription
            try:
                async with prisma.tx() as transaction:
                    subscription_updated = await transaction.subscription.update(
                        where={"id": subscription_db_selected.id},
                        data={
                            "status": PaymentStatus.ACTIVE,
                            "startDate": datetime.now(),
                            "endDate": None
                        }
                    )  
                    
                    await transaction.seat.update_many(
                        where={"subscriptionId": subscription_db_selected.id},
                        data={
                            "status": SeatStatus.ACTIVE,
                            "endDate": None
                        }
                    )
                    
                    subscription_lago_data = Subscription(
                        external_customer_id=user.id,
                        plan_code=data.plan_code,
                        external_id=subscription_db_selected.id,
                        ending_at="",
                    )
                    
                    update_subscription(subscription_db_selected.id, subscription_lago_data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"An error occurred while reactivating the subscription in the database: {str(e)}")            
            return subscription_updated
    


    # Qui gestisco se l'utente non ha una subscription ed è la prima volta che ne crea una
    try: 
        async with prisma.tx() as transaction:
            subscription_db = await transaction.subscription.create(
                data={
                    "status": PaymentStatus.PENDING,
                    "startDate": datetime.now(),
                    "endDate": None,    # Inizialmente non ha una data di fine
                    "planCode": data.plan_code,
                    "organization": {
                        "connect": {
                            "id": user.owner.id
                        }
                    }
                })
            
            # Qui devo gestire se c'era già una subscription e deve prendere i seat e metterli nella nuova subscription
            

            await transaction.seat.create(
                    data={
                        "status": SeatStatus.PENDING,
                        "subscription": {
                            "connect": {
                                "id": subscription_db.id
                            }
                        },
                        "user": {
                            "connect" : {
                                "id": user.id
                            }
                        }
                    }
                )
            
            # Creo la subscription in lago
            try: 
                subscription_lago_data: Subscription = Subscription(
                    external_customer_id=user_id,
                    plan_code=data.plan_code,
                    external_id=subscription_db.id,
                    subscription_at=datetime.now().isoformat()
                )

                create_a_subscription(subscription_lago_data)

                event_to_send = Event(
                    transaction_id=str(uuid.uuid4()),
                    external_subscription_id=subscription_db.id,
                    code=data.billable_metric_code,
                    timestamp= datetime.now().timestamp(),
                    properties={
                        "user_id": user_id,
                        "operation_type": "add"
                        }
                )

                send_usage_event(event_to_send)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"An error occurred while creating the subscription in the database: {str(e)}")

    except Exception as e:
       # Se si verifica un errore, tutte le operazioni nella transazione verranno annullate
       #TODO va aggiustato il messaggio di errore
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the subscription: {str(e)}")
   

    return subscription_db




@subscription_router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)) :
    
    user_id = payload.sub

    user: User = await prisma.user.find_unique(where={"id": user_id},include={
        "owner": {
            "include": {
                "subscriptions": True
            }
        },
    })
    

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=404, detail="The user is not an owner of any organisation")
    
    if not user.owner.subscriptions or len(user.owner.subscriptions) == 0:
        raise HTTPException(status_code=403, detail="The organization does not have any subscription")

    if subscription_id not in [sub.id for sub in user.owner.subscriptions]:
        raise HTTPException(status_code=403, detail="The subscription does not belong to the user's organization")

    subscription_db = [user for user in user.owner.subscriptions if user.id == subscription_id][0]
    
    if not subscription_db:
        raise HTTPException(status_code=404, detail="Subscription not found in our database")
    
    if subscription_db.status != PaymentStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="The subscription is not active and cannot be deleted")

    subscriptions_lago = get_subscriptions_by_customer(user.id)

    if not subscriptions_lago or len(subscriptions_lago) == 0:
        raise HTTPException(status_code=404, detail="No subscriptions found in Lago for the customer")
    
    
    subscription_lago_to_update = None

    for sub in subscriptions_lago:
        if sub.external_id == subscription_db.id:
            subscription_lago_to_update = sub
            break

    if not subscription_lago_to_update:
        raise HTTPException(status_code=404, detail="Subscription not found in Lago")

    try:
        async with prisma.tx() as transaction:
            await transaction.subscription.update(
                where={"id": subscription_db.id},
                data={
                    "status": PaymentStatus.SCHEDULED_FOR_TERMINATION,
                    # ultimo giorno del mese corrente
                    "endDate": subscription_lago_to_update.current_billing_period_ending_at
                }
            )  
            
            await transaction.seat.update_many(
                where={"subscriptionId": subscription_db.id},
                data={
                    "status": SeatStatus.SCHEDULED_FOR_TERMINATION,
                    "endDate": subscription_lago_to_update.current_billing_period_ending_at
                }
            )
            
            subscription_update_data = Subscription(
                external_customer_id =  user.id,
                plan_code = subscription_lago_to_update.plan_code,
                external_id = subscription_db.id,
                ending_at = subscription_lago_to_update.current_billing_period_ending_at
            )
            
            update_subscription(subscription_lago_to_update.external_id, subscription_update_data)
          


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while updating the subscription in the database: {str(e)}")

    return True
    

async def schedule_subscription_termination():
    """
    This function checks for subscriptions that are scheduled for termination and whose end date has passed.
    It then terminates these subscriptions by updating their status to 'TERMINATED'.
    """
    print("Running scheduled subscription termination check...")
    subscriptions_to_terminate = await prisma.subscription.find_many(
        where={
            "status": PaymentStatus.SCHEDULED_FOR_TERMINATION,
            "endDate": {
                "lte": datetime.now()
            }
        },
        include={
            "seats": True
        }
    )

    if not subscriptions_to_terminate or len(subscriptions_to_terminate) == 0:
        print("No subscriptions to terminate at this time.")
        return

    await prisma.subscription.update_many(
        where={
            "id": {"in": [sub.id for sub in subscriptions_to_terminate]}
        },
        data={
            "status": PaymentStatus.TERMINATED
        }
    )

    await prisma.seat.update_many(
        where={
            "subscriptionId": {"in": [sub.id for sub in subscriptions_to_terminate]}
        },
        data={
            "status": SeatStatus.TERMINATED
        }
    )

    print(f"Terminated {len(subscriptions_to_terminate)} subscriptions and their associated seats.")