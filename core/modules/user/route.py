
from authx import TokenPayload
from fastapi import APIRouter, Depends, HTTPException
from core.settings import auth

from core.services.prisma import prisma
from prisma.models import User
from core.services.lago.lago import get_checkout_url
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.modules.user.model import CheckoutOutputDto

user_router = APIRouter(prefix="/user", tags=["user"])
auth_scheme = HTTPBearer()

@user_router.post("/checkout")
async def regenerate_checkout_url(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)) -> CheckoutOutputDto:
    user_id = payload.sub

    user: User = await prisma.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return CheckoutOutputDto(url=get_checkout_url(user_id))

@user_router.get("/my-team")
async def get_my_team(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = payload.sub

    user: User = await prisma.user.find_unique(
        where={"id": user_id},
        include={
            "owner": {
                "include": {
                    "users": True
                }
            }
        }
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.owner:
        raise HTTPException(status_code=404, detail="The user is not an owner of any organisation")
    # Restituisci solo alcuni campi degli utenti (ad esempio id, email, nome)
    users = [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "surname": u.surname
        }
        for u in user.owner.users
    ]
    return users