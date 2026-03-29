import argparse,config,logging,sys
from pathlib import Path

from chat import Chat
from qdrant import Qdrant
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

    subparser.add_parser("chat", help="Start chatting with context")

    args = parser.parse_args()

    qdrant = Qdrant()
    try:
        if args.command == "updoc":
                ingest = Ingest(qdrant)
                ingest.load(Path(args.path))
        elif args.command == "chat":
            ##Testing
            chat = Chat(qdrant)
            while True:
                user_input = input("\nTu: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input:
                    continue
                chat.chat(user_input)
        else:
            parser.print_help()

    except Exception as e:
        logging.error(f"{e}")

if __name__ == "__main__":
    main()