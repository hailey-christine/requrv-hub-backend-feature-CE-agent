

from core.modules.webhook.route import process_webhook
from core.services.prisma import prisma

async def processing_webhook_lago():
    await prisma.webhook.delete_many(where={"hasBeenProcessed": True})

    # qui prendo il totale dei webhook non processati
    total_webhooks = await prisma.webhook.count(where={"hasBeenProcessed": False})
    
    # qui dovrei fare un ciclo per processare 500 webhook alla volta
    if total_webhooks > 0:
        batch_size = 500
        
        for offset in range(0, total_webhooks, batch_size):
            webhooks = await prisma.webhook.find_many(
                where={"hasBeenProcessed": False},
                skip=offset,
                take=batch_size
            )

            for webhook in webhooks:
                data = webhook.data
                try:
                    await process_webhook(data, webhook.id)
                except Exception as e:
                    print(f"Error processing webhook {webhook.id}: {e}")
                    # Log the error or handle it as needed


