"""
Mock TOCOnline Service

Simulates integration with TOCOnline API for posting accounting records.
In production, this would implement OAuth2 flow and actual API calls.
"""
import time
import random
import uuid
from typing import Dict, Optional


class MockTOCOnlineService:
    """Mock TOCOnline service that simulates API integration"""
    
    def __init__(self):
        self.client_id = "mock_client_id"
        self.client_secret = "mock_client_secret"
        self.access_token = None
        self.token_expires_at = None
    
    def authenticate(self) -> Dict:
        """
        Simulate OAuth2 authentication with TOCOnline
        
        Returns:
            Dictionary containing access token and expiry
        """
        time.sleep(random.uniform(0.3, 0.7))
        
        self.access_token = f"mock_token_{uuid.uuid4().hex}"
        self.token_expires_at = time.time() + 3600  # 1 hour
        
        return {
            "access_token": self.access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "sales.write purchases.write"
        }
    
    def map_fields_to_toconline(self, fields: Dict) -> Dict:
        """
        Map extracted fields to TOCOnline API schema
        
        Args:
            fields: Dictionary of extracted fields
        
        Returns:
            Dictionary formatted for TOCOnline API
        """
        # Convert internal field names to TOCOnline schema
        mapped = {
            "supplier": fields.get("supplier_name", {}).get("value", ""),
            "supplierTaxId": fields.get("supplier_nif", {}).get("value", ""),
            "documentNumber": fields.get("invoice_number", {}).get("value", ""),
            "documentDate": self._convert_date_format(
                fields.get("invoice_date", {}).get("value", "")
            ),
            "currency": fields.get("currency", {}).get("value", "EUR"),
            "netAmount": float(fields.get("subtotal", {}).get("value", "0").replace(',', '.')),
            "vatAmount": float(fields.get("vat_amount", {}).get("value", "0").replace(',', '.')),
            "grossAmount": float(fields.get("total_amount", {}).get("value", "0").replace(',', '.')),
            "vatRate": float(fields.get("vat_rate", {}).get("value", "23")),
            "documentType": "INVOICE",
            "status": "DRAFT"
        }
        
        return mapped
    
    def _convert_date_format(self, date_str: str) -> str:
        """Convert DD/MM/YYYY to YYYY-MM-DD"""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            pass
        return date_str
    
    def post_document(self, data: Dict) -> Dict:
        """
        Simulate posting a document to TOCOnline
        
        Args:
            data: Document data formatted for TOCOnline
        
        Returns:
            Response from TOCOnline API (mocked)
        """
        time.sleep(random.uniform(0.5, 1.5))
        
        # Simulate success/failure
        success_rate = 0.95
        
        if random.random() < success_rate:
            return {
                "status": "success",
                "recordId": f"TOC{uuid.uuid4().hex[:12].upper()}",
                "documentNumber": data.get("documentNumber", ""),
                "message": "Document posted successfully",
                "validationStatus": "APPROVED",
                "atReference": f"AT{random.randint(100000000, 999999999)}"  # Portuguese tax authority reference
            }
        else:
            # Simulate various error scenarios
            errors = [
                {"code": "VALIDATION_ERROR", "message": "Invalid VAT calculation"},
                {"code": "DUPLICATE_DOCUMENT", "message": "Document number already exists"},
                {"code": "INVALID_TAX_ID", "message": "Supplier tax ID not found"},
                {"code": "MISSING_FIELD", "message": "Required field missing: documentDate"}
            ]
            error = random.choice(errors)
            
            return {
                "status": "error",
                "errorCode": error["code"],
                "message": error["message"],
                "recordId": None
            }
    
    def get_document_status(self, record_id: str) -> Dict:
        """
        Simulate checking document status in TOCOnline
        
        Args:
            record_id: TOCOnline record ID
        
        Returns:
            Document status information
        """
        time.sleep(random.uniform(0.2, 0.5))
        
        statuses = ["DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "FINALIZED"]
        
        return {
            "recordId": record_id,
            "status": random.choice(statuses),
            "lastUpdated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "validationMessages": []
        }
    
    def validate_document(self, data: Dict) -> Dict:
        """
        Simulate document validation before posting
        
        Args:
            data: Document data to validate
        
        Returns:
            Validation results
        """
        validations = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = ["supplier", "supplierTaxId", "documentNumber", 
                          "documentDate", "netAmount", "vatAmount", "grossAmount"]
        
        for field in required_fields:
            if field not in data or not data[field]:
                validations["valid"] = False
                validations["errors"].append(f"Missing required field: {field}")
        
        # Validate VAT calculation
        if "netAmount" in data and "vatAmount" in data and "grossAmount" in data:
            expected_gross = data["netAmount"] + data["vatAmount"]
            if abs(expected_gross - data["grossAmount"]) > 0.01:
                validations["valid"] = False
                validations["errors"].append(
                    f"VAT calculation error: {data['netAmount']} + {data['vatAmount']} != {data['grossAmount']}"
                )
        
        # Add some realistic warnings
        if random.random() < 0.3:
            validations["warnings"].append("Document date is more than 30 days old")
        
        return validations
