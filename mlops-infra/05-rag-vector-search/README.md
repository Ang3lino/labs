# Lab 05 — RAG Pipeline (Vector Search + Embeddings)

## Summary

Build a Retrieval-Augmented Generation pipeline: embed documents into a vector database, retrieve relevant chunks at query time, and ground LLM responses with real data. This is how enterprise AI avoids hallucination.

## Problem It Solves

LLMs hallucinate. They confidently state wrong facts because they only know their training data (stale, generic). Your company has:
- Internal docs, SOWs, architecture decisions
- Jira tickets, Confluence pages, Slack threads
- Customer data that was never in any training set

RAG solves this: "Before answering, search our documents for relevant context, then answer ONLY based on what you found." No hallucination because the answer is grounded in retrieved evidence.

## How It Works Under the Hood

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAG Pipeline                                  │
│                                                                  │
│  INDEXING (offline, once per document update)                    │
│  ┌──────┐    ┌──────────┐    ┌───────────┐    ┌────────────┐   │
│  │ Docs │───>│ Chunker  │───>│ Embedding │───>│ Vector DB  │   │
│  │ PDF  │    │ 512 tok  │    │ Model     │    │ (Qdrant/   │   │
│  │ DOCX │    │ overlap  │    │ text →    │    │  Milvus/   │   │
│  │ MD   │    │ 50 tok   │    │ [0.1,0.3  │    │  pgvector) │   │
│  └──────┘    └──────────┘    │  ...0.7]  │    └────────────┘   │
│                               └───────────┘                      │
│                                                                  │
│  RETRIEVAL (online, per user query)                             │
│  ┌──────────┐    ┌───────────┐    ┌────────────┐               │
│  │ User     │───>│ Embed     │───>│ Vector DB  │               │
│  │ question │    │ query     │    │ similarity │               │
│  └──────────┘    └───────────┘    │ search     │               │
│                                    │ top-K=5    │               │
│                                    └──────┬─────┘               │
│                                           │                      │
│  GENERATION                               ▼                      │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ LLM Prompt:                                            │     │
│  │ "Answer based ONLY on the following context:           │     │
│  │  [chunk 1] [chunk 2] [chunk 3] [chunk 4] [chunk 5]    │     │
│  │                                                        │     │
│  │  Question: {user question}                             │     │
│  │  Answer:"                                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                         │                                        │
│                         ▼                                        │
│                   Grounded answer (with citations)                │
└─────────────────────────────────────────────────────────────────┘
```

**Key concepts:**

| Concept | What it is | Why it matters |
|---|---|---|
| **Embedding** | Text → dense vector (768-1536 dimensions) | Similar text = similar vectors = findable |
| **Chunking** | Split documents into ~512 token pieces | LLM context is limited; chunks are retrieval units |
| **Vector DB** | Database optimized for nearest-neighbor search | Find the 5 most relevant chunks in <50ms across millions |
| **Similarity search** | Cosine similarity between query embedding and stored embeddings | "Which chunks are semantically closest to the question?" |
| **Top-K retrieval** | Return K most similar chunks | Balance: too few = missed context, too many = noise |
| **Context window stuffing** | Inject retrieved chunks into LLM prompt | Ground the model in factual evidence |

**Why chunking strategy matters:**

```
Too large (2000 tokens):
  - Retrieves irrelevant content alongside relevant
  - Wastes LLM context window
  
Too small (100 tokens):
  - Loses context (a sentence without its paragraph)
  - May not contain enough info to answer

Sweet spot (400-600 tokens with 50-100 overlap):
  - Each chunk is a coherent thought
  - Overlap prevents cutting important context at boundaries
```

**Embedding models (2026 landscape):**

| Model | Dimensions | Quality | Speed | Notes |
|---|---|---|---|---|
| `text-embedding-3-small` (OpenAI) | 1536 | Good | API call | Paid, cloud |
| `text-embedding-3-large` (OpenAI) | 3072 | Best | API call | Paid, cloud |
| `BAAI/bge-large-en-v1.5` | 1024 | Very good | Local GPU | Free, open-source |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Decent | Local CPU | Fast, lightweight |
| `nomic-embed-text` (Ollama) | 768 | Good | Local | Free, runs on ollama |

## Alternatives & When to Pick

| Tool | When to pick | When NOT |
|---|---|---|
| **Qdrant** | Best open-source vector DB. Rust, fast, rich filtering. | If you need SQL alongside vectors (use pgvector) |
| **pgvector** | Already using PostgreSQL. Don't want another database. | Large scale (>10M vectors), need advanced features |
| **Milvus** | Massive scale (billions of vectors), distributed. | Small/medium scale (overkill), simpler setups |
| **ChromaDB** | Prototyping, local dev, simplest API. | Production at scale (single-node, not battle-tested) |
| **Pinecone** | Managed, zero-ops, just works. | On-prem requirement, cost-sensitive |
| **Weaviate** | Multi-modal (text + images), GraphQL API. | Pure text RAG where Qdrant/pgvector suffice |
| **FAISS (Meta)** | In-memory, research, fastest raw speed. | Need persistence, filtering, production features |

**Decision rule**: Prototyping → ChromaDB. Production on-prem → Qdrant or pgvector. Enterprise scale → Milvus.

## Industry Scenarios

| Company / Pattern | RAG Implementation |
|---|---|
| **HPE AI Platform** (your project) | RAG over internal docs (SharePoint, Jira, Confluence), vector DB, metadata filtering, access control per source |
| **GitHub Copilot** | RAG over repository context (current file + imports + similar code) |
| **Notion AI** | RAG over workspace pages, respecting permission boundaries |
| **Enterprise support bots** | RAG over knowledge base articles, route to human if confidence low |
| **Legal AI** | RAG over case law + statutes, cite exact source paragraphs |
| **Medical AI** | RAG over clinical guidelines, ground recommendations in evidence |

## Key Terms

- `Embedding model` — converts text to dense vectors
- `Vector database` — stores and searches embeddings
- `Chunking` — splitting documents into retrieval units
- `Top-K retrieval` — return K nearest neighbors
- `Cosine similarity` — measure of vector angle (1.0 = identical direction)
- `Hybrid search` — combine vector similarity + keyword (BM25) search
- `Re-ranking` — refine initial retrieval with a cross-encoder
- `Metadata filtering` — restrict search by document attributes (team, date, type)
- `Hallucination grounding` — limiting LLM to retrieved context only
- `RAG evaluation` — faithfulness, relevance, answer correctness metrics
- `Context window` — max tokens the LLM can process at once

## Interview Talking Points

"I built a RAG pipeline for internal documentation: documents are chunked at 512 tokens with 50-token overlap, embedded with BGE-large, and stored in Qdrant. At query time, the user question is embedded and we retrieve top-5 chunks via cosine similarity with metadata filtering (team, document type). These chunks are injected into the LLM prompt with instructions to answer only from the provided context. We measure faithfulness and relevance using RAGAS metrics and re-index nightly as documents change."

## Exercises

### Exercise 1: Embed and store documents (minimal)

```python
# rag_basic.py
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from pathlib import Path
import uuid

