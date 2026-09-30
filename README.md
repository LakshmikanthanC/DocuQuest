# 🤖 AI-Powered RAG Document Assistant

An AI-powered **Retrieval-Augmented Generation (RAG)** application that allows users to upload PDF documents and ask questions in natural language.

The system retrieves the most relevant content from the uploaded documents and uses an LLM to generate answers **only from the retrieved context**. Every response includes the **source document, page number, matching snippet, and similarity score** for verification.

---

Username:admin@example.com
Password:admin12345

---


## ✨ Features

* 📄 **PDF Upload** — Upload one or multiple PDF documents.
* 🔍 **Semantic Search** — Retrieve relevant content based on meaning rather than exact keywords.
* 💬 **AI Chat** — Ask questions about uploaded documents using natural language.
* 📚 **Source Citations** — View filename, page number, snippet, and similarity score.
* ⚠️ **Hallucination Protection** — The LLM is instructed to answer only from retrieved document context.
* 🔐 **JWT Authentication** — Secure registration and login with bearer tokens.
* 👤 **Per-User Data Isolation** — Users can only retrieve their own uploaded document chunks.
* 🗂️ **Document Management** — View, search, and delete uploaded documents.
* 💾 **Persistent Vector Storage** — ChromaDB stores document embeddings on disk.
* 🚀 **Background Processing** — PDF indexing runs in the background after upload.
* 🧠 **Local LLM** — Uses Ollama with Llama, allowing the application to run without an external LLM API.
* 🐳 **Docker Support** — Frontend, backend, and Ollama can be started using Docker Compose.
* 🧪 **Automated Testing** — Backend includes comprehensive tests for the RAG pipeline and API.

---

# 🛠️ Tech Stack

## Frontend

| Technology          | Purpose                                 |
| ------------------- | --------------------------------------- |
| **Next.js 16**      | React framework and application routing |
| **React 19**        | User interface                          |
| **TypeScript**      | Type-safe frontend development          |
| **Tailwind CSS v4** | UI styling and responsive design        |

## Backend

| Technology                | Purpose                                |
| ------------------------- | -------------------------------------- |
| **FastAPI**               | REST API and backend services          |
| **Python 3.11+**          | Backend programming language           |
| **LangChain**             | RAG pipeline and LLM integration       |
| **PyMuPDF**               | PDF text extraction                    |
| **Sentence Transformers** | Document and query embeddings          |
| **ChromaDB**              | Vector database and semantic retrieval |
| **Pydantic**              | Request and response validation        |
| **bcrypt**                | Password hashing                       |
| **JWT**                   | Authentication and authorization       |

## AI / Machine Learning

| Technology           | Purpose                                     |
| -------------------- | ------------------------------------------- |
| **Ollama**           | Local LLM runtime                           |
| **Llama 3.1**        | Question-answering LLM                      |
| **all-MiniLM-L6-v2** | Text embedding model                        |
| **RAG**              | Retrieval-Augmented Generation architecture |

## DevOps & Tools

| Technology         | Purpose                                |
| ------------------ | -------------------------------------- |
| **Docker**         | Containerization                       |
| **Docker Compose** | Multi-container application management |
| **Git & GitHub**   | Version control                        |
| **Pytest**         | Backend testing                        |
| **ESLint**         | Frontend code quality                  |

---

# 🏗️ System Architecture

```text
                         AI-Powered RAG System
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
          PDF Upload                              User Question
              │                                       │
              ▼                                       ▼
          PyMuPDF                                Query Embedding
              │                                       │
              ▼                                       ▼
        Text Extraction                           ChromaDB
              │                                       │
              ▼                                  Similarity Search
       Page-wise Chunking                             │
              │                                       ▼
              ▼                                  Top-K Chunks
      Sentence Transformer                            │
              │                                       │
              ▼                                       ▼
          Embeddings ────────────────► Context + Question
                                                      │
                                                      ▼
                                               Llama via Ollama
                                                      │
                                                      ▼
                                           Answer + Citations
                                                      │
                                                      ▼
                                                Web Interface
```

