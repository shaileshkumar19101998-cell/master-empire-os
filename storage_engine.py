import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional

def get_r2_client():
    endpoint_url = os.getenv("R2_ENDPOINT_URL", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()

    if not endpoint_url or not access_key or not secret_key:
        return None

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        region_name="auto"
    )

def object_exists(object_key: str) -> bool:
    bucket_name = os.getenv("R2_BUCKET_NAME", "").strip()
    client = get_r2_client()
    if not client or not bucket_name:
        return False
    try:
        client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
            return False
        raise

def generate_presigned_download(object_key: str, expiry_seconds: int = 300) -> Optional[str]:
    bucket_name = os.getenv("R2_BUCKET_NAME", "").strip()
    client = get_r2_client()
    if not client or not bucket_name:
        return None
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=min(expiry_seconds, 300)
        )
        return url
    except ClientError:
        return None

def upload_pdf(local_file_path: str, object_key: str) -> bool:
    bucket_name = os.getenv("R2_BUCKET_NAME", "").strip()
    client = get_r2_client()
    if not client or not bucket_name:
        return False
    try:
        client.upload_file(
            local_file_path,
            bucket_name,
            object_key,
            ExtraArgs={"ContentType": "application/pdf"}
        )
        return True
    except ClientError:
        return False