import boto3
from typing import List
from pathlib import Path


def list_page_keys(bucket: str, prefix: str, region: str | None = None) -> List[str]:
    session = boto3.session.Session(region_name=region) if region else boto3.session.Session()
    s3 = session.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    keys: List[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if isinstance(key, str) and key.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                keys.append(key)
    return sorted(keys)


def download_s3_key(
    bucket: str,
    key: str,
    dest_path: Path,
    region: str | None = None,
) -> None:
    session = boto3.session.Session(region_name=region) if region else boto3.session.Session()
    s3 = session.client("s3")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(dest_path))