---

# 🔄 How RAG Works

### 1. Upload PDF

The user uploads a PDF through the web interface.

### 2. Extract Text

**PyMuPDF** extracts text from each page while preserving page information.

### 3. Chunk Documents

The extracted text is divided into smaller chunks.

Each chunk maintains metadata such as:

```text
user_id
document_id
filename
page_number
chunk_index
```

### 4. Generate Embeddings

The **all-MiniLM-L6-v2** Sentence Transformer converts each chunk into a numerical vector.

### 5. Store in ChromaDB

The embeddings and their metadata are stored in **ChromaDB**.

### 6. Ask a Question

The user asks a question through the chat interface.

### 7. Semantic Retrieval

The question is converted into an embedding and compared against stored document embeddings.

The system retrieves the most relevant chunks.

### 8. Context Validation

Chunks below the configured relevance threshold are rejected.

If no relevant context exists, the LLM is not called.

### 9. Generate Answer

The retrieved chunks are passed to **Llama through Ollama** with a context-only prompt.

### 10. Return Sources

The application returns:

* Answer
* Document name
* Page number
* Matching snippet
* Similarity score

---

# 🛡️ Hallucination Reduction

The system includes multiple safeguards against unsupported answers.

### Context-only prompting

The LLM receives only the retrieved document chunks and is instructed not to use outside knowledge.

If the retrieved context does not contain the answer, the model is instructed to respond:

> "I could not find an answer to this question in the uploaded documents."

### Relevance threshold

Retrieved chunks are checked against:

```text
MIN_RELEVANCE_SCORE = 0.4
```

If the chunks do not meet the minimum relevance score, the LLM is not called.

### No-context fallback

When retrieval returns no useful context:

```text
LLM
 ↓
Not called
 ↓
"No supporting context was found"
```

This prevents the model from generating an answer without supporting document content.

---

# 🔐 Authentication & Security

The application provides user-level authentication and document isolation.

### Authentication

* User registration
* User login
* JWT access tokens
* Bearer authentication
* bcrypt password hashing

Example:

```http
Authorization: Bearer <token>
```

### Per-user document isolation

Every ChromaDB record contains a `user_id`.

During retrieval, the query is filtered using the authenticated user's ID.

```text
User A
  │
  ├── Document A
  └── Document B

User B
  │
  └── Document C
```

User A cannot retrieve chunks belonging to User B.

---

# 📚 Source Citations

Each retrieved chunk maintains its original page number.

Example response:

```json
{
  "filename": "research-paper.pdf",
  "page": 3,
  "chunk_index": 7,
  "snippet": "Machine learning is a subset of artificial...",
  "score": 0.87
}
```

This makes it possible to verify the generated answer against the original PDF.

---

# 📁 Project Structure

```text
rag-document-assistant/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── globals.css
│   │   │   └── error.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── AuthForm
│   │   │   ├── DocumentManager
│   │   │   ├── ChatPanel
│   │   │   └── SourceCitations
│   │   │
│   │   └── lib/
│   │       ├── api
│   │       └── types
│   │
│   └── Dockerfile
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── chat.py
│   │   │   └── system.py
│   │   │
│   │   ├── core/
│   │   │   ├── settings.py
│   │   │   ├── security.py
│   │   │   └── auth.py
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py
│   │   │
│   │   ├── rag/
│   │   │   ├── pdf_loader.py
│   │   │   ├── chunker.py
│   │   │   ├── embeddings.py
│   │   │   ├── vector_store.py
│   │   │   └── chain.py
│   │   │
│   │   └── services/
│   │       ├── user_service.py
│   │       ├── document_service.py
│   │       ├── chat_service.py
│   │       └── json_store.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── documents/
│   └── uploaded PDFs
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# ⚙️ Configuration

The application can be configured through environment variables.

| Variable                      | Default                   | Description                |
| ----------------------------- | ------------------------- | -------------------------- |
| `SECRET_KEY`                  | `change-me-in-production` | JWT signing key            |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080`                   | JWT expiration time        |
| `CORS_ORIGINS`                | `http://localhost:3000`   | Allowed frontend origins   |
| `OLLAMA_BASE_URL`             | `http://localhost:11434`  | Ollama server              |
| `LLM_MODEL`                   | `llama3.1`                | LLM model                  |
| `LLM_TEMPERATURE`             | `0.1`                     | LLM temperature            |
| `LLM_NUM_CTX`                 | `4096`                    | LLM context window         |
| `EMBEDDING_MODEL`             | `all-MiniLM-L6-v2`        | Embedding model            |
| `CHUNK_SIZE`                  | `1000`                    | Chunk size                 |
| `CHUNK_OVERLAP`               | `150`                     | Chunk overlap              |
| `RETRIEVAL_TOP_K`             | `4`                       | Number of retrieved chunks |
| `MAX_UPLOAD_MB`               | `25`                      | Maximum PDF size           |
| `MIN_RELEVANCE_SCORE`         | `0.4`                     | Minimum retrieval score    |

