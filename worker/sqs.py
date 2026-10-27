"""SQS queue adapter for cloud deployment."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient


def receive(client: "SQSClient", queue_url: str) -> tuple[str, str] | None:
    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=20,
        VisibilityTimeout=900,
    )
    messages = response.get("Messages", [])
    if not messages:
        return None
    return messages[0]["Body"], messages[0]["ReceiptHandle"]


def acknowledge(client: "SQSClient", queue_url: str, receipt: str) -> None:
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
