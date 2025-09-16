from typing import Annotated
from authx import TokenPayload
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core.settings import settings, auth
from core.services.prisma import prisma
import boto3


media_router = APIRouter(prefix="/media", tags=["media"])
media_scheme = HTTPBearer()

session = boto3.Session()
s3_client = session.client(
    service_name="s3",
    aws_access_key_id=settings.model_dump()["requrv_aws_access_key_id"],
    aws_secret_access_key=settings.model_dump()["requrv_aws_secret_access_key"],
    endpoint_url=settings.model_dump()["requrv_aws_endpoint"],
    region_name=settings.model_dump()["requrv_aws_region"],
)


@media_router.post("/upload")
async def upload_file(
    file: UploadFile | None,
    token: HTTPAuthorizationCredentials = Depends(media_scheme),
    payload: TokenPayload = Depends(auth.access_token_required),
):
    if not file:
        raise HTTPException(status_code=422, detail="No file to process")

    try:
        file_object = await file.read()

        file_key = (
            "requrv-hub/" + payload.sub + "/" + file.filename
            if file.filename
            else "file"
        )

        s3_client.put_object(
            Body=file_object,
            Bucket=settings.model_dump()["requrv_aws_bucket"],
            Key=file_key,
            ContentType=file.content_type,
        )

        object_file = await prisma.media.create(
            {
                "name": file.filename if file.filename else "file",
                "key": file_key,
                "size": file.size,
            }
        )
    except HTTPException as e:
        raise e
    
    return object_file


@media_router.post("/delete")
async def delete_file(
    file_id: Annotated[str, Body(embed=True, strict=True)],
    token: HTTPAuthorizationCredentials = Depends(media_scheme),
    payload: TokenPayload = Depends(auth.access_token_required),
):
    try:
        actual_file = await prisma.media.find_unique_or_raise(where={"id": file_id})

        s3_client.delete_object(
            Bucket=settings.model_dump()["requrv_aws_bucket"],
            Key=actual_file.key,
        )

        await prisma.media.delete(where={"id": file_id})

    except HTTPException as e:
        raise e

    return "ok"