Frontend:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

> Never use the default `SECRET_KEY` in production.

---

# 🚀 Running Locally

## Prerequisites

Install:

* Python 3.11+
* Node.js 20+
* Ollama
* Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/rag-document-assistant.git

cd rag-document-assistant
```

---

# 🧠 2. Start Ollama

Start Ollama:

```bash
ollama serve
```

In another terminal:

```bash
ollama pull llama3.1
```

---

# 🐍 3. Start Backend

```bash
cd backend
```

Create a virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment file:

### Windows

```bash
copy .env.example .env
```

### macOS / Linux

```bash
cp .env.example .env
```

Start FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

Backend API:

```text
http://localhost:8000
```

Swagger API documentation:

```text
http://localhost:8000/docs
```

The first embedding request downloads:

```text
all-MiniLM-L6-v2
```

from Hugging Face. Subsequent runs use the cached model.

---

# 💻 4. Start Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create environment file:

### Windows

```bash
copy .env.example .env.local
```

### macOS / Linux

```bash
cp .env.example .env.local
```

Start the development server:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

---

# 🐳 Running with Docker

The complete application can also be started using Docker Compose.

```bash
docker compose up --build
```

The Docker setup includes:

```text
Frontend
   │
   ▼
Backend
   │
   ├── ChromaDB
   └── Ollama
        │
        ▼
      Llama
```

The `ollama-pull` service automatically downloads the configured model during the initial startup.

---

# 🔌 API Endpoints

All API routes use the `/api` prefix.

| Method | Endpoint                | Description                      |
| ------ | ----------------------- | -------------------------------- |
| GET    | `/api/health`           | Check application and LLM health |
| POST   | `/api/auth/register`    | Create a new account             |
| POST   | `/api/auth/login`       | Authenticate user                |
| GET    | `/api/auth/me`          | Get current user                 |
| GET    | `/api/documents`        | List user's documents            |
| POST   | `/api/documents`        | Upload a PDF                     |
| GET    | `/api/documents/{id}`   | Get document information         |
| DELETE | `/api/documents/{id}`   | Delete document                  |
| POST   | `/api/chat`             | Ask a question                   |
| GET    | `/api/chat/history`     | Get chat history                 |
| DELETE | `/api/chat/history`     | Clear current conversation       |
| DELETE | `/api/chat/history/all` | Clear history and documents      |

---

# 💬 Example Chat Request

```json
{
  "question": "What is machine learning?",
  "top_k": 4,
  "document_ids": ["a1b2c3"]
}
```

Example response:

```json
{
  "answer": "Machine learning is a subset of artificial intelligence...",
  "sources": [
    {
      "document_id": "a1b2c3",
      "filename": "research-paper.pdf",
      "page": 3,
      "chunk_index": 7,
      "snippet": "Machine learning is a subset of artificial...",
      "score": 0.87
    }
  ],
  "has_context": true,
  "model": "llama3.1"
}
```

---

# 🔧 Retrieval Configuration

The RAG pipeline can be tuned using environment variables.

### Increase retrieved context

```env
RETRIEVAL_TOP_K=6
```

Useful when answers require information from multiple sections.

### Smaller chunks

```env
CHUNK_SIZE=700
CHUNK_OVERLAP=100
```

Useful when answers are becoming mixed across different topics.

### Larger chunks

```env
CHUNK_SIZE=1500
LLM_NUM_CTX=8192
```

Useful for long passages where additional surrounding context is required.

---

# 🧪 Testing

## Backend

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

The backend test suite covers:

* PDF extraction
* Text cleaning
* Page-aware chunking
* Prompt construction
* Refusal detection
* ChromaDB storage
* User filtering
* User isolation
* JSON persistence
* Corruption recovery
* CORS configuration
* Retrieval relevance threshold
* Chart and diagram extraction
* API contract

The LLM and embedding model can be replaced with deterministic test doubles, allowing the tests to run offline.

---

## Frontend

Type checking:

```bash
npx tsc --noEmit
```

Linting:

```bash
npm run lint
```

Production build:

```bash
npm run build
```

---

# 📊 RAG Pipeline

```text
PDF
 │
 ▼
