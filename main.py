import argparse,config,logging,sys
from pathlib import Path
from src.ingest import Ingest

def setup_logger() -> None:
    """Configure the root logger using config.py settings."""
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.ERROR)

    logging.basicConfig(
        level=level,
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATEFMT,
        stream=sys.stdout
    )

def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="Dockbuck")
    subparser = parser.add_subparsers(dest="command")

    ingest_parser = subparser.add_parser("updoc", help="Upload documents in vectorstore")
    ingest_parser.add_argument("--path", help="Folder or File path")

    args = parser.parse_args()

    if args.command == "updoc":
        try:
            ingest = Ingest()
            ingest.load(Path(args.path))
        except Exception as e:
            logging.error(f"{e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()