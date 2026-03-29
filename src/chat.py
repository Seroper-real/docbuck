import ollama
import config
from qdrant import Qdrant

class Chat:

    def __init__(self, qdrant:Qdrant):
        self.qdrant = qdrant
        self.chat_model = config.OL_CHAT_MODEL_NAME

    def chat(self, query:str):
        context_text = self.qdrant.get_context_results(query)

        prompt = f"""
            You are a helpful assistant. Answer the question using ONLY the provided context.
            If the answer is not in the context, say that you don't know.

            Context:
            {context_text}

            Question: {query}
            """

        stream = ollama.generate(
            model=self.chat_model,
            prompt=prompt,
            stream=True,
        )
        for chunk in stream:
            content = chunk['response']
            print(content, end="", flush=True)
        print()
