import json
import logging

import ollama
from pydantic import BaseModel, ValidationError

import config
from models import ClassifyResult, Context, Chunk


def _generate(model:str, prompt:str, system_prompt:str = None, response_format:str = 'json', temperature:float = 0) -> str:
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
        options={"temperature": temperature}
    )
    logging.debug(
        f"Generated: {response['response']}"
        "\n------------------------------- GENERATE END --------------------------------------------"
    )
    return response['response']


def _generate_to_model[T:BaseModel](model_class: type[T], model:str, prompt:str, system_prompt:str = None, temperature:float = 0) -> T:
    response = _generate(model,prompt,system_prompt,'json',temperature)
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

class Cortex:

    def __init__(self):
        self.chat_model = config.OL_CHAT_MODEL
        self.classify_model = config.OL_CLASSIFY_MODEL
        self.language = config.OL_CHAT_LANGUAGE
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
                {self._parse_categories_for_prompt(categories)}
                
                ### TASKS
                1. **Summarize**: Create a concise summary of the document in English.
                2. **Context**: Provide a 1-sentence "elevator pitch" that describes exactly what this specific document is about.
                3. **Category**: 
                    - Compare the document content with the CURRENT_CATEGORIES provided.
                    - If it fits an existing category, use it.
                    - If it does not fit any, define a new, concise category name (1-3 words).
                4. **Time Period**: 
                    - Identify if the document refers to a specific timeframe.
                    - If the document has a date in it or the nature of the document is time relevant (e.g., a bill), define a range of dates, using YYYY-MM-DD ad format
                        (e.g, for a document that say 2025, the range will be from 2025-01-01 to 2025-12-31)
                    - If the document is general or timeless (e.g., a technical manual), set both start_date and end_date to null.
                
                ### OUTPUT FORMAT
                Return ONLY a valid JSON object with the following structure:
                
                {{
                  "summary": "<Summary>",
                  "text": "<Context>",
                  "category": "<Category>",
                  "start_date": "<Date start or null>"
                  "end_date": "<Date End or null>"
                }}
            """
        return _generate_to_model(Context, self.summarize_model, prompt)

    def _context_from_summaries(self, tokenized_chunks: dict[int, tuple[int,Chunk]], categories: set[str]) -> Context:
        summarized_chunks = "\n".join([self._summarize_portion(index,[chunk]) for index, chunk in tokenized_chunks.values()]) #TODO pass more chunks at the time, within the limit of context_window
        prompt = f"""
            ### ROLE
            You are an Expert Metadata Architect. Your task is to analyze a collection of PRE-GENERATED SUMMARIES 
            from a document and consolidate them into a final global context for a RAG system.

            ### INPUT DATA
            PARTIAL_SUMMARIES:
            {summarized_chunks}

            EXISTING_SYSTEM_CATEGORIES:
            {self._parse_categories_for_prompt(categories)}

            ### TASKS
            1. **Final Summary**: Synthesize the partial summaries into a single, cohesive, and exhaustive overview in English.
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
              "text": "<Context>",
              "category": "<Category>",
              "start_date": "<Date start or null>"
              "end_date": "<Date End or null>"
            }}
        """
        return _generate_to_model(Context, self.summarize_model, prompt)

    def _summarize_portion(self, index:int, chunks: list[Chunk]) -> str:
        context = [chunk.content for chunk in chunks]  # Todo mettere [chunk metadata | chunk text]
        raw_context = "\n".join(context)
        logging.info(f"Summarize chunk index: {index} | Text: {raw_context}")

        prompt = f"""
            ### ROLE
            You are a precise Document Summarizer. 
            Your goal is to provide a concise and exhaustive summary of the provided text fragment.

            ### INPUT DATA
            TEXT_CHUNK:
            {raw_context}

            ### INSTRUCTIONS
            1. Summarize the content of the TEXT_CHUNK above.
            2. The summary must be exhaustive but concise.
            3. Provide the summary in English.
            4. **IMPORTANT**: Return ONLY the summary text. 
        """
        return _generate(self.summarize_model, prompt)

    def _parse_categories_for_prompt(self, categories: set[str]) -> str:
        return ",".join(categories) if categories else "None (You must define a new one)"

    ### prev
    def chat(self, query:str):
        data : ClassifyResult = self.classify(query)

        context_text = self.qdrant.get_context_results(data.user_query_optimized)

        system_prompt = f"""
            You are a helpful assistant. Answer the question using ONLY the provided context.
            If the answer is not in the context, say that you don't know. 
            Do not use outside knowledge.
            Talk in {self.language} 
            """

        user_content = f"""
            Context:
            {context_text}

            User request: {query}
            """

        stream = ollama.generate(
            model=self.chat_model,
            system=system_prompt,
            prompt=user_content,
            stream=True,
        )
        for chunk in stream:
            content = chunk['response']
            print(content, end="", flush=True)
        print()

    def start_chatting(self):
        logging.info("You can start chatting!")
        while True:
            user_input = input("\nTu: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input:
                continue
            self.chat(user_input)

    def classify(self,user_query:str) -> ClassifyResult:

        system_prompt = """
            You are a specialized intent classifier for a RAG (Retrieval-Augmented Generation) system.
            Analyze the user's input and provide a classification in strict JSON format.
            
            CLASSIFICATION CATEGORIES:
            - "SEARCH": Default category. Use when the user asks for specific facts, technical details, or general information across the entire knowledge base.
            - "SUMMARIZE": Use when the user explicitly requests a summary, synthesis, or overview of a full document or multiple documents.
            - "DOCUMENT_SPECIFIC": Use when the user's question is tied to a specific file name or an identifiable unique source mentioned in the prompt.
            
            OUTPUT REQUIREMENTS:
            - Return ONLY a JSON object.
            - Do not include explanations, greetings, or preamble.
            - Format: {"intent": "<CATEGORY>", "target_file": "<filename_string>" or null, "user_query_optimized": "<optimized version of the user query for vectorial database search>"}
            """

        response = ollama.generate(
            model=self.classify_model,
            system=system_prompt,
            prompt=user_query,
            format='json',
            options={
                "temperature": 0,
                #"num_predict": 50
            }
        )
        logging.debug(f"Classify output: {response}")

        try:
            raw_data = json.loads(response['response'])
            logging.debug(f"Classify output: {raw_data}")
            return ClassifyResult(**raw_data)
        except json.JSONDecodeError:
            # Fallback to default search if JSON is malformed
            logging.warning(f"Classify output has produced a malformed JSON: {response}")
            return ClassifyResult(intent="SEARCH",target_file=None,user_query_optimized=user_query)
