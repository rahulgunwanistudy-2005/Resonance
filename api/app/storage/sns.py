from typing import TYPE_CHECKING

from api.app.schemas import ApprovalRecord, DomainError
from api.app.storage.local import LocalStore

if TYPE_CHECKING:
    from mypy_boto3_sns import SNSClient


def send_approved(
    client: "SNSClient", topic: str, store: LocalStore, approval_id: str
) -> str:
    approval = store.get("approval", approval_id, ApprovalRecord)
    if approval.status != "approved":
        raise DomainError(
            "Inspection notifications require a recorded human approval", 403
        )
    response = client.publish(
        TopicArn=topic,
        Subject="Resonance inspection review approved",
        Message=f"Inspection request {approval.id} for capture {approval.capture_id} was approved. Reason: {approval.reason}. Triage support; not structural certification.",
        MessageAttributes={
            "approval_id": {"DataType": "String", "StringValue": approval.id}
        },
    )
    return response["MessageId"]