PyMuPDF
 │
 ▼
Page-wise Text Extraction
 │
 ▼
Chunking
 │
 ▼
Sentence Transformers
 │
 ▼
Embeddings
 │
 ▼
ChromaDB
 │
 ├───────────────┐
 │               │
 ▼               ▼
User Question → Query Embedding
                     │
                     ▼
              Similarity Search
                     │
                     ▼
                Top-K Chunks
                     │
                     ▼
              Relevance Check
                     │
              ┌──────┴──────┐
              │             │
           Relevant      Not Relevant
              │             │
              ▼             ▼
        Llama / Ollama    No LLM Call
              │
              ▼
       Answer + Sources
```

---

# 🔒 Production Considerations

For a public deployment, the following changes are recommended:

* Replace the default JWT `SECRET_KEY`.
* Use an `httpOnly` secure cookie instead of `localStorage` for JWT storage.
* Configure production `CORS_ORIGINS`.
* Replace JSON user/document storage with PostgreSQL.
* Use object storage such as AWS S3 for uploaded PDFs.
* Add rate limiting.
* Add HTTPS.
* Use multiple backend workers only after replacing the in-process JSON stores.
* Configure persistent volumes for ChromaDB and Ollama.
* Add monitoring and application logging.

---

# ⚠️ Troubleshooting

| Problem                | Solution                                           |
| ---------------------- | -------------------------------------------------- |
| Cannot reach backend   | Start FastAPI or update `NEXT_PUBLIC_API_URL`      |
| Ollama offline         | Run `ollama serve`                                 |
| Model not found        | Run `ollama pull llama3.1`                         |
| First upload is slow   | The embedding model is being downloaded            |
| No supporting context  | Ask a question related to the uploaded document    |
| Credentials invalid    | Log in again to obtain a new token                 |
| Chroma dimension error | Delete `backend/chroma_db/` and re-index documents |
| Browser CORS error     | Configure `CORS_ORIGINS` correctly                 |

---

# 📈 Future Improvements

* 🔹 PostgreSQL database
* 🔹 AWS S3 document storage
* 🔹 Redis caching
* 🔹 Streaming LLM responses
* 🔹 OCR support for scanned PDFs
* 🔹 Multi-document conversations
* 🔹 Conversation memory
* 🔹 Hybrid keyword + semantic search
* 🔹 Reranking models
* 🔹 PDF page preview
* 🔹 Role-based access control
* 🔹 Document sharing
* 🔹 Cloud deployment
* 🔹 Advanced evaluation metrics for RAG accuracy

---

# 📄 License

This project is licensed under the **MIT License**.

---



⭐ If you find this project useful, consider giving the repository a star!
