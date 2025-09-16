from functools import wraps
from fastapi import Request, HTTPException
from lago_python_client.client import Client
from lago_python_client.exceptions import LagoApiError
from core.settings import auth
from core.services.lago.lago import user_has_active_subscription

from core.settings import settings

setting = settings.model_dump()

# Definisci il decorator
def lago_guard(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = (await auth.access_token_required(request)).sub
            
        try:
            if user_has_active_subscription(user_id):
                # Se l'utente ha un abbonamento attivo, continua
                pass
            else:
                # Se l'utente non ha un abbonamento attivo, solleva un'eccezione
                raise HTTPException(
                    status_code=403,
                    detail="You do not have an active subscription."
                )
        except LagoApiError as e:
            raise HTTPException(status_code=400, detail=e.response)

        return await func(request, *args, **kwargs)
    return wrapper
