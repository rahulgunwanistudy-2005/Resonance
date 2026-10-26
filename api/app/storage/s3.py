"""Prepared AWS artifact adapter. Local mode never constructs cloud clients."""

from pathlib import Path
from typing import TYPE_CHECKING

from api.app.schemas import DomainError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class S3Artifacts:
    def __init__(self, client: "S3Client", bucket: str):
        self.client, self.bucket = client, bucket

    def put(self, capture_id: str, path: Path) -> str:
        if path.stat().st_size > 16 * 1024**2 or Path(capture_id).name != capture_id:
            raise DomainError(
                "Artifact exceeds its bound or has an invalid capture identifier"
            )
        key = f"evidence/{capture_id}/{path.name}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=path.read_bytes(),
            ServerSideEncryption="AES256",
        )
        return key

    def download_capture(self, key: str, destination: Path) -> None:
        metadata = self.client.head_object(Bucket=self.bucket, Key=key)
        if metadata["ContentLength"] > 200_000_000:
            raise DomainError("Cloud capture exceeds the upload limit")
        with destination.open("wb") as stream:
            self.client.download_fileobj(self.bucket, key, stream)
