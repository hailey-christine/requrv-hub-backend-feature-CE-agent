

from datetime import datetime
from re import I
from typing import Annotated
import uuid
from authx import TokenPayload
from fastapi import APIRouter, Body, Depends, HTTPException
from core.settings import auth
from core.services.lago.lago import get_subscriptions_by_customer, send_usage_event
from core.modules.seat.model import InsertSeatIntoSubscriptionInputDto, TerminateSeatInputDto, UsersSeatAssociationInputDto
from lago_python_client.models import Event
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.services.litellm import create_key

from core.services.prisma import prisma
from prisma.models import User
from prisma.enums import SeatStatus, PaymentStatus


seat_router = APIRouter(prefix="/seat", tags=["seat"])
auth_scheme = HTTPBearer()

@seat_router.post("/active")
async def active_seat_into_subscription(
    data: Annotated[ InsertSeatIntoSubscriptionInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)) :
    
    user_id = payload.sub
    subscription_id = data.subscription_id
    
    if not data.user_ids and len(data.user_ids) <= 0:
        raise HTTPException(status_code=400, detail="You must provide at least one user ID")

    user: User = await prisma.user.find_unique(where={"id": user_id},include={
        "owner": True,
    })

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=400, detail="The user is not an owner of any organisation")
    
    # Controllo se la subscription esiste
    subscription_db = await prisma.subscription.find_unique(
        where={"id": subscription_id},
        include={
            "organization": True,
            "seats": True
        }
    )

    if not subscription_db:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if not subscription_db.organization:
        raise HTTPException(status_code=404, detail="Organization not found for the subscription")

    if subscription_db.organization.id != user.owner.id:
        raise HTTPException(status_code=400, detail="You are not allowed to add seats to this subscription")

    team_key = subscription_db.organization.team_key

    if not team_key:
        raise ValueError("Team key not found for the organization")
    
    data.user_ids = list(set(data.user_ids))

    # Qui creo la subscription per l'utente in una transaction prima nel nostro db e poi in lago
    try: 
        async with prisma.tx() as transaction:
            for user_id in data.user_ids:
                user = await transaction.user.find_unique(where={"id": user_id})
                if not user:
                    raise HTTPException(status_code=404, detail=f"User {user_id} not found")
                
                if user.organizationId != subscription_db.organization.id:
                    raise HTTPException(status_code=400, detail=f"User {user_id} does not belong to the organization of the subscription")


                # qui controllo se non ha già un seat per quella subscription
                existing_seat = await transaction.seat.find_first(
                    where={
                        "userId": user_id,
                        "subscriptionId": subscription_id
                    }
                )

                if existing_seat and existing_seat.status == SeatStatus.ACTIVE:
                    raise HTTPException(status_code=400, detail=f"User {user_id} already has an active seat for this subscription")
                if existing_seat and existing_seat.status == SeatStatus.SCHEDULED_FOR_TERMINATION:
                    #riattivo il seat
                    await transaction.seat.update(
                        where={"id": existing_seat.id},
                        data={
                            "status": SeatStatus.ACTIVE,
                            "endDate": None
                        }
                    )
                    continue

                await transaction.seat.create(
                    data={
                        "status": SeatStatus.ACTIVE,
                        "key_litellm": create_key(team_key).key,
                        "billable_metric_code": data.billable_metric_code,
                        "subscription": {
                            "connect": {
                                "id": subscription_id
                            }
                        },
                        "user": {
                            "connect": {
                                "id": user_id
                            }
                        } ,

                    }
                )
                
            event_to_send = Event(
                transaction_id=str(uuid.uuid4()),
                external_subscription_id=subscription_id,
                code=data.billable_metric_code,
                timestamp= datetime.now().timestamp(),
                properties={
                    "user_id": user_id, 
                    "operation_type": "add"
                    }
            )

            send_usage_event(event_to_send)
            

    except Exception as e:
       # Se si verifica un errore, tutte le operazioni nella transazione verranno annullate
       #TODO va aggiustato il messaggio di errore
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the seat of subscription: {str(e)}")
   
    subscription_db = await prisma.subscription.find_unique(
        where={"id": subscription_id},
        include={
            "organization": True,   
            "seats": True
        }
    )
    return subscription_db


@seat_router.post("/terminate")
async def terminate_seat(
    data: Annotated[ TerminateSeatInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):

    user_id = payload.sub

    user: User = await prisma.user.find_unique(where={"id": user_id},include={
        "owner": {
            "include": {
                "subscriptions": {
                    "include": {
                        "seats": True
                    }
                }
            }
        },
    })

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=404, detail="The user is not an owner of any organisation")
    # qui ci sarebbero tutti i controlli

    # prendo la subscription che voglio modificare tramite id da quelle nel organization 
    subscription_db = next((sub for sub in user.owner.subscriptions if sub.id == data.subscription_id), None)
    
    if not subscription_db:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription_db.status != PaymentStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Subscription is not active")
    
    seats_to_terminate = [ seat for seat in subscription_db.seats if seat.userId in data.user_ids and seat.status == SeatStatus.ACTIVE]

    subscriptions_lago = get_subscriptions_by_customer(user.id)

    if not subscriptions_lago or len(subscriptions_lago) == 0:
        raise HTTPException(status_code=404, detail="No subscriptions found in Lago for the customer")
    
    subscription_lago = None

    for sub in subscriptions_lago:
        if sub.external_id == subscription_db.id:
            subscription_lago = sub
            break

    if not subscription_lago:
        raise HTTPException(status_code=404, detail="Subscription not found in Lago")

    await prisma.seat.update_many(
        where={
            "id": {"in": [seat.id for seat in seats_to_terminate]}
        },
        data={
            "status": SeatStatus.SCHEDULED_FOR_TERMINATION,
            "endDate": subscription_lago.current_billing_period_ending_at
        }
    )

    return True


async def schedule_seat_termination():
    """
    This function checks for seats that are scheduled for termination and whose end date has passed.
    It then terminates these seats by updating their status to 'TERMINATED'.
    """
    print("Running scheduled seat termination check...")
    seats_to_terminate = await prisma.seat.find_many(
        where={
            "status": SeatStatus.SCHEDULED_FOR_TERMINATION,
            "endDate": {
                "lte": datetime.now()
            }
        },
        include={
            "subscription": True
        }
    )

    if not seats_to_terminate or len(seats_to_terminate) == 0:
        print("No seats to terminate at this time.")
        return

    await prisma.seat.update_many(
        where={
            "id": {"in": [seat.id for seat in seats_to_terminate]}
        },
        data={
            "status": SeatStatus.TERMINATED
        }
    )

    for seat in seats_to_terminate:
        if seat.subscription.status == PaymentStatus.ACTIVE: 
            event_to_send = Event(
                transaction_id=str(uuid.uuid4()),
                external_subscription_id= seat.subscriptionId,
                code=seat.billable_metric_code,
                timestamp= datetime.now().timestamp(),
                properties={
                    "user_id": seat.userId, 
                    "operation_type": "remove"
                    }
            )

            send_usage_event(event_to_send)


    print(f"Terminated {len(seats_to_terminate)} seats.") 
    
    