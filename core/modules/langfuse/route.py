
from urllib import response
from authx import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core.settings import auth
from core.modules.langfuse.model import CreateLangfuseInputDto, UpdateLangfuseInputDto

from core.services.prisma import prisma

from typing import Annotated


langfuse_router = APIRouter(prefix="/langfuse", tags=["langfuse"])
auth_scheme = HTTPBearer()

@langfuse_router.post("")
async def create_langfuse(
    data: Annotated[ CreateLangfuseInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = payload.sub

    user = await prisma.user.find_unique(
        where={"id": user_id}, 
        include={
            "owner": {
                "include": {
                    "langfuse": True
                }
            }
            }
        )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=403, detail="User does not have permission to create Langfuse configuration")
    if user.owner.langfuse:
        raise HTTPException(status_code=403, detail="The organization has already configured Langfuse")

    await prisma.langfuse.create(
        data={
            "host": data.host,
            "key": data.key,
            "secret": data.secret,
            "organization": {
                "connect": {
                    "id": user.owner.id
                }
            }
        }
    )

    return True

@langfuse_router.patch("")
async def update_langfuse(
    data: Annotated[UpdateLangfuseInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
        user_id = payload.sub

        user = await prisma.user.find_unique(
            where={"id": user_id}, 
            include={
                "owner": {
                    "include": {
                        "langfuse": True
                    }
                }
                }
            )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.owner:
            raise HTTPException(status_code=403, detail="User does not have permission to create Langfuse configuration")
        if not user.owner.langfuse:
            raise HTTPException(status_code=404, detail="LangFuse configuration not found")

        update_data = {}
        if data.host is not None:
            update_data["host"] = data.host
        if data.key is not None:
            update_data["key"] = data.key
        if data.secret is not None:
            update_data["secret"] = data.secret

        if update_data:
            await prisma.langfuse.update(
                where={"id": user.owner.langfuse.id},
                data=update_data
            )

        return True

@langfuse_router.delete("")
async def delete_langfuse_configuration(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
        user_id = payload.sub

        user = await prisma.user.find_unique(
            where={"id": user_id}, 
            include={
                "owner": {
                    "include": {
                        "langfuse": True
                    }
                }
                }
            )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.owner:
            raise HTTPException(status_code=403, detail="User does not have permission to create Langfuse configuration")

        await prisma.langfuse.delete(
            where={"id": user.owner.langfuse.id}
        )

        return True

@langfuse_router.get("")
async def get_langfuse_configuration(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
    
    user_id = payload.sub

    user = await prisma.user.find_unique(
        where={"id": user_id}, 
        include={
            "owner": {
                "include": {
                    "langfuse": True
                }
            }
            }
        )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=403, detail="User does not have permission to create Langfuse configuration")
    
    langfuse = user.owner.langfuse
    if not langfuse:
        raise HTTPException(status_code=404, detail="LangFuse configuration not found")


    return {
        "id": langfuse.id,
        "host": langfuse.host,
        "key": _mask(langfuse.key),
        "secret": _mask(langfuse.secret),
        "organizationId": user.owner.id,
        "createdAt": langfuse.createdAt,
        "updatedAt": langfuse.updatedAt,
    }


def _mask(value):
    if not value or len(value) <= 4:
        return '*' * 10 + value[-4:] if value else None
    return '*' * 10 + value[-4:]
