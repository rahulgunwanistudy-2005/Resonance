"""Start a local API plus separate durable worker, with a private local admin token."""

import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    import secrets
    from resonance.config import Settings, load_env_file

    loaded = load_env_file()
    if loaded:
        print(f"Loaded from .env: {', '.join(sorted(loaded))}", flush=True)
    settings = Settings.from_env()
    token_file = Path("outputs/local-admin-token")
    token_file.parent.mkdir(exist_ok=True)
    if settings.admin_token is None:
        if not token_file.exists():
            token_file.write_text(secrets.token_urlsafe(32))
            token_file.chmod(0o600)
        token = token_file.read_text().strip()
    else:
        token = settings.admin_token
    # Environment construction remains at the executable edge via config.
    from resonance.config import process_environment

    environment = process_environment(
        {
            "RESONANCE_ADMIN_TOKEN": token,
            "MPLCONFIGDIR": str(Path("outputs/matplotlib").resolve()),
        }
    )
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.app.main:app",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
            "--ws-max-size",
            "65536",
        ],
        [sys.executable, "-m", "worker.main"],
    ]
    processes = [subprocess.Popen(command, env=environment) for command in commands]

    stopping = False

    def stop(_signal: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True
        for process in processes:
            process.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(
        f"Local console: http://{settings.host}:{settings.port}; admin token: "
        + ("RESONANCE_ADMIN_TOKEN" if settings.admin_token else f"file {token_file}"),
        flush=True,
    )
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        if not stopping and any(
            process.poll() not in (None, 0) for process in processes
        ):
            raise RuntimeError(
                "The local API or worker stopped unexpectedly; check its startup log"
            )
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
