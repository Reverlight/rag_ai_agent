import asyncio
import logging
import traceback

from fastapi import FastAPI
import inngest
import inngest.fast_api
from dotenv import load_dotenv
from inngest.experimental import ai
import uuid
import os
import datetime
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc

load_dotenv()

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
        output_type=RAGChunkAndSrc,
    )
    return ingested.module_dump()


app = FastAPI()

@app.get('/error')
def get_notes():
    a = [10, 3, 4]
    return {'error': a[5]}


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


inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])

