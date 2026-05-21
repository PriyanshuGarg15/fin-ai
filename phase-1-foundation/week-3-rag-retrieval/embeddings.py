import os
import asyncio
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

gemini_client= genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def generate_embedding(text: str, model: str="gemini-embedding-2")->list[float]:
    """
    Generate embedding for a single text using Gemini.
    gemini-embedding-2 uses Matryoshka Representation Learning, allowing us to 
    freely scale the dimensions down without losing semantic meaning.
    """
    text= text.replace("\n", " ").strip()
    if not text:
        raise ValueError("Cannot embed empty text")
    response= await gemini_client.aio.models.embed_content(
        model=model,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=1536
        )
    )
    return response.embeddings[0].values

async def generate_embeddings_batch(text_list: list[str], model: str="gemini-embedding-2", batch_size: int=100)->list[list[float]]:
    """Generate embeddings for multiple texts efficiently using batching"""
    tasks = []
    for t in text_list:
        cleaned = t.replace("\n", " ").strip()
        # Queue up an individual embedding request for each string
        tasks.append(
            gemini_client.aio.models.embed_content(
                model=model,
                contents=cleaned,
                config=types.EmbedContentConfig(output_dimensionality=1536)
            )
        )
    
    print(f"Embedding {len(tasks)} texts concurrently...")
    
    # Execute all requests at the exact same time
    responses = await asyncio.gather(*tasks)
    
    # Extract the vector from each individual response
    return [resp.embeddings[0].values for resp in responses]

async def test_embeddings():
    text=[
        "A home loan requires income proof, identity documents, and property papers.",
        "Personal loans are unsecured and based on credit score and income.",
        "Business loans require GST registration, balance sheets, and ITR.",
        "Credit score below 650 typically results in loan rejection.",
        "FOIR is the ratio of fixed monthly obligations to gross monthly income."
    ]
    embeddings= await generate_embeddings_batch(text)
    print(f"Generated {len(embeddings)} embeddings, each of dimension {len(embeddings[0])}")

    #cosineSimilarity
    from numpy import dot
    from numpy.linalg import norm

    def cosine_similarity(a, b):
        return dot(a, b) / (norm(a) * norm(b))
    
    q_embedding= await generate_embedding("What credit score is needed for a loan?")
    similarities=[(text[i], cosine_similarity(q_embedding, embeddings[i])) for i in range(len(text))]
    similarities.sort(key=lambda x: x[1], reverse=True)
    print("\nSimilarity search results for 'What credit score is needed for a loan?':")
    for text, score in similarities:
        print(f"  [{score:.4f}] {text}")

if __name__ == "__main__":
    asyncio.run(test_embeddings())