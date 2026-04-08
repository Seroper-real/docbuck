import json
import logging

import ollama
from pydantic import BaseModel, ValidationError

import config
from models import ClassifyResult, Context, Chunk, ClassifiedQuery, SearchResult, ContextPayload, ContextFilterScore, \
    UniversePayload


def _generate(model:str, prompt:str, system_prompt:str = None, response_format:str = '', max_output_token:int = -1, temperature:float = 0.3) -> str:
    logging.debug(
        "------------------------------- GENERATE START ------------------------------------------\n"
        f"Generate input: model={model}, format={response_format}, "
        f"temperature={temperature}, prompt={prompt}, "
        f"system_prompt={system_prompt if system_prompt else 'None'}"
    )
    response = ollama.generate(
        model=model,
        system = system_prompt,
        prompt=prompt,
        format=response_format,
        options={
            "temperature": temperature,
            "num_predict": max_output_token,
        }
    )
    logging.debug(
        f"Generated: {response['response']}"
        "\n------------------------------- GENERATE END --------------------------------------------"
    )
    return response['response']


def _generate_to_model[T:BaseModel](model_class: type[T], model:str, prompt:str, system_prompt:str = None, max_output_token:int = -1, temperature:float = 0) -> T:
    response = _generate(model,prompt,system_prompt,'json',max_output_token, temperature)
    try:
        raw_data = json.loads(response)
        return model_class(**raw_data)
    except (json.JSONDecodeError, ValidationError):
        logging.warning(f"Classify output has produced a malformed JSON: {response}")
        raise


def _get_context_space(context_window:int) -> int:
    #For now assume a fixed amount of free tokens
    return context_window - 1024

def _calculate_tokens(text:str) -> int:
    # For now let's only make an estimate conversion from text to tokens using // 3
    return len(text) // 3


def _parse_categories_for_prompt(categories: set[str]) -> str:
    return ",".join(categories) if categories else "None"


class Cortex:

    def __init__(self):
        self.chat_model = config.OL_CHAT_MODEL
        self.classify_model = config.OL_CLASSIFY_MODEL
        self.output_language = config.OL_CHAT_LANGUAGE
        self.processing_language = config.OL_PROCESSING_LANGUAGE
        self.summarize_model = config.OL_SUMMARIZE_MODEL
        self.summarize_model_context_window = config.OL_SUMMARIZE_MODEL_CONTEXT_WINDOW

    def extract_context_info(self, chunks: list[Chunk], categories: set[str]) -> Context:
        tokenized_chunks: dict[int, tuple[int,Chunk]] = {}
        total_tokens = 0
        for chunk in chunks:
            token = _calculate_tokens(chunk.content)
            total_tokens += token
            tokenized_chunks[chunk.chunk_index] = (token, chunk)

        if _get_context_space(self.summarize_model_context_window) >= total_tokens:
            return self._context_from_document(chunks, categories)
        else:
            return self._context_from_summaries(tokenized_chunks, categories)

    def _context_from_document(self, chunks: list[Chunk], categories: set[str]) -> Context:
        context = [chunk.content for chunk in chunks] #Todo mettere [chunk metadata | chunk text]
        raw_context = "\n".join(context)

        prompt = f"""
            ### ROLE
                You are a professional Document Classifier and Summarizer. Your goal is to analyze the provided text and extract structured metadata for a RAG (Retrieval-Augmented Generation) system.
                
                ### INPUT DATA
                DOCUMENT_TEXT:
                {raw_context}
                
                CURRENT_CATEGORIES:
                {_parse_categories_for_prompt(categories)}
                
                ### TASKS
                1. **Summarize**: Create a concise summary of the document in {self.processing_language}.
                2. **Context**: Provide a 1-sentence "elevator pitch" that describes exactly what this specific document is about.
                3. **Category**: 
                    - Compare the document content with the CURRENT_CATEGORIES provided.
                    - If it fits an existing category, use it.
                    - If it does not fit any, define a new, concise category name (1-3 words).
                    - If category is None, you must define a new one
                4. **Time Period**: 
                    - Identify if the document refers to a specific timeframe.
                    - If the document has a date in it or the nature of the document is time relevant (e.g., a bill), define a range of dates, using YYYY-MM-DD ad format
                        (e.g, for a document that say 2025, the range will be from 2025-01-01 to 2025-12-31)
                    - If the document is general or timeless (e.g., a technical manual), set both start_date and end_date to null.
                
                ### OUTPUT FORMAT
                Return ONLY a valid JSON object with the following structure:
                
                {{
                  "summary": "<Summary>",
                  "content": "<Context>",
                  "category": "<Category>",
                  "start_date": "<Date start or null>"
                  "end_date": "<Date End or null>"
                }}
            """
        return _generate_to_model(Context, self.summarize_model, prompt)

    def _context_from_summaries(self, tokenized_chunks: dict[int, tuple[int,Chunk]], categories: set[str]) -> Context:
        summarized_chunks = ""
        available_tokens = _get_context_space(self.summarize_model_context_window)
        current_tokens = 0
        batch = []
        for index, (token, chunk) in sorted(tokenized_chunks.items()):
            if current_tokens + token > available_tokens:
                if batch:
                    summarized_chunks += f"{self._summarize_portion(batch)}\n"
                else:
                    #This is the case where a single chunk is larger than the context windows. Unrealistic.
                    #For now let's just pass it as is
                    logging.warning(f"Found a chunk larger than the contex window: {self.summarize_model_context_window} Chunk: {chunk.content}")
                    summarized_chunks += f"{self._summarize_portion([chunk])}\n"
                    current_tokens = 0
                    continue

                current_tokens = 0
                batch.clear()

            current_tokens += token
            batch.append(chunk)

        if batch:
            summarized_chunks += f"{self._summarize_portion(batch)}\n"

        prompt = f"""
            ### ROLE
            You are an Expert Metadata Architect. Your task is to analyze a collection of PRE-GENERATED SUMMARIES 
            from a document and consolidate them into a final global context for a RAG system.

            ### INPUT DATA
            PARTIAL_SUMMARIES:
            {summarized_chunks}

            EXISTING_SYSTEM_CATEGORIES:
            {_parse_categories_for_prompt(categories)}

            ### TASKS
            1. **Final Summary**: Synthesize the partial summaries into a single, cohesive, and exhaustive overview in {self.processing_language}.
            2. **Global Context**: Provide a 1-sentence "elevator pitch" that defines the document's core identity.
            3. **Category Refinement**: 
               - Look at the EXISTING_SYSTEM_CATEGORIES. 
               - Assign the most appropriate one or, if the document introduces a new distinct topic, 
                 create a new concise category (1-3 words).
            4. **Temporal Consolidation**: 
               - Scan the summaries for date references.
               - If a specific timeframe emerges (e.g., "Fiscal Year 2025"), set the range YYYY-MM-DD.
               - If the document is general or timeless (e.g., a technical manual), set both start_date and end_date to null.

            ### CONSTRAINTS
            - Do not invent details not present in the summaries.
            - Focus on the "big picture" rather than repeating every single detail.
            - Output MUST be a valid JSON object.

            ### OUTPUT FORMAT
            {{
              "summary": "<Summary>",
              "content": "<Context>",
              "category": "<Category>",
              "start_date": "<Date start or null>"
              "end_date": "<Date End or null>"
            }}
        """
        return _generate_to_model(Context, self.summarize_model, prompt)

    def _summarize_portion(self, chunks: list[Chunk]) -> str:
        context = [chunk.content for chunk in chunks]
        raw_context = "\n".join(context)
        logging.info(f"Summarize {len(chunks)} chunks | Text: {raw_context.replace('\n', '\\n')}")

        output_prefix = "<SUMMARY>"
        prompt = f"""
            ### ROLE
            You are a precise Document Summarizer.
    
            ### INPUT DATA
            TEXT_CHUNK:
            {raw_context}
    
            ### INSTRUCTIONS
            1. Summarize the content of the TEXT_CHUNK above.
            2. The summary must be exhaustive but concise.
            3. Provide the summary in {self.processing_language}.
            4. Do NOT include any preamble, introduction, or closing remarks.
            5. Do NOT use markdown formatting.
            6. Start DIRECTLY with the summary content.
    
            ### OUTPUT
            {output_prefix}
            """
        return _generate(self.summarize_model, prompt, max_output_token=1024).strip().removeprefix(output_prefix).strip()

    def query_classification(self, user_query:str, categories: set[str]) -> ClassifiedQuery:
        prompt = f"""
            ### ROLE
            You are a precise Query Analyzer for a RAG system.
            Your goal is to analyze the user query and extract structured information to optimize document retrieval.
    
            ### AVAILABLE CATEGORIES
            {_parse_categories_for_prompt(categories)}
    
            ### INPUT
            USER_QUERY: {user_query}
    
            ### INSTRUCTIONS
            1. Select the most relevant categories from AVAILABLE CATEGORIES that match the query intent. Return an empty list if none match.
            2. Detect if the query refers to a specific date range. Extract start and end date if present, otherwise set both to null.
            3. Generate an optimized query for vector search: rephrase it to maximize semantic similarity with relevant document chunks.
            4. Return the original query in {self.processing_language}.
    
            ### CONSTRAINTS
            - Return ONLY a valid JSON object, no preamble, no markdown, no explanation.
            - Dates must be in ISO 8601 format (YYYY-MM-DD) or null.
            - The optimized query must be in {self.processing_language}.
    
            ### OUTPUT FORMAT
            {{
                "categories": ["category1", "category2"],
                "start_date": "YYYY-MM-DD or null"
                "end_date": "YYYY-MM-DD or null"
                "optimized_query": "...",
                "original_query": "..."
            }}
            """
        return _generate_to_model(ClassifiedQuery, self.classify_model, prompt)

    def context_filtering(self, query: ClassifiedQuery, datas: list[SearchResult[ContextPayload]], threshold: float = 0.7):
        for data in datas:
            data.context_score = self._calculate_document_relevance(query.original_query, data.payload.summary)
        return [data for data in datas if data.context_score.score > threshold]

    def _calculate_document_relevance(self, query: str, document_summary: str) -> ContextFilterScore:
        prompt = f"""
            ### ROLE
            You are a precise Relevance Evaluator for a RAG system.
            Your goal is to evaluate how relevant a document is to the user query.

            ### USER QUERY
            {query}

            ### DOCUMENT SUMMARY
            {document_summary}

            ### INSTRUCTIONS
            1. Analyze how relevant the DOCUMENT SUMMARY is to the USER QUERY.
            2. Assign a relevance score between 0.0 and 1.0 where:
               - 0.0 = completely irrelevant
               - 0.5 = partially relevant
               - 1.0 = perfectly relevant
            3. Provide a brief justification for the score.

            ### CONSTRAINTS
            - Return ONLY a valid JSON object, no preamble, no markdown, no explanation.

            ### OUTPUT FORMAT
            {{
                "score": 0.0,
                "reason": "..."
            }}
            """
        return _generate_to_model(ContextFilterScore, model=self.summarize_model, prompt=prompt)

    def query_expansion(self, original_query: str, contexts: list[SearchResult[ContextPayload]]) -> str:
        output_prefix = "<QUERY>"
        prompt = f"""
            ### ROLE
            You are a precise Query Optimizer for a RAG system.
            Your goal is to expand and optimize the user query based on the available context summaries.
    
            ### ORIGINAL QUERY
            {original_query}
    
            ### AVAILABLE CONTEXTS
            {"\n".join([context.payload.summary for context in contexts])}
    
            ### INSTRUCTIONS
            1. Analyze the ORIGINAL QUERY and the AVAILABLE CONTEXTS.
            2. Generate an expanded query that:
               - Preserves the original intent of the user
               - Incorporates relevant terminology and concepts from the AVAILABLE CONTEXTS
               - Maximizes semantic similarity with the document chunks
            3. The expanded query must be in English.
    
            ### CONSTRAINTS
            - Provide the optimized query in {self.processing_language}.
            - Do NOT include any preamble, introduction, or closing remarks.
            - Do NOT use markdown formatting.
            - Start DIRECTLY with the optimized query.

            ### OUTPUT FORMAT
            {output_prefix}
            """
        return _generate(self.summarize_model, prompt).strip().removeprefix(output_prefix).strip()

    def response(self, optimized_query: str, contexts: list[SearchResult[UniversePayload]]) -> str:
        chunks = "\n\n".join([
            f"[{r.payload.document_id}] {r.payload.content}" #TODO document name
            for r in contexts
        ])
        prompt = f"""
            ### ROLE
            You are a precise Question Answering assistant.
            Your goal is to answer the user query based exclusively on the provided document chunks.
    
            ### USER QUERY
            {optimized_query}
    
            ### DOCUMENT CHUNKS
            {chunks}
    
            ### INSTRUCTIONS
            1. Answer the USER QUERY using ONLY the information provided in the DOCUMENT CHUNKS.
            2. If the answer is not present in the chunks, say explicitly that you don't have enough information to answer.
            3. Be concise and precise.
            4. Do not hallucinate or infer information not present in the chunks.
    
            ### CONSTRAINTS
            - Do NOT use markdown formatting.
            - Do NOT include preamble or closing remarks.
            - Start DIRECTLY with the answer.
            - Talk in {self.output_language} 
            """
        return _generate(self.summarize_model,prompt)