import json
import logging
from collections import defaultdict
from typing import Tuple

import ollama
from docling_core.transforms.chunker import BaseChunk

import config
from models import ClassifyResult
from qdrant import Qdrant

class Cortex:

    def __init__(self, qdrant:Qdrant):
        self.qdrant = qdrant
        self.chat_model = config.OL_CHAT_MODEL
        self.classify_model = config.OL_CLASSIFY_MODEL
        self.language = config.OL_CHAT_LANGUAGE
        self.summarize_model = config.OL_SUMMARIZE_MODEL
        self.summarize_model_context_window = config.OL_SUMMARIZE_MODEL_CONTEXT_WINDOW

    def summarize(self, chunks: list[BaseChunk]) -> str:
        #For now let's only make an estimate conversion from text to tokens using // 3
        tokenized_chunks: dict[int, tuple[int,BaseChunk]] = {}
        total_tokens = 0
        for i,chunk in enumerate(chunks):
            token = len(chunk.text) // 3
            total_tokens += token
            tokenized_chunks[i] = (token, chunk)

        if self._get_context_space(self.summarize_model_context_window < total_tokens):
            #TODO summarize all in one
            pass
        else:
            #TODO summarize at chunk rate
            pass


    def _get_context_space(self, context_window):
        #For now assume a fixed amount of free tokens
        return context_window - 1024

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