# 1. Load embedding model (runs locally, no API key)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# 2. Start Qdrant (in-memory for this exercise)
client = QdrantClient(":memory:")  # or QdrantClient("http://localhost:6333") for persistent

# 3. Create collection
client.create_collection(
    collection_name="docs",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# 4. Chunk and embed documents
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

# Load your converted markdown files (from file-analyzer!)
docs_dir = Path("output")
points = []
for md_file in docs_dir.glob("*.md"):
    text = md_file.read_text(encoding="utf-8")
    chunks = chunk_text(text)
    embeddings = model.encode(chunks)
    for chunk, embedding in zip(chunks, embeddings):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding.tolist(),
            payload={"text": chunk, "source": md_file.name},
        ))

client.upsert(collection_name="docs", points=points)
print(f"Indexed {len(points)} chunks from {len(list(docs_dir.glob('*.md')))} documents")
```

### Exercise 2: Query the RAG pipeline

```python
# rag_query.py
def rag_query(question: str, top_k: int = 5) -> str:
    # Embed the question
    query_vector = model.encode(question).tolist()
    
    # Search vector DB
    results = client.search(
        collection_name="docs",
        query_vector=query_vector,
        limit=top_k,
    )
    
    # Build context from retrieved chunks
    context = "\n\n---\n\n".join(
        f"[Source: {r.payload['source']}]\n{r.payload['text']}"
        for r in results
    )
    
    # Build prompt
    prompt = f"""Answer the question based ONLY on the following context. 
If the context doesn't contain the answer, say "I don't have enough information."

Context:
{context}

Question: {question}
Answer:"""
    
    return prompt  # Pass this to your LLM (vLLM, ollama, OpenAI, etc.)

# Example
prompt = rag_query("What is the timeline for the HPE AI Platform project?")
print(prompt)
```

### Exercise 3: Connect to vLLM (from Lab 04)

```python
import httpx

def ask_with_rag(question: str) -> str:
    prompt = rag_query(question)
    
    response = httpx.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "microsoft/Phi-3-mini-4k-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.1,  # low temp for factual answers
        },
    )
    return response.json()["choices"][0]["message"]["content"]

answer = ask_with_rag("What GPUs does the HPE platform use?")
print(answer)
# Should mention: ProLiant DL380a Gen12, A10G, Fort Collins
```

### Exercise 4: Persistent Qdrant with Docker

```bash
# Run Qdrant as a container (persistent storage)
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Now use: QdrantClient("http://localhost:6333")
# Data survives container restart
```

### Exercise 5: Metadata filtering

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Only search in SOW document
results = client.search(
    collection_name="docs",
    query_vector=query_vector,
    query_filter=Filter(
        must=[FieldCondition(key="source", match=MatchValue(value="HPE_Apex SOW_4th August 2026_Final.md"))]
    ),
    limit=5,
)
```

### Exercise 6: Hybrid search (vector + keyword)

```python
# Qdrant supports hybrid search natively
from qdrant_client.models import SparseVector

# Index both dense (semantic) and sparse (keyword) vectors
# Then combine scores at query time for best of both worlds
# Dense: "What's the project scope?" finds semantically similar
# Sparse: "DL380a" finds exact keyword matches
```

### Exercise 7: Deploy RAG on K8s

```yaml
# qdrant-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
  namespace: ml-serving
spec:
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        - containerPort: 6334
        volumeMounts:
        - name: storage
          mountPath: /qdrant/storage
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: qdrant-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: ml-serving
spec:
  selector:
    app: qdrant
  ports:
  - name: http
    port: 6333
  - name: grpc
    port: 6334
```

## References

- [Qdrant documentation](https://qdrant.tech/documentation/)
- [LangChain RAG tutorial](https://python.langchain.com/docs/tutorials/rag/)
- [Sentence Transformers](https://www.sbert.net/)
- [RAGAS — RAG evaluation](https://docs.ragas.io/)
- [Chunking strategies comparison](https://www.pinecone.io/learn/chunking-strategies/)
- *Designing Machine Learning Systems* Ch.10 (Infrastructure and Tooling)
