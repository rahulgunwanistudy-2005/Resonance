from datetime import UTC, datetime
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber

from api.app.schemas import ApprovalRecord, DomainError
from api.app.storage.local import LocalStore
from api.app.storage.sns import send_approved


def test_prepared_sns_boundary_refuses_unapproved_and_uses_recorded_reason(
    tmp_path: Path,
) -> None:
    store = LocalStore(tmp_path / "db")
    approval = ApprovalRecord(
        id="approval",
        bridge_id="bridge",
        capture_id="capture",
        created_at=datetime.now(UTC),
    )
    store.put("approval", approval.id, approval)
    client = boto3.client(
        "sns",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    with Stubber(client) as stubber:
        with pytest.raises(DomainError):
            send_approved(
                client, "arn:aws:sns:us-east-1:123456789012:review", store, approval.id
            )
        approval.status = "approved"
        approval.reason = "Reviewed actual evidence"
        store.put("approval", approval.id, approval)
        stubber.add_response("publish", {"MessageId": "local-stub-message"})
        assert (
            send_approved(
                client, "arn:aws:sns:us-east-1:123456789012:review", store, approval.id
            )
            == "local-stub-message"
        )
        stubber.assert_no_pending_responses()
