"""CORS policy for the same-origin local Windows beta UI."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors(app: FastAPI):
    """Allow only the two loopback host spellings served on the backend port."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:9000", "http://localhost:9000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Authorization", "X-CSRF-Token"],
        max_age=300,
    )
    print("[cors-explicit] CORS middleware installed with localhost origins")
    return app
