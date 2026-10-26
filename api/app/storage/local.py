import hashlib
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from api.app.schemas import ApprovalInput, ApprovalRecord, CaptureRecord, DomainError

T = TypeVar("T", bound=BaseModel)


class LocalStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS documents(kind TEXT, id TEXT, bridge_id TEXT,
                    created REAL, body TEXT, PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, state TEXT,
                    lease REAL DEFAULT 0, attempts INTEGER DEFAULT 0, error TEXT);
                CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY, token_hash TEXT,
                    expires REAL, claimed INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS limits(key TEXT, bucket INTEGER, count INTEGER,
                    PRIMARY KEY(key,bucket));
                CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, approval_id TEXT UNIQUE,
                    state TEXT DEFAULT 'pending');
                CREATE INDEX IF NOT EXISTS documents_bridge ON documents(kind,bridge_id,created);
            """)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind: str, key: str, value: BaseModel, bridge_id: str = "") -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
                (kind, key, bridge_id, time.time(), value.model_dump_json()),
            )

    def get(self, kind: str, key: str, model: type[T]) -> T:
        with self.connection() as db:
            row = db.execute(
                "SELECT body FROM documents WHERE kind=? AND id=?", (kind, key)
            ).fetchone()
        if row is None:
            raise DomainError("Resource not found", 404)
        return model.model_validate_json(row["body"])

    def list(
        self, kind: str, model: type[T], bridge_id: str | None = None, limit: int = 100
    ) -> list[T]:
        with self.connection() as db:
            if bridge_id is None:
                rows = db.execute(
                    "SELECT body FROM documents WHERE kind=? ORDER BY created DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT body FROM documents WHERE kind=? AND bridge_id=? ORDER BY created DESC LIMIT ?",
                    (kind, bridge_id, limit),
                ).fetchall()
        return [model.model_validate_json(row["body"]) for row in rows]

    def limit(self, key: str, maximum: int = 12) -> None:
        bucket = int(time.time() // 60)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM limits WHERE bucket < ?", (bucket - 2,))
            db.execute(
                "INSERT INTO limits VALUES(?,?,1) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1",
                (key, bucket),
            )
            count = db.execute(
                "SELECT count FROM limits WHERE key=? AND bucket=?", (key, bucket)
            ).fetchone()[0]
        if count > maximum:
            raise DomainError(
                "Too many requests; wait before starting another upload", 429
            )

    def ticket(self, capture_id: str, token: str, expires: float) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO uploads(id,token_hash,expires) VALUES(?,?,?)",
                (capture_id, hashlib.sha256(token.encode()).hexdigest(), expires),
            )

    def claim_upload(self, capture_id: str, token: str) -> None:
        with self.connection() as db:
            cursor = db.execute(
                "UPDATE uploads SET claimed=1 WHERE id=? AND token_hash=? AND expires>? AND claimed=0",
                (capture_id, hashlib.sha256(token.encode()).hexdigest(), time.time()),
            )
            if cursor.rowcount != 1:
                raise DomainError(
                    "Upload token is invalid, expired or already used; start a new upload",
                    403,
                )

    def enqueue(self, capture_id: str) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO jobs(id,state) VALUES(?,'queued')", (capture_id,))

    def claim_job(self) -> str | None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            exhausted = db.execute(
                "SELECT id FROM jobs WHERE state='processing' AND lease<? AND attempts>=3",
                (time.time(),),
            ).fetchall()
            for item in exhausted:
                db.execute(
                    "UPDATE jobs SET state='failed',error='Worker lease retries exhausted' WHERE id=?",
                    (item["id"],),
                )
                document = db.execute(
                    "SELECT body FROM documents WHERE kind='capture' AND id=?",
                    (item["id"],),
                ).fetchone()
                if document is not None:
                    record = CaptureRecord.model_validate_json(document["body"])
                    record.status = "failed"
                    record.error = (
                        "Worker retries were exhausted; start a new measurement"
                    )
                    db.execute(
                        "UPDATE documents SET body=? WHERE kind='capture' AND id=?",
                        (record.model_dump_json(), item["id"]),
                    )
            row = db.execute(
                "SELECT id FROM jobs WHERE (state='queued' OR state='processing' AND lease<?) AND attempts<3 ORDER BY rowid LIMIT 1",
                (time.time(),),
            ).fetchone()
            if row is None:
                return None
            key = str(row["id"])
            db.execute(
                "UPDATE jobs SET state='processing',lease=?,attempts=attempts+1 WHERE id=?",
                (time.time() + 900, key),
            )
            return key

    def expired_captures(self, cutoff: float) -> Iterator[CaptureRecord]:
        with self.connection() as db:
            cursor = db.execute(
                "SELECT body FROM documents WHERE kind='capture' AND created<?",
                (cutoff,),
            )
            while rows := cursor.fetchmany(100):
                for row in rows:
                    yield CaptureRecord.model_validate_json(row["body"])

    def received(self, record: CaptureRecord) -> None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE documents SET body=? WHERE kind='capture' AND id=?",
                (record.model_dump_json(), record.capture.id),
            )
            db.execute(
                "INSERT INTO jobs(id,state) VALUES(?,'queued')", (record.capture.id,)
            )

    def finish_job(self, capture_id: str, error: str | None = None) -> None:
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET state=?,error=? WHERE id=?",
                ("failed" if error else "complete", error, capture_id),
            )

    def resolve_approval(self, key: str, value: ApprovalInput) -> ApprovalRecord:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT body FROM documents WHERE kind='approval' AND id=?", (key,)
            ).fetchone()
            if row is None:
                raise DomainError("Approval not found", 404)
            approval = ApprovalRecord.model_validate_json(row["body"])
            target = "approved" if value.approved else "rejected"
            if approval.status != "pending":
                if approval.status == target and approval.reason == value.reason:
                    return approval
                raise DomainError("This approval has already been resolved", 409)
            approval.status = "approved" if value.approved else "rejected"
            approval.reason = value.reason
            approval.resolved_at = datetime.now(UTC)
            approval.delivery = "pending" if value.approved else "not_requested"
            db.execute(
                "UPDATE documents SET body=? WHERE kind='approval' AND id=?",
                (approval.model_dump_json(), key),
            )
            if value.approved:
                db.execute(
                    "INSERT INTO outbox(id,approval_id) VALUES(?,?) ON CONFLICT DO NOTHING",
                    (key, key),
                )
            return approval

    def local_receipts(self) -> int:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT approval_id FROM outbox WHERE state='pending'"
            ).fetchall()
            for row in rows:
                approval_row = db.execute(
                    "SELECT body FROM documents WHERE kind='approval' AND id=?",
                    (row[0],),
                ).fetchone()
                approval = ApprovalRecord.model_validate_json(approval_row[0])
                if approval.status != "approved":
                    raise DomainError(
                        "Notification outbox contains an unapproved alert", 409
                    )
                approval.delivery = "recorded_locally"
                db.execute(
                    "UPDATE documents SET body=? WHERE kind='approval' AND id=?",
                    (approval.model_dump_json(), approval.id),
                )
                db.execute(
                    "UPDATE outbox SET state='recorded_locally' WHERE approval_id=?",
                    (approval.id,),
                )
            return len(rows)
