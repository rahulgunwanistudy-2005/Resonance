import argparse
import logging
import time

from api.app.services.catalog import Catalog
from api.app.services.measure.jobs import expire_uploads, process_one
from resonance.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    catalog = Catalog(Settings.from_env())
    while True:
        expire_uploads(catalog)
        worked = process_one(catalog)
        if args.once:
            return
        if not worked:
            time.sleep(1)


if __name__ == "__main__":
    main()
