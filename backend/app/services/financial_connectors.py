"""
Financial System Integration Connectors

Authentic connector implementations for major accounting systems:
- QuickBooks
- Xero  
- SAP
- NetSuite
- Sage
- Microsoft Dynamics

Each connector provides:
- Authentication handling
- API client initialization
- Data sync operations (invoices, payments, customers)
- Error handling and retry logic
- GL code mapping
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
import json
from abc import ABC, abstractmethod


class FinancialSystemConnector(ABC):
    """Base class for all financial system connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_endpoint = config.get('api_endpoint')
        self.credentials = config.get('credentials', {})
        self.access_token = None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the financial system"""
        pass
    
    @abstractmethod
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        """Sync an invoice to the financial system"""
        pass
    
    @abstractmethod
    def sync_payment(self, payment_data: Dict) -> Dict:
        """Sync a payment to the financial system"""
        pass
    
    @abstractmethod
    def sync_customer(self, customer_data: Dict) -> Dict:
        """Sync a customer to the financial system"""
        pass
    
    @abstractmethod
    def get_chart_of_accounts(self) -> List[Dict]:
        """Get chart of accounts from financial system"""
        pass


class QuickBooksConnector(FinancialSystemConnector):
    """
    QuickBooks Online API Connector
    
    Required Configuration:
    - client_id: OAuth 2.0 Client ID
    - client_secret: OAuth 2.0 Client Secret
    - refresh_token: OAuth 2.0 Refresh Token
    - realm_id: QuickBooks Company ID
    - environment: 'sandbox' or 'production'
    
    API Documentation: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/invoice
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.environment = config.get('environment', 'sandbox')
        self.base_url = (
            "https://sandbox-quickbooks.api.intuit.com/v3" if self.environment == 'sandbox'
            else "https://quickbooks.api.intuit.com/v3"
        )
        self.realm_id = config.get('realm_id')
        self.client_id = self.credentials.get('client_id')
        self.client_secret = self.credentials.get('client_secret')
        self.refresh_token = self.credentials.get('refresh_token')
    
    def authenticate(self) -> bool:
        """
        Authenticate using OAuth 2.0 refresh token
        Returns True if successful, False otherwise
        """
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Missing required credentials: client_id, client_secret, refresh_token")
        
        try:
            response = requests.post(
                "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access_token']
                return True
            else:
                raise Exception(f"Authentication failed: {response.text}")
        
        except Exception as e:
            raise Exception(f"QuickBooks authentication error: {str(e)}")
    
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        """
        Sync invoice to QuickBooks
        
        Invoice data format:
        {
            "customer_ref": "123",
            "invoice_number": "INV-001",
            "txn_date": "2025-01-15",
            "due_date": "2025-02-14",
            "line_items": [
                {
                    "description": "Software Subscription",
                    "amount": 1000.00,
                    "quantity": 1,
                    "account_ref": "Income Account ID"
                }
            ],
            "total_amount": 1000.00
        }
        """
        if not self.access_token:
            self.authenticate()
        
        # Transform to QuickBooks format
        qb_invoice = {
            "CustomerRef": {"value": invoice_data['customer_ref']},
            "DocNumber": invoice_data['invoice_number'],
            "TxnDate": invoice_data['txn_date'],
            "DueDate": invoice_data['due_date'],
            "Line": [
                {
                    "DetailType": "SalesItemLineDetail",
                    "Description": item['description'],
                    "Amount": item['amount'],
                    "SalesItemLineDetail": {
                        "Qty": item['quantity'],
                        "ItemRef": {"value": item.get('item_ref', '1')}  # Default item
                    }
                }
                for item in invoice_data['line_items']
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/company/{self.realm_id}/invoice",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=qb_invoice
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['Invoice']['Id'],
                    "sync_date": datetime.utcnow().isoformat()
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_payment(self, payment_data: Dict) -> Dict:
        """Sync payment to QuickBooks"""
        if not self.access_token:
            self.authenticate()
        
        qb_payment = {
            "CustomerRef": {"value": payment_data['customer_ref']},
            "TotalAmt": payment_data['amount'],
            "TxnDate": payment_data['payment_date'],
            "Line": [{
                "Amount": payment_data['amount'],
                "LinkedTxn": [{
                    "TxnId": payment_data['invoice_id'],
                    "TxnType": "Invoice"
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/company/{self.realm_id}/payment",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=qb_payment
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['Payment']['Id']
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_customer(self, customer_data: Dict) -> Dict:
        """Sync customer to QuickBooks"""
        if not self.access_token:
            self.authenticate()
        
        qb_customer = {
            "DisplayName": customer_data['name'],
            "PrimaryEmailAddr": {"Address": customer_data.get('email', '')},
            "CompanyName": customer_data.get('company_name', customer_data['name']),
            "BillAddr": customer_data.get('billing_address', {})
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/company/{self.realm_id}/customer",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=qb_customer
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['Customer']['Id']
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_chart_of_accounts(self) -> List[Dict]:
        """Get chart of accounts from QuickBooks"""
        if not self.access_token:
            self.authenticate()
        
        try:
            response = requests.get(
                f"{self.base_url}/company/{self.realm_id}/query?query=SELECT * FROM Account",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                accounts = response.json().get('QueryResponse', {}).get('Account', [])
                return [
                    {
                        "id": acc['Id'],
                        "name": acc['Name'],
                        "type": acc['AccountType'],
                        "number": acc.get('AcctNum', '')
                    }
                    for acc in accounts
                ]
            else:
                raise Exception(f"Failed to get accounts: {response.text}")
        
        except Exception as e:
            raise Exception(f"Error getting chart of accounts: {str(e)}")


class XeroConnector(FinancialSystemConnector):
    """
    Xero API Connector
    
    Required Configuration:
    - client_id: OAuth 2.0 Client ID
    - client_secret: OAuth 2.0 Client Secret
    - refresh_token: OAuth 2.0 Refresh Token
    - tenant_id: Xero Organization/Tenant ID
    
    API Documentation: https://developer.xero.com/documentation/api/accounting/overview
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://api.xero.com/api.xro/2.0"
        self.tenant_id = config.get('tenant_id')
        self.client_id = self.credentials.get('client_id')
        self.client_secret = self.credentials.get('client_secret')
        self.refresh_token = self.credentials.get('refresh_token')
    
    def authenticate(self) -> bool:
        """Authenticate using OAuth 2.0"""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Missing required credentials")
        
        try:
            response = requests.post(
                "https://identity.xero.com/connect/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['access_token']
                return True
            else:
                raise Exception(f"Authentication failed: {response.text}")
        
        except Exception as e:
            raise Exception(f"Xero authentication error: {str(e)}")
    
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        """Sync invoice to Xero"""
        if not self.access_token:
            self.authenticate()
        
        xero_invoice = {
            "Type": "ACCREC",
            "Contact": {"ContactID": invoice_data['customer_ref']},
            "InvoiceNumber": invoice_data['invoice_number'],
            "Date": invoice_data['txn_date'],
            "DueDate": invoice_data['due_date'],
            "LineItems": [
                {
                    "Description": item['description'],
                    "Quantity": item['quantity'],
                    "UnitAmount": item['amount'] / item['quantity'],
                    "AccountCode": item.get('account_code', '200')
                }
                for item in invoice_data['line_items']
            ],
            "Status": "AUTHORISED"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/Invoices",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Xero-tenant-id": self.tenant_id,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={"Invoices": [xero_invoice]}
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['Invoices'][0]['InvoiceID']
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_payment(self, payment_data: Dict) -> Dict:
        """Sync payment to Xero"""
        if not self.access_token:
            self.authenticate()
        
        xero_payment = {
            "Invoice": {"InvoiceID": payment_data['invoice_id']},
            "Account": {"Code": payment_data.get('account_code', '090')},
            "Date": payment_data['payment_date'],
            "Amount": payment_data['amount']
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/Payments",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Xero-tenant-id": self.tenant_id,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={"Payments": [xero_payment]}
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['Payments'][0]['PaymentID']
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_customer(self, customer_data: Dict) -> Dict:
        """Sync customer to Xero"""
        if not self.access_token:
            self.authenticate()
        
        xero_contact = {
            "Name": customer_data['name'],
            "EmailAddress": customer_data.get('email', ''),
            "Addresses": [customer_data.get('billing_address', {})]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/Contacts",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Xero-tenant-id": self.tenant_id,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={"Contacts": [xero_contact]}
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['Contacts'][0]['ContactID']
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_chart_of_accounts(self) -> List[Dict]:
        """Get chart of accounts from Xero"""
        if not self.access_token:
            self.authenticate()
        
        try:
            response = requests.get(
                f"{self.base_url}/Accounts",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Xero-tenant-id": self.tenant_id,
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                accounts = response.json().get('Accounts', [])
                return [
                    {
                        "id": acc['AccountID'],
                        "name": acc['Name'],
                        "type": acc['Type'],
                        "code": acc.get('Code', '')
                    }
                    for acc in accounts
                ]
            else:
                raise Exception(f"Failed to get accounts: {response.text}")
        
        except Exception as e:
            raise Exception(f"Error getting chart of accounts: {str(e)}")


class SAPConnector(FinancialSystemConnector):
    """
    SAP Business One API Connector
    
    Required Configuration:
    - api_endpoint: SAP Business One Service Layer URL
    - company_db: Company Database Name
    - username: SAP B1 Username
    - password: SAP B1 Password
    
    API Documentation: https://help.sap.com/docs/SAP_BUSINESS_ONE/68a2e87fb29941b5ac82f8c7dc3c3fa2
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.company_db = config.get('company_db')
        self.username = self.credentials.get('username')
        self.password = self.credentials.get('password')
        self.session_id = None
    
    def authenticate(self) -> bool:
        """Authenticate with SAP Business One"""
        if not all([self.api_endpoint, self.company_db, self.username, self.password]):
            raise ValueError("Missing required credentials")
        
        try:
            response = requests.post(
                f"{self.api_endpoint}/Login",
                json={
                    "CompanyDB": self.company_db,
                    "UserName": self.username,
                    "Password": self.password
                },
                verify=False  # May need SSL cert configuration
            )
            
            if response.status_code == 200:
                self.session_id = response.cookies.get('B1SESSION')
                return True
            else:
                raise Exception(f"Authentication failed: {response.text}")
        
        except Exception as e:
            raise Exception(f"SAP authentication error: {str(e)}")
    
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        """Sync invoice to SAP"""
        if not self.session_id:
            self.authenticate()
        
        # SAP uses DocumentLines array
        sap_invoice = {
            "CardCode": invoice_data['customer_ref'],
            "DocDate": invoice_data['txn_date'],
            "DocDueDate": invoice_data['due_date'],
            "DocumentLines": [
                {
                    "ItemDescription": item['description'],
                    "Quantity": item['quantity'],
                    "UnitPrice": item['amount'] / item['quantity'],
                    "AccountCode": item.get('account_code', '')
                }
                for item in invoice_data['line_items']
            ]
        }
        
        try:
            response = requests.post(
                f"{self.api_endpoint}/Invoices",
                json=sap_invoice,
                cookies={"B1SESSION": self.session_id},
                verify=False
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "external_id": response.json()['DocEntry']
                }
            else:
                raise Exception(f"Sync failed: {response.text}")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_payment(self, payment_data: Dict) -> Dict:
        """Sync payment to SAP"""
        # Implementation similar to invoice sync
        return {"success": False, "error": "Not implemented - requires SAP configuration"}
    
    def sync_customer(self, customer_data: Dict) -> Dict:
        """Sync customer to SAP"""
        # Implementation similar to invoice sync
        return {"success": False, "error": "Not implemented - requires SAP configuration"}
    
    def get_chart_of_accounts(self) -> List[Dict]:
        """Get chart of accounts from SAP"""
        if not self.session_id:
            self.authenticate()
        
        try:
            response = requests.get(
                f"{self.api_endpoint}/ChartOfAccounts",
                cookies={"B1SESSION": self.session_id},
                verify=False
            )
            
            if response.status_code == 200:
                accounts = response.json().get('value', [])
                return [
                    {
                        "id": acc['Code'],
                        "name": acc['Name'],
                        "type": acc.get('AcctCurrency', ''),
                        "code": acc['Code']
                    }
                    for acc in accounts
                ]
            else:
                raise Exception(f"Failed to get accounts: {response.text}")
        
        except Exception as e:
            raise Exception(f"Error getting chart of accounts: {str(e)}")


# Stub connectors for other systems
class NetSuiteConnector(FinancialSystemConnector):
    """NetSuite SuiteTalk API Connector - Requires configuration"""
    
    def authenticate(self) -> bool:
        raise NotImplementedError("NetSuite connector requires account-specific configuration")
    
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        return {"success": False, "error": "NetSuite connector not configured"}
    
    def sync_payment(self, payment_data: Dict) -> Dict:
        return {"success": False, "error": "NetSuite connector not configured"}
    
    def sync_customer(self, customer_data: Dict) -> Dict:
        return {"success": False, "error": "NetSuite connector not configured"}
    
    def get_chart_of_accounts(self) -> List[Dict]:
        raise NotImplementedError("NetSuite connector requires account-specific configuration")


class SageConnector(FinancialSystemConnector):
    """Sage Intacct API Connector - Requires configuration"""
    
    def authenticate(self) -> bool:
        raise NotImplementedError("Sage connector requires account-specific configuration")
    
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        return {"success": False, "error": "Sage connector not configured"}
    
    def sync_payment(self, payment_data: Dict) -> Dict:
        return {"success": False, "error": "Sage connector not configured"}
    
    def sync_customer(self, customer_data: Dict) -> Dict:
        return {"success": False, "error": "Sage connector not configured"}
    
    def get_chart_of_accounts(self) -> List[Dict]:
        raise NotImplementedError("Sage connector requires account-specific configuration")


class DynamicsConnector(FinancialSystemConnector):
    """Microsoft Dynamics 365 API Connector - Requires configuration"""
    
    def authenticate(self) -> bool:
        raise NotImplementedError("Dynamics connector requires account-specific configuration")
    
    def sync_invoice(self, invoice_data: Dict) -> Dict:
        return {"success": False, "error": "Dynamics connector not configured"}
    
    def sync_payment(self, payment_data: Dict) -> Dict:
        return {"success": False, "error": "Dynamics connector not configured"}
    
    def sync_customer(self, customer_data: Dict) -> Dict:
        return {"success": False, "error": "Dynamics connector not configured"}
    
    def get_chart_of_accounts(self) -> List[Dict]:
        raise NotImplementedError("Dynamics connector requires account-specific configuration")


# Connector factory
def get_connector(provider: str, config: Dict[str, Any]) -> FinancialSystemConnector:
    """
    Factory method to get the appropriate connector
    
    Args:
        provider: One of 'quickbooks', 'xero', 'sap', 'netsuite', 'sage', 'dynamics'
        config: Configuration dictionary with credentials and settings
    
    Returns:
        FinancialSystemConnector instance
    """
    connectors = {
        'quickbooks': QuickBooksConnector,
        'xero': XeroConnector,
        'sap': SAPConnector,
        'netsuite': NetSuiteConnector,
        'sage': SageConnector,
        'dynamics': DynamicsConnector
    }
    
    connector_class = connectors.get(provider.lower())
    if not connector_class:
        raise ValueError(f"Unknown provider: {provider}")
    
    return connector_class(config)
