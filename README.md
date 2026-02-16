# RAG PDF Assistant

AI-powered document Q&A system built with FastAPI, React, and Qdrant vector database. Upload PDFs and query their content using natural language.

![Preview](https://raw.githubusercontent.com/Reverlight/rag_ai_agent/feature/frontend/preview.png)

## Features

- 📄 **PDF Upload & Processing**: Automatic text extraction and chunking
- 🔍 **Semantic Search**: Vector-based similarity search using Qdrant
- 🤖 **AI Answers**: OpenAI-powered responses based on document context
- ⚡ **Event-Driven**: Background processing with Inngest
- 🎨 **Modern UI**: Beautiful React interface with real-time feedback

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Setup


1. Create `.env` file
```env
OPENAI_API_KEY=your_openai_api_key_here
```
2. Start all services
```bash
docker-compose up --build
```

3. Access the application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Inngest Dashboard**: http://localhost:8288

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI   │─────▶│   Qdrant    │
│  Frontend   │      │   Backend   │      │  Vector DB  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   Inngest   │
                     │   Events    │
                     └─────────────┘
```

## Usage

1. **Upload PDF**: Click upload area and select a PDF file
2. **Wait for Processing**: System chunks and embeds the document
3. **Ask Questions**: Type your question in the query box
4. **Get AI Answers**: Receive contextual answers with source citations


## Tech Stack

- **Backend**: FastAPI, Python 3.9+
- **Frontend**: React 18, Lucide Icons
- **Vector DB**: Qdrant
- **Embeddings**: OpenAI text-embedding-3
- **LLM**: OpenAI GPT-4o-mini
- **Orchestration**: Inngest
- **Containerization**: Docker & Docker Compose
