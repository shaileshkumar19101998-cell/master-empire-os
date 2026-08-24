import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any

def get_r2_client():
    endpoint_url = os.getenv("R2_ENDPOINT_URL", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()

    if not endpoint_url or not access_key or not secret_key:
        return None

    try:
        session = boto3.session.Session()
        return session.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
        )
    except Exception:
        return None

def object_exists(object_key: str) -> bool:
    client = get_r2_client()
    bucket = os.getenv("R2_BUCKET_NAME", "").strip()
    if not client or not bucket or not object_key:
        return False
    try:
        client.head_object(Bucket=bucket, Key=object_key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ["404", "NoSuchKey"]:
            return False
        return False
    except Exception:
        return False

def verify_upload_integrity(object_key: str, expected_size: int, expected_hash: Optional[str] = None) -> bool:
    """Verifies R2 object existence, Content-Length, and integrity via HeadObject."""
    client = get_r2_client()
    bucket = os.getenv("R2_BUCKET_NAME", "").strip()
    if not client or not bucket or not object_key:
        return False
    try:
        response = client.head_object(Bucket=bucket, Key=object_key)
        content_length = response.get("ContentLength", 0)
        if content_length != expected_size or content_length <= 0:
            return False
        
        # Verify metadata hash if present
        metadata = response.get("Metadata", {})
        if expected_hash and "sha256" in metadata:
            if metadata["sha256"] != expected_hash:
                return False
        return True
    except Exception:
        return False

def upload_pdf_bytes(pdf_bytes: bytes, object_key: str, sha256_hash: Optional[str] = None) -> bool:
    client = get_r2_client()
    bucket = os.getenv("R2_BUCKET_NAME", "").strip()
    if not client or not bucket or not object_key or not pdf_bytes:
        return False
    try:
        extra_args = {"ContentType": "application/pdf"}
        if sha256_hash:
            extra_args["Metadata"] = {"sha256": sha256_hash}

        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=pdf_bytes,
            **extra_args
        )
        return verify_upload_integrity(object_key, len(pdf_bytes), sha256_hash)
    except Exception:
        return False

def generate_presigned_download(object_key: str, expiry_seconds: int = 300) -> Optional[str]:
    client = get_r2_client()
    bucket = os.getenv("R2_BUCKET_NAME", "").strip()
    if not client or not bucket or not object_key:
        return None
    try:
        return client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expiry_seconds
        )
    except Exception:
        return None