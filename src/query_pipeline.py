import logging

from cortex import Cortex
from models import ClassifiedQuery, SearchResult, ContextPayload, UniversePayload
from qdrant import Qdrant


class QueryPipeline:

    def __init__(self):
        self.qdrant = Qdrant()
        self.cortex = Cortex()

    def query(self, query:str) -> str:
        categories: set[str] = self.qdrant.get_categories()
        classified_query : ClassifiedQuery = self.cortex.query_classification(query, categories)
        context_results : list[SearchResult[ContextPayload]] = self.qdrant.search_context(classified_query)
        context_filtered : list[SearchResult[ContextPayload]] = context_results #self.cortex.context_filtering(classified_query,context_results) TODO context filter must be fine tuned
        universe_results : list[SearchResult[UniversePayload]] =self.qdrant.search_universe(classified_query, [context.payload.document_id for context in context_filtered])
        optimized_semantic_search_query = self.cortex.query_expansion(classified_query.original_query,context_filtered)
        return self.cortex.response(optimized_semantic_search_query, universe_results)

    def start_chatting(self):
        logging.info("You can start chatting!")
        while True:
            user_input = input("\nTu: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input:
                continue
            logging.info(self.query(user_input))