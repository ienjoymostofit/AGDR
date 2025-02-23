import sys
import logging
from typing import Tuple
from openai import OpenAI
from core.config import ModelConfig
import Levenshtein

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

    def are_similar(cosine_similarity, levenshtein_similarity):
        if cosine_similarity > 0.8 and levenshtein_similarity < 0.3:
            return "Different"
        else:
            return "Similar"


    def normalized_levenshtein_distance(self, s1, s2):
            """
            Calculates the normalized Levenshtein distance between two strings.

            The function is case-insensitive and ignores leading and trailing whitespaces.
            It returns a value between 0 and 1, where 0 means the strings are identical and 1 means they are completely different.
            """
            s1 = s1.strip().lower()
            s2 = s2.strip().lower()

            distance = Levenshtein.distance(s1, s2)
            max_len = max(len(s1), len(s2))

            if max_len == 0:
                return 0.0  # Handle empty strings case to avoid division by zero

            return distance / max_len

    def euclidean_distance(self, vec1, vec2):
        """Calculate the Euclidean distance between two vectors."""
        squared_diff_sum = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
        return squared_diff_sum ** 0.5

    def manhattan_distance(self, vec1, vec2):
        """Calculate the Manhattan (L1) distance between two vectors."""
        return sum(abs(a - b) for a, b in zip(vec1, vec2))

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

    def is_same_concept(self, text1, text2):
        text1 = text1.strip().replace(" ", "").lower()
        text2 = text2.strip().replace(" ", "").lower()
        embedding1 = self.get_embedding(text1)
        embedding2 = self.get_embedding(text2)

        # "Gustav V" "King Gustav V" : 0.86 with granite-embedding:30m-en, but also "Sweden" "Swedish" : 0.91, so not enough for our use case
        cosine_similarity = self.cosine_similarity(embedding1, embedding2)
        if cosine_similarity > 0.9:
            levenshtein_similarity = 1 - self.normalized_levenshtein_distance(text1, text2)
            if levenshtein_similarity > 0.7:
                return True
        else:
            return False

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
