import subprocess
import tarfile
from pathlib import Path


def main() -> None:
    output = Path("outputs/release.tar.gz")
    output.parent.mkdir(exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    with tarfile.open(output, "w:gz") as archive:
        for name in tracked:
            if (
                name
                and Path(name).is_file()
                and not name.startswith(("data/", "models/"))
            ):
                archive.add(name, arcname=name)
        for path in Path("web/dist").rglob("*"):
            if path.is_file():
                archive.add(path, arcname=str(path))
    print(f"Packaged tracked source and built console: {output}")


if __name__ == "__main__":
    main()
