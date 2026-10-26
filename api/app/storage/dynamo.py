from typing import TYPE_CHECKING

from resonance.agent.loop import AgentResult

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBClient


class DynamoMeasurements:
    def __init__(self, client: "DynamoDBClient", table: str):
        self.client, self.table = client, table

    def save(self, result: AgentResult) -> None:
        self.client.put_item(
            TableName=self.table,
            Item={
                "kind": {"S": "measurement"},
                "id": {"S": result.decision.capture_id},
                "bridge_id": {"S": result.decision.bridge_id},
                "body": {"S": result.model_dump_json()},
            },
            ConditionExpression="attribute_not_exists(id)",
        )
