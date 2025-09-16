from .payment_status_updated import payment_status_updated
from core.services.prisma import prisma

async def main_match_invoice(data, webhook_id):
    match data['webhook_type']:
        case 'invoice.payment_status_updated':
            await payment_status_updated(data, webhook_id)
        case 'invoice.created':
            await payment_status_updated(data, webhook_id)
        case _:
            await prisma.webhook.update(
                    where={"id": webhook_id},
                    data={"hasBeenProcessed": True}
                )
            print(f"Unsupported webhook type: {data['webhook_type']}")  
            #raise ValueError(f"Unsupported object type: {data['webhook_type']}")