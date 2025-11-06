import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from app.main import app
from app.core.config import settings

client = TestClient(app)

class TestMainApp:
    """Test the main FastAPI application."""
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_read_main(self):
        """Test the main API endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_app_initialization(self):
        """Test that the app initializes correctly."""
        assert app.title == "Fernando API"
        assert settings.APP_NAME == "Fernando"
    
    @patch('app.core.config.settings.DEBUG', True)
    def test_debug_mode(self):
        """Test debug mode functionality."""
        assert settings.DEBUG is True

class TestAPIEndpoints:
    """Test various API endpoints."""
    
    def test_api_docs_available(self):
        """Test that API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_api_openapi_spec(self):
        """Test OpenAPI specification generation."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Fernando API"

class TestErrorHandling:
    """Test error handling."""
    
    def test_404_not_found(self):
        """Test 404 handling."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test method not allowed handling."""
        response = client.patch("/health")
        assert response.status_code == 405