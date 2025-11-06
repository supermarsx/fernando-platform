"""Pytest configuration and shared fixtures."""
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from unittest.mock import Mock
import asyncio

from app.main import app
from app.core.config import settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('app.core.config.settings') as mock:
        mock.DEBUG = True
        mock.DATABASE_URL = "sqlite:///./test.db"
        mock.SECRET_KEY = "test-secret-key"
        mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        yield mock

@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "id": 1,
        "filename": "test_document.pdf",
        "file_type": "pdf",
        "status": "pending",
        "created_at": "2023-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_extraction_data():
    """Sample extraction data for testing."""
    return {
        "document_id": 1,
        "extracted_text": "Sample extracted text",
        "confidence": 0.95,
        "fields": {
            "amount": "100.00",
            "date": "2023-01-01",
            "vendor": "Test Vendor"
        }
    }

@pytest.fixture
def mock_file_upload():
    """Mock file upload data."""
    return {
        "filename": "test.pdf",
        "content": b"fake pdf content",
        "content_type": "application/pdf"
    }

@pytest.fixture
def mock_processing_service():
    """Mock document processing service."""
    with patch('app.services.document_processor.DocumentProcessor') as mock:
        processor = Mock()
        processor.process_document.return_value = {
            "status": "completed",
            "extracted_data": {"amount": "100.00"}
        }
        mock.return_value = processor
        yield mock

@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    with patch('app.services.mock_llm.MockLLMService') as mock:
        service = Mock()
        service.extract_fields.return_value = {
            "amount": "100.00",
            "date": "2023-01-01",
            "vendor": "Test Vendor"
        }
        mock.return_value = service
        yield mock

@pytest.fixture
def mock_ocr_service():
    """Mock OCR service."""
    with patch('app.services.mock_ocr.MockOCRService') as mock:
        service = Mock()
        service.extract_text.return_value = "Extracted text from document"
        mock.return_value = service
        yield mock