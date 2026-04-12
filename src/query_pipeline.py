import logging

from cortex import Cortex
from models import ClassifiedQuery, SearchResult, ContextPayload, UniversePayload
from qdrant import Qdrant

class QueryPipeline:

    def __init__(self):
        self.qdrant = Qdrant()
        self.cortex = Cortex()

    def query(self, query:str) -> str:
        logging.info(f"Received query: {query}")
        categories: set[str] = self.qdrant.get_categories()
        logging.info(f"Retrieved categories: {categories}")
        classified_query : ClassifiedQuery = self.cortex.query_classification(query, categories)
        logging.info(f"Classified query: {classified_query}")
        context_results : list[SearchResult[ContextPayload]] = self.qdrant.search_context(classified_query)
        logging.info(f"Context results: {context_results}")
        universe_results : list[SearchResult[UniversePayload]] =self.qdrant.search_universe(classified_query.optimized_query, [context.payload.document_id for context in context_results])
        logging.info(f"Universe results: {universe_results}")
        universe_filtered : list[SearchResult[UniversePayload]] = self.cortex.context_filtering(classified_query,universe_results)
        logging.info(f"Universe results filtered: {universe_filtered}")
        optimized_semantic_search_query = self.cortex.query_expansion(classified_query.user_query, context_results)
        logging.info(f"Optimized semantic query: {optimized_semantic_search_query}")
        print(f"Response with context filtered by document id:\n{self.cortex.response(optimized_semantic_search_query, universe_filtered)}")

    def start_chatting(self):
        logging.info("You can start chatting!")
        while True:
            user_input = input("\nTu: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input:
                continue
            self.query(user_input)