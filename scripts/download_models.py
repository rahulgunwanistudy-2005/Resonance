"""Reproduce P0 downloads; weights remain untracked and redistribution is not authorized."""

import hashlib
import json
import urllib.request
from pathlib import Path


def main() -> None:
    manifest = json.loads(Path("eval/results/model_downloads.json").read_text())
    Path("models").mkdir(exist_ok=True)
    for name, record in manifest.items():
        if "sha256" not in record:
            raise RuntimeError(f"No verified download hash for {name}")
        target = Path("models") / name
        if (
            target.exists()
            and hashlib.sha256(target.read_bytes()).hexdigest() == record["sha256"]
        ):
            print(f"Verified existing {name}")
            continue
        temporary = target.with_suffix(".download")
        urllib.request.urlretrieve(record["url"], temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != record["sha256"]:
            temporary.unlink()
            raise RuntimeError(
                f"Hash mismatch for {name}; review the upstream export before using it"
            )
        temporary.replace(target)
        print(f"Downloaded and verified {name}")


if __name__ == "__main__":
    main()
