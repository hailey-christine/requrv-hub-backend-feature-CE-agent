from authx import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core.settings import auth
from .model import CreateVectorDbInputDto, UpdateVectorDbInputDto

from core.services.prisma import prisma

from typing import Annotated


vector_db_router = APIRouter(prefix="/vector-db", tags=["vector db"])
auth_scheme = HTTPBearer()

@vector_db_router.post("")
async def create_vector_db(
    data: Annotated[ CreateVectorDbInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = payload.sub

    user = await prisma.user.find_unique(
        where={"id": user_id}, 
        include={
            "owner": {
                "include": {
                    "vectorDb": True
                }
            }
            }
        )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=403, detail="User does not have permission to create vectorDb configuration")
    if user.owner.vectorDb:
        raise HTTPException(status_code=403, detail="The organization has already configured vectorDb")

    await prisma.vectordb.create(
        data={
            "url": data.url,
            "user": data.user,
            "key": data.key,
            "region": data.region,
            "organization": {
                "connect": {
                    "id": user.owner.id
                }
            }
        }
    )

    return True

@vector_db_router.patch("")
async def update_vector_db(
    data: Annotated[UpdateVectorDbInputDto, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
        user_id = payload.sub

        user = await prisma.user.find_unique(
            where={"id": user_id}, 
            include={
                "owner": {
                    "include": {
                        "vectorDb": True
                    }
                }
                }
            )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.owner:
            raise HTTPException(status_code=403, detail="User does not have permission to create vectorDb configuration")
        if not user.owner.vectorDb:
            raise HTTPException(status_code=404, detail="VectorDb configuration not found")

        update_data = {}
        if data.url is not None:
            update_data["url"] = data.url
        if data.user is not None:
            update_data["user"] = data.user
        if data.key is not None:
            update_data["key"] = data.key
        if data.region is not None:
            update_data["region"] = data.region

        if update_data:
            await prisma.vectordb.update(
                where={"id": user.owner.vectorDb.id},
                data=update_data
            )

        return True

@vector_db_router.delete("")
async def delete_vector_db_configuration(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
        user_id = payload.sub

        user = await prisma.user.find_unique(
            where={"id": user_id}, 
            include={
                "owner": {
                    "include": {
                        "vectorDb": True
                    }
                }
                }
            )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.owner:
            raise HTTPException(status_code=403, detail="User does not have permission to create vectorDb configuration")

        await prisma.vectordb.delete(
            where={"id": user.owner.vectorDb.id}
        )

        return True

@vector_db_router.get("")
async def get_vector_db_configuration(
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = payload.sub

    user = await prisma.user.find_unique(
        where={"id": user_id}, 
        include={
            "owner": {
                "include": {
                    "vectorDb": True
                }
            }
            }
        )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.owner:
        raise HTTPException(status_code=403, detail="User does not have permission to create vectorDb configuration")
    
    vectorDb = user.owner.vectorDb
    if not vectorDb:
        raise HTTPException(status_code=404, detail="Vector Db configuration not found")


    return {
        "id": vectorDb.id,
        "url": vectorDb.url,
        "user": _mask(vectorDb.user),
        "key": _mask(vectorDb.key),
        "region": vectorDb.region,
        "organizationId": id,
        "createdAt": vectorDb.createdAt,
        "updatedAt": vectorDb.updatedAt,
    }


def _mask(value):
    if not value or len(value) <= 4:
        return '*' * 10 + value[-4:] if value else None
    return '*' * 10 + value[-4:]
