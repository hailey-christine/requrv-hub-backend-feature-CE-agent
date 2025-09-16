import json
from math import e
from typing import Annotated
from core.services.prisma import prisma
from fastapi import APIRouter, Body
from core.modules.webhook.match_case_webhook_lago.match_case_invoice.main_match_invoice import main_match_invoice


webhook_router = APIRouter(prefix="/webhook", tags=["webhooks"])


@webhook_router.post("/lago")
async def webhooks_lago(data: Annotated[dict, Body()]):
    new_webhook = await prisma.webhook.create(
        data={
            "data": json.dumps(data)
        })
    
    try:
        await process_webhook(data, new_webhook.id)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Optionally, you can log the error or handle it as needed
        await prisma.webhook.update(
            where={"id": new_webhook.id},
            data={"hasBeenProcessed": True}
        )
        return {"status": "error", "message": str(e)}
    return True
    


async def process_webhook(data: dict, webhook_id: str):
    try:
        match data['object_type']:
            case 'invoice':
                return await main_match_invoice(data, webhook_id)
            case _:
                await prisma.webhook.update(
                    where={"id": webhook_id},
                    data={"hasBeenProcessed": True}
                )
                print(f"Unsupported object type: {data['object_type']}")
                #raise ValueError(f"Unsupported object type: {data['object_type']}")
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Optionally, you can log the error or handle it as needed
        await prisma.webhook.update(
            where={"id": webhook_id},
            data={"hasBeenProcessed": True}
        )
      
    return True