import logging

from tools.cortex import Cortex
from models import ClassifiedQuery, SearchResult, ContextPayload, UniversePayload
from tools.qdrant import Qdrant

logger = logging.getLogger("chain")

class NeedlePickerChain:

    def __init__(self):
        self.qdrant = Qdrant()
        self.cortex = Cortex()

    def query(self, query:str) -> str:
        logging.debug(f"Received query: {query}")
        categories: set[str] = self.qdrant.get_categories()
        logging.debug(f"Retrieved categories: {categories}")
        classified_query : ClassifiedQuery = self.cortex.query_classification(query, categories)
        logging.debug(f"Classified query: {classified_query}")
        context_results : list[SearchResult[ContextPayload]] = self.qdrant.search_context(classified_query)
        logging.debug(f"Context results: {context_results}")
        universe_results : list[SearchResult[UniversePayload]] =self.qdrant.search_universe(classified_query.optimized_query, [context.payload.document_id for context in context_results])
        logging.debug(f"Universe results: {universe_results}")
        universe_filtered : list[SearchResult[UniversePayload]] = self.cortex.context_filtering(classified_query,universe_results)
        logging.debug(f"Universe results filtered: {universe_filtered}")
        optimized_semantic_search_query = self.cortex.query_expansion(classified_query.user_query, context_results)
        logging.debug(f"Optimized semantic query: {optimized_semantic_search_query}")
        return self.cortex.response(optimized_semantic_search_query, universe_filtered)
