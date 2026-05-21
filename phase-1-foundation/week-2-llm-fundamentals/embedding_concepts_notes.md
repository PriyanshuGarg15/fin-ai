# Vector Embeddings — Conceptual Notes

## What is an embedding?
A vector (list of numbers) that represents the semantic meaning of text.
"Home loan" and "housing loan" produce vectors that are geometrically close.
"Home loan" and "cricket score" produce vectors that are geometrically far.

## Why does this matter for RAG?
When a user asks "what documents do I need for a loan?", we convert that question
to a vector, then find the document chunks whose vectors are closest.
This is semantic search — not keyword search.

## Key numbers to remember:
- OpenAI text-embedding-3-small: 1536 dimensions, $0.02/1M tokens
- OpenAI text-embedding-3-large: 3072 dimensions, $0.13/1M tokens
- Anthropic: no native embedding model (use OpenAI or Cohere for embeddings)

## Similarity metrics:
- Cosine similarity: angle between vectors (most common for text)
- Euclidean distance: absolute distance (less common)
- Dot product: directional + magnitude (used in some vector DBs)

## My mental model:
Embedding = GPS coordinate for meaning
Similarity search = "find all documents within 500m of this question"