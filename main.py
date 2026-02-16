import asyncio
import logging
import shutil
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel

import inngest
import inngest.fast_api
from dotenv import load_dotenv
from inngest.experimental import ai
import uuid
import os
import datetime

from starlette.middleware.cors import CORSMiddleware

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

inngest_client = inngest.Inngest(
    app_id='rag_app',
    logger=logging.getLogger('uvicorn'),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id='RAG: Ingest PDF',
    trigger=inngest.TriggerEvent(event='rag/ingest_pdf')
)
async def rag_ingest_pdf(ctx: inngest.Context):
    def _load(ctx):
        pdf_path = ctx.event.data['pdf_path']
        source_id = ctx.event.data.get('source_id', pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src):
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL,
                              f"{source_id}: {i}")) for i in range(len(chunks))]
        payloads = [{'source': source_id, 'text': chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunks_and_src = await ctx.step.run(
        "load-and-chunk",
        lambda: _load(ctx),
        output_type=RAGChunkAndSrc,
    )

    ingested = await ctx.step.run(
        "embed-and-upsert",
        lambda: _upsert(chunks_and_src),
        output_type=RAGUpsertResult,  # ✅ CORRECT
    )
    return ingested.model_dump()


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


@app.get('/')
def read_root():
    return {'message': 'RAG API is running'}


@app.post('/upload')
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF and trigger ingestion"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Save file
    file_path = UPLOAD_DIR / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Trigger Inngest function
    try:
        event_id = await inngest_client.send(
            inngest.Event(
                name="rag/ingest_pdf",
                data={
                    "pdf_path": str(file_path),
                    "source_id": file.filename
                }
            )
        )

        # Wait a bit and try to get the result (simplified approach)
        await asyncio.sleep(2)

        # For a proper implementation, you'd poll the Inngest API for the result
        # Here we'll return a success message
        return {
            "message": "PDF uploaded and processing started",
            "filename": file.filename,
            "event_id": str(event_id),
            "chunks_ingested": "Processing..."  # In production, poll for actual result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@app.post('/query')
async def query_pdf(request: QueryRequest):
    """Query the RAG system"""
    try:
        # Trigger Inngest function
        event_id = await inngest_client.send(
            inngest.Event(
                name="rag/query_pdf_ai",
                data={
                    "question": request.question,
                    "top_k": request.top_k
                }
            )
        )

        # In production, you'd poll for the result
        # For now, we'll do a synchronous search
        query_vec = embed_texts([request.question])[0]
        store = QdrantStorage()
        found = store.search(query_vec, request.top_k)

        if not found['contexts']:
            return {
                "answer": "No relevant information found. Please upload PDFs first.",
                "sources": [],
                "num_contexts": 0
            }

        # Quick answer using OpenAI directly (bypassing Inngest for immediate response)
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        content_block = '\n\n'.join(f' - {c}' for c in found['contexts'])
        user_content = (
            'Use the following context to answer the question. \n\n'
            f'Context:\n{content_block}\n\n'
            f'Question: {request.question}\n'
            'Answer concisely using the context above.'
        )

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=1024,
            temperature=0.2,
            messages=[
                {'role': 'system', 'content': 'You answer questions using only the provided context'},
                {'role': 'user', 'content': user_content}
            ]
        )

        answer = response.choices[0].message.content.strip()

        return {
            "answer": answer,
            "sources": found['sources'],
            "num_contexts": len(found['contexts']),
            "event_id": str(event_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")



@app.get('/error')
def get_notes():
    a = [10, 3, 4]
    return {'error': a[5]}

@inngest_client.create_function(
    fn_id="RAG: Query",
    trigger=inngest.TriggerEvent(event='rag/query_pdf_ai')
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    def _search(question: str, top_k: int = 5):
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        found = store.search(query_vec, top_k)
        return RAGSearchResult(contexts=found['contexts'], sources=found['sources'])

    question = ctx.event.data['question']
    top_k = int(ctx.event.data.get('top_k', 5))
    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    content_block = '\n\n'.join(f' - {c}' for c in found.contexts)  # ✅ FIX 1: 'n/n' → '\n\n'
    user_content = (
        'Use the following context to answer the question. \n\n'
        f'Context:\n{content_block}\n\n'
        f'Question: {question}\n'  # ✅ FIX 2: Added colon after 'Question'
        'Answer concisely using the context above.'
    )
    adapter = ai.openai.Adapter(
        auth_key=os.getenv('OPENAI_API_KEY'),
        model='gpt-4o-mini'
    )
    res = await ctx.step.ai.infer(
        'llm-answer',
        adapter=adapter,
        body={
            'max_tokens': 1024,  # ✅ FIX 3: 'max_token' → 'max_tokens'
            'temperature': 0.2,
            'messages': [
                {'role': 'system', 'content': 'You answer questions using only the provided context'},
                {'role': 'user', 'content': user_content}
            ]
        }
    )

    answer = res['choices'][0]['message']['content'].strip()
    return {'answer': answer, 'sources': found.sources, 'num_contexts': len(found.contexts)}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    event = inngest.Event(
        name="fastapi_exception",
        data={
            "path": str(request.url),
            "method": request.method,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "stack_trace": tb_str,  # <-- full traceback
        }
    )
    inngest_client.send_sync(event)


inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])

