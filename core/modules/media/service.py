import logging
from fastapi import HTTPException, UploadFile
from core.settings import settings
from core.services.prisma import prisma
import boto3
from core.services.otp import otp

session = boto3.Session()
s3_client = session.client(
    service_name="s3",
    aws_access_key_id=settings.model_dump()["requrv_aws_access_key_id"],
    aws_secret_access_key=settings.model_dump()["requrv_aws_secret_access_key"],
    endpoint_url=settings.model_dump()["requrv_aws_endpoint"],
    region_name=settings.model_dump()["requrv_aws_region"],
)


def create_presigned_url(object_key, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client("s3")
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.model_dump()["requrv_aws_bucket"],
                "Key": object_key,
            },
            ExpiresIn=expiration,
        )
    except HTTPException as e:
        logging.error(e)
        raise e

    # The response contains the presigned URL
    return response


async def upload_file_to_s3(file: UploadFile, who_uploaded_it_user_id: str = None):
    """Upload a file to an S3 bucket"""
    try: 
        async with prisma.tx() as transaction:
            # generazione del file key
            file_extension = file.filename.split(".")[-1] if file.filename else ""
            file_key = "requrv-hub/" + otp.now() + "." + file_extension
            
            media_db = await transaction.media.create(
                data={
                    "key": file_key,
                    "name": file.filename,
                    "size": file.size,
                    "type": file.content_type,
                    "whoUploadedItUserId": who_uploaded_it_user_id,
                    # Add other necessary fields
                }
            )

            file_object = await file.read()

            s3_client.put_object(
                Body=file_object,
                Bucket=settings.model_dump()["requrv_aws_bucket"],
                Key=file_key,
                ContentType=file.content_type,
            )

            pass

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
   
    return media_db
    