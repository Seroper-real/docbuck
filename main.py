import argparse
import logging
from pathlib import Path

from fastembed import TextEmbedding

from agent import Agent
from ingestion.ingestion_chain import IngestionChain
from logger import setup_logger


def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="Dockbuck")
    subparser = parser.add_subparsers(dest="command")

    #Docling
    ingest_parser = subparser.add_parser("updoc", help="Upload documents in vectorstore")
    ingest_parser.add_argument("--path", help="Folder or File path")

    ingest_parser = subparser.add_parser("deldoc", help="Delete documents in vectorstore")
    ingest_parser.add_argument("--path", help="Folder or File path")

    #Qdrant
    qd_parser = subparser.add_parser("qd", help="Qdrant commands")
    qd_parser.add_argument("--models", action="store_true", help="List of available models")

    subparser.add_parser("chat", help="Start chatting with context")

    ingest_parser = subparser.add_parser("query", help="Ask a specific query")
    ingest_parser.add_argument("--text", help="The input query")

    args = parser.parse_args()

    try:
        if args.command == "updoc":
            ingestion_chain = IngestionChain()
            ingestion_chain.load(Path(args.path))
        elif args.command == "deldoc":
            ingestion_chain = IngestionChain()
            ingestion_chain.delete(Path(args.path))
        elif args.command == "chat":
            agent = Agent()
            agent.start_chatting()
        elif args.command == "query":
            agent = Agent()
            agent.chat(args.text)
        elif args.command == "qd":
            if args.models:
                print(f"{'Name':<40} | {'Dim':<6} | {'Description'}")
                print("-" * 80)
                supported_models = TextEmbedding.list_supported_models()
                for model in supported_models:
                    model_name = model.get("model")
                    dim = model.get("dim")
                    description = model.get("description", "No description")
                    print(f"{model_name:<40} | {dim:<6} | {description}")
        else:
            parser.print_help()

    except Exception as e:
        logging.error(f"{e}")

if __name__ == "__main__":
    main()