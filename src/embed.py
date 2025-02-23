import sys
import logging
from typing import Tuple
from openai import OpenAI
from settings import ModelConfig

class Embedder:
    def __init__(self, model_config: ModelConfig):
        self.client = OpenAI(base_url=model_config.base_url, api_key=model_config.api_key)
        self.model_config = model_config
        self.embedding_cache = {}
        self.logger = logging.getLogger(__name__)

    def get_embedding(self, text):
        if text in self.embedding_cache:
            self.logger.debug("Cache hit")
            return self.embedding_cache[text]
        self.logger.debug(f"Embedding text: {text}")
        response = self.client.embeddings.create(
            model=self.model_config.model_name,
            input=text
        )

        embedding = response.data[0].embedding
        self.embedding_cache[text] = embedding
        return embedding

    def euclidean_distance(self, vec1, vec2):
        """Calculate the Euclidean distance between two vectors."""
        squared_diff_sum = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
        return squared_diff_sum ** 0.5

    def manhattan_distance(self, vec1, vec2):
        """Calculate the Manhattan (L1) distance between two vectors."""
        return sum(abs(a - b) for a, b in zip(vec1, vec2))

    def compare_texts_euclidean(self, text1, text2):
        """Compare two texts using Euclidean distance."""
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        return self.euclidean_distance(embedding1, embedding2)

    def compare_texts_manhattan(self, text1, text2):
        """Compare two texts using Manhattan distance."""
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        return self.manhattan_distance(embedding1, embedding2)

    def cosine_similarity(self, vec1, vec2):
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot_product / (norm1 * norm2)

    def compare_texts_cosine(self, text1, text2):
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)
        similarity = self.cosine_similarity(embedding1, embedding2)
        return similarity

    def compare_texts_weighted(self, text1, text2, weights: Tuple[float, float]):
        weight_sum = sum(weights)
        if weight_sum != 1:
            raise ValueError("Weights must sum to 1.")
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)

        cosine_similarity = self.cosine_similarity(embedding1, embedding2)
        euclidean_distance = self.euclidean_distance(embedding1, embedding2)

        weighted_similarity = weights[0] * cosine_similarity + weights[1] * (1 - euclidean_distance)
        return weighted_similarity

if __name__ == "__main__":
    from dotenv import load_dotenv
    from settings import Settings
    load_dotenv()

    settings = Settings()  # type: ignore [call-arg]

    if len(sys.argv) != 3:
        print("Usage: python script.py 'text1' 'text2'" )
        sys.exit(1)

    text1 = sys.argv[1]
    text2 = sys.argv[2]

    embedder = Embedder(settings.embedding_model_config)
    similarity = embedder.compare_texts_cosine(text1, text2)
    print(f"Cosine similarity: {similarity}")
    euclidean_distance = embedder.compare_texts_euclidean(text1, text2)
    print(f"Euclidean distance: {euclidean_distance}")
    manhattan_distance = embedder.compare_texts_manhattan(text1, text2)
    print(f"Manhattan distance: {manhattan_distance}")
    weighted_similarity = embedder.compare_texts_weighted(text1, text2, (0.9,0.1))
    print(f"Weighted similarity: {weighted_similarity}")
