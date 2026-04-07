import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    """
    Generates embeddings for text batches using a Sentence Transformer model.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initializes the EmbeddingGenerator by loading the specified Sentence Transformer model.

        Args:
            model_name: The name of the pre-trained model to load from Hugging Face.
        """
        self.model = SentenceTransformer(model_name)
        # The output dimension of 'all-MiniLM-L6-v2' is 384
        self.vector_size = self.model.get_sentence_embedding_dimension()

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embeds a batch of texts into a NumPy array of vectors.

        Args:
            texts: A list of strings to embed.

        Returns:
            A NumPy array where each row is the embedding for the corresponding text.
        """
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=True)
        return embeddings

if __name__ == "__main__":
    # Example usage:
    embedder = EmbeddingGenerator()
    texts_to_embed = [
        "This is an example sentence.",
        "Each sentence is converted to a vector.",
        "Embeddings capture semantic meaning.",
        "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python.",
        "It is based on standard Python type hints."
    ]

    print(f"Embedding {len(texts_to_embed)} texts...")
    embeddings = embedder.embed_batch(texts_to_embed)

    print(f"Generated embeddings with shape: {embeddings.shape}")
    print(f"Vector size: {embedder.vector_size}")
    print("First embedding sample:", embeddings[0][:5]) # Print first 5 dimensions of the first embedding
