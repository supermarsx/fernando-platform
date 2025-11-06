"""
Mock OCR Service

Simulates OCR processing of documents. In production, this would integrate
with Tesseract, PaddleOCR, or other OCR engines.
"""
import time
import random
from typing import Dict, List
from pathlib import Path


class MockOCRService:
    """Mock OCR service that simulates text extraction from documents"""
    
    def __init__(self):
        self.engine_name = "MockOCR"
        self.version = "1.0.0"
    
    def process_document(self, file_path: str) -> Dict:
        """
        Simulate OCR processing of a document
        
        Returns:
            Dictionary containing extracted text and confidence scores
        """
        time.sleep(random.uniform(0.5, 1.5))  # Simulate processing time
        
        # Mock extracted text from a Portuguese invoice
        mock_text = """
        FACTURA
        
        Fornecedor: TECNOLOGIA AVANCADA LDA
        NIF: 123456789
        Morada: Rua das Flores, 123, 1200-195 Lisboa
        
        Cliente: EMPRESA EXEMPLO SA
        NIF: 987654321
        
        Data: 15/10/2025
        Factura N: 2025/1234
        
        Descricao                    Quantidade    Preco Unit.    Total
        Servicos de Consultoria         10 horas      50.00 EUR    500.00 EUR
        Desenvolvimento Software         5 horas      75.00 EUR    375.00 EUR
        
        Subtotal:                                                   875.00 EUR
        IVA (23%):                                                  201.25 EUR
        Total:                                                    1,076.25 EUR
        
        Metodo de Pagamento: Transferencia Bancaria
        IBAN: PT50 0000 0000 0000 0000 0000 0
        """
        
        return {
            "text": mock_text,
            "confidence": random.uniform(0.85, 0.98),
            "engine": self.engine_name,
            "version": self.version,
            "pages_processed": 1,
            "processing_time_seconds": random.uniform(0.5, 1.5)
        }
    
    def extract_zones(self, file_path: str) -> List[Dict]:
        """
        Simulate zone detection in document
        
        Returns:
            List of detected zones with bounding boxes
        """
        return [
            {"type": "header", "confidence": 0.95, "bbox": [0, 0, 100, 15]},
            {"type": "supplier_info", "confidence": 0.92, "bbox": [0, 15, 50, 40]},
            {"type": "client_info", "confidence": 0.90, "bbox": [50, 15, 100, 40]},
            {"type": "items_table", "confidence": 0.94, "bbox": [0, 40, 100, 75]},
            {"type": "totals", "confidence": 0.96, "bbox": [0, 75, 100, 90]},
        ]
