import os
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import logging

logger = logging.getLogger("uvicorn.access")
logger.disabled = True


def register_middleware(app: FastAPI):

    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)
        processing_time = time.time() - start_time

        # Obsługa None dla request.client
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else "unknown"

        message = f"{client_host}:{client_port} - {request.method} - {request.url.path} - {response.status_code} completed after {processing_time}s"
        print(message)

        # Logowanie do pliku
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_filename = f"log_{datetime.now().strftime('%d-%m-%y')}.txt"
        log_path = os.path.join(log_dir, log_filename)
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")

        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1","0.0.0.0"],
    )