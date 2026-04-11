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
        context_filtered : list[SearchResult[ContextPayload]] = context_results #self.cortex.context_filtering(classified_query,context_results) TODO context filter must be fine tuned
        logging.info(f"Context filtered: {context_filtered}")
        universe_results : list[SearchResult[UniversePayload]] =self.qdrant.search_universe(classified_query.optimized_query, [context.payload.document_id for context in context_filtered])
        logging.info(f"Universe results: {universe_results}")
        optimized_semantic_search_query = self.cortex.query_expansion(classified_query.original_query,context_filtered)
        logging.info(f"Optimized semantic query: {optimized_semantic_search_query}")

        print(f"Response with context filtered by document id:\n{self.cortex.response(optimized_semantic_search_query, universe_results)}")

        full_universe_results : list[SearchResult[UniversePayload]] =self.qdrant.search_universe(classified_query.original_query)
        logging.info(f"Universe full results: {full_universe_results}")
        print(f"Response with no filter:\n{self.cortex.response(optimized_semantic_search_query, full_universe_results)}")


    def start_chatting(self):
        logging.info("You can start chatting!")
        while True:
            user_input = input("\nTu: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input:
                continue
            self.query(user_input)