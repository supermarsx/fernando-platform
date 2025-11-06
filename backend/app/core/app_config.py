"""
Application configuration and initialization
"""
from fastapi import FastAPI
from app.core.config import settings

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Fernando Platform - Enterprise Edition",
        version="2.0.0-enterprise",
        description="Enterprise-grade automated Portuguese invoice processing with OCR, LLM extraction, and TOCOnline integration",
        debug=settings.DEBUG
    )
    return app