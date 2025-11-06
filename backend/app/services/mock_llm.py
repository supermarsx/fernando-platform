"""
Mock LLM Service

Simulates LLM-based extraction of structured fields from OCR text.
In production, this would integrate with OpenAI, local Phi-4, or other LLMs.
"""
import time
import random
import re
from typing import Dict, List
from datetime import datetime


class MockLLMService:
    """Mock LLM service that simulates field extraction from text"""
    
    def __init__(self):
        self.model_name = "MockLLM"
        self.version = "1.0.0"
    
    def extract_fields(self, text: str, document_type: str = "invoice") -> Dict:
        """
        Simulate LLM extraction of structured fields from OCR text
        
        Args:
            text: OCR extracted text
            document_type: Type of document (invoice, receipt, etc.)
        
        Returns:
            Dictionary containing extracted fields with confidence scores
        """
        time.sleep(random.uniform(1.0, 2.0))  # Simulate API call time
        
        # Simple pattern matching to simulate intelligent extraction
        fields = {}
        
        # Extract supplier name
        supplier_match = re.search(r'Fornecedor:\s*(.+)', text)
        if supplier_match:
            fields["supplier_name"] = {
                "value": supplier_match.group(1).strip(),
                "confidence": random.uniform(0.85, 0.98)
            }
        else:
            fields["supplier_name"] = {
                "value": "TECNOLOGIA AVANCADA LDA",
                "confidence": 0.75
            }
        
        # Extract NIF (tax ID)
        nif_match = re.search(r'NIF:\s*(\d+)', text)
        if nif_match:
            fields["supplier_nif"] = {
                "value": nif_match.group(1),
                "confidence": random.uniform(0.90, 0.99)
            }
        else:
            fields["supplier_nif"] = {
                "value": "123456789",
                "confidence": 0.70
            }
        
        # Extract invoice date
        date_match = re.search(r'Data:\s*(\d{2}/\d{2}/\d{4})', text)
        if date_match:
            fields["invoice_date"] = {
                "value": date_match.group(1),
                "confidence": random.uniform(0.88, 0.97)
            }
        else:
            fields["invoice_date"] = {
                "value": datetime.now().strftime("%d/%m/%Y"),
                "confidence": 0.65
            }
        
        # Extract invoice number
        invoice_match = re.search(r'Factura N[:\s]+(.+)', text)
        if invoice_match:
            fields["invoice_number"] = {
                "value": invoice_match.group(1).strip(),
                "confidence": random.uniform(0.85, 0.95)
            }
        else:
            fields["invoice_number"] = {
                "value": "2025/1234",
                "confidence": 0.70
            }
        
        # Extract amounts
        subtotal_match = re.search(r'Subtotal:\s*(\d+[.,]\d+)\s*EUR', text)
        if subtotal_match:
            fields["subtotal"] = {
                "value": subtotal_match.group(1).replace(',', '.'),
                "confidence": random.uniform(0.90, 0.98)
            }
        else:
            fields["subtotal"] = {
                "value": "875.00",
                "confidence": 0.75
            }
        
        # Extract VAT
        vat_match = re.search(r'IVA[^:]*:\s*(\d+[.,]\d+)\s*EUR', text)
        if vat_match:
            fields["vat_amount"] = {
                "value": vat_match.group(1).replace(',', '.'),
                "confidence": random.uniform(0.90, 0.98)
            }
        else:
            fields["vat_amount"] = {
                "value": "201.25",
                "confidence": 0.75
            }
        
        # Extract total
        total_match = re.search(r'Total:\s*(\d+[.,]\d+)\s*EUR', text)
        if total_match:
            fields["total_amount"] = {
                "value": total_match.group(1).replace(',', '.'),
                "confidence": random.uniform(0.92, 0.99)
            }
        else:
            fields["total_amount"] = {
                "value": "1076.25",
                "confidence": 0.75
            }
        
        # Extract VAT rate
        vat_rate_match = re.search(r'IVA\s*\((\d+)%\)', text)
        if vat_rate_match:
            fields["vat_rate"] = {
                "value": vat_rate_match.group(1),
                "confidence": random.uniform(0.88, 0.96)
            }
        else:
            fields["vat_rate"] = {
                "value": "23",
                "confidence": 0.80
            }
        
        # Currency
        fields["currency"] = {
            "value": "EUR",
            "confidence": 0.99
        }
        
        return {
            "fields": fields,
            "model": self.model_name,
            "version": self.version,
            "processing_time_seconds": random.uniform(1.0, 2.0)
        }
    
    def validate_extraction(self, fields: Dict) -> Dict[str, bool]:
        """
        Simulate validation of extracted fields
        
        Returns:
            Dictionary mapping field names to validation results
        """
        validations = {}
        
        for field_name, field_data in fields.items():
            # Simple validation rules
            if field_name == "supplier_nif":
                # Check if NIF is 9 digits
                validations[field_name] = len(field_data["value"]) == 9 and field_data["value"].isdigit()
            elif field_name == "invoice_date":
                # Check if date format is valid
                try:
                    datetime.strptime(field_data["value"], "%d/%m/%Y")
                    validations[field_name] = True
                except:
                    validations[field_name] = False
            elif field_name in ["subtotal", "vat_amount", "total_amount"]:
                # Check if numeric
                try:
                    float(field_data["value"])
                    validations[field_name] = True
                except:
                    validations[field_name] = False
            else:
                # Default: valid if confidence > 0.7
                validations[field_name] = field_data["confidence"] > 0.7
        
        return validations
