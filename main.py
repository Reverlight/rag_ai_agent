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
    return {'hello': 'world'}



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

