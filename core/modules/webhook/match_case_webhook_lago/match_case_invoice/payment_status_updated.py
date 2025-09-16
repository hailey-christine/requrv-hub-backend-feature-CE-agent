from core.services.prisma import prisma
from prisma.enums import PaymentStatus, SeatStatus
from datetime import datetime, timedelta
from core.services.litellm import create_key


async def payment_status_updated(data, webhook_id):
    """
    Process the payment status update for an invoice.
    
    Args:
        data (dict): The data received from the webhook.
    
    Returns:
        None
    """
    # if data['webhook_type'] != 'invoice.payment_status_updated' and data['webhook_type'] != 'invoice.created':
    #     print(f"Unsupported webhook type: {data['webhook_type']}")
    #     # raise ValueError(f"Unsupported webhook type: {data['webhook_type']}")
    #     return
    
    invoice = data['invoice']
    payment_status = invoice['payment_status']
    subscription_id = invoice['fees'][0]['external_subscription_id']

    if not subscription_id:
        print("No subscription ID found in the invoice fees.")
        return

    if payment_status == 'succeeded':
        # Update the subscription status in the database
        try: 
            async with prisma.tx() as transaction:
                # Aggiorna l'utente come confermato e rimuovi il token di conferma

                await transaction.webhook.update(
                    where={"id": webhook_id},
                    data={"hasBeenProcessed": True}
                )

                subscription_db = await transaction.subscription.update(
                    where={"id": subscription_id},
                    data={
                        "status": PaymentStatus.ACTIVE, 
                        "startDate": datetime.now()
                        },
                    include={
                        "organization": True,
                        "seats": True
                    }
                )
                if not subscription_db:
                    raise ValueError("Subscription not found")
                if not subscription_db.organization:
                    raise ValueError("Organization not found for the subscription")
                
                team_key = subscription_db.organization.team_key

                if not team_key:
                    raise ValueError("Team key not found for the organization")

                for seat in subscription_db.seats:
                    await transaction.seat.update(
                        where={"id": seat.id},
                        data={
                            "status": SeatStatus.ACTIVE,
                            "key_litellm": create_key(team_key).key
                        }
                    )

        except Exception as e:
            # Se si verifica un errore, tutte le operazioni nella transazione verranno annullate
            raise e
    elif payment_status == 'failed':
        # Update the subscription status in the database
        try:
            async with prisma.tx() as transaction:
                # Aggiorna l'utente come non confermato e rimuovi il token di conferma
                await transaction.webhook.update(
                    where={"id": webhook_id},
                    data={"hasBeenProcessed": True}
                )

                await transaction.subscription.update(
                    where={"id": subscription_id},
                    data={
                        "status": PaymentStatus.FAILED,
                        "startDate": datetime.now(),
                        "endDate": datetime.now() + timedelta(days=30)
                    },
                )

        except Exception as e:
            # Se si verifica un errore, tutte le operazioni nella transazione verranno annullate
            raise e