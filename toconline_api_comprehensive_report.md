# TOCOnline API Comprehensive Documentation Report

**Research Date:** 2025-11-05  
**API Base URL:** https://api-docs.toconline.pt/  
**OpenAPI Specification:** https://app.swaggerhub.com/apis/toconline.pt/toc-online_open_api/1.0.0

## Executive Summary

The TOCOnline API is a comprehensive REST API designed for Portuguese accounting and invoice management systems. It provides extensive functionality for managing sales documents (invoices, quotes, delivery notes), purchase documents (supplier invoices, expense reports), company master data, and tax compliance with Portuguese tax authorities (AT - Autoridade Tributária).

## Key Findings - Invoice and Accounting Document APIs

### 1. Authentication System

**Simplified Authentication (Recommended)**
- **3-Step OAuth2 Process:**
  1. **Obtain API Credentials:** Get `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OAUTH_URL`, `API_URL` from TOConline platform
  2. **Get Authorization Code:** GET request to `OAUTH_URL/auth` with client_id, redirect_uri, response_type=code, scope=commercial
  3. **Get Access Token:** POST to `OAUTH_URL/token` with authorization code and base64 encoded credentials

**Headers Required:**
- `Authorization: Bearer <access_token>`
- `Content-Type: application/json`
- `Accept: application/json`

### 2. Sales Document API (Invoices & Related Documents)

**Base Endpoint:** `/api/v1/commercial_sales_documents`

#### Document Types Supported:
- **FT** - Fatura (Invoice)
- **FS** - Fatura simplificada (Simplified Invoice)
- **FR** - Fatura-recibo (Invoice-receipt)
- **Orçamentos** (Estimates)
- **Faturas-proforma** (Proforma Invoices)
- **Guias** (Delivery Notes)
- **Notas** (Credit/Debit Notes)

#### Key Endpoints:

**Create Sales Document**
```
POST /api/v1/commercial_sales_documents
```
- **Automatic Finalization:** All documents are automatically finalized upon creation
- **No Updates/Deletes:** Finalized documents cannot be modified or deleted via API
- **Complete Document Creation:** Header and line items created in single request

**Request Structure:**
```json
{
  "document_type": "FT", // Invoice type
  "date": "2023-01-01",
  "customer_id": 123, // Optional if using tax number
  "customer_tax_registration_number": "229659179",
  "customer_business_name": "Ricardo Ribeiro",
  "customer_address_detail": "Praceta da Liberdade n5",
  "customer_city": "Lisboa",
  "customer_postcode": "1000-101",
  "customer_country": "PT",
  "due_date": "2023-02-01",
  "currency_iso_code": "EUR",
  "currency_conversion_rate": 1.21,
  "payment_mechanism": "MO",
  "retention": 7.5,
  "retention_type": "IRS",
  "apply_retention_when_paid": true,
  "vat_included_prices": false,
  "lines": [
    {
      "item_type": "Service", // or "Product"
      "item_id": 456, // Optional
      "description": "Service Description",
      "quantity": 1,
      "unit_price": 100.00,
      "settlement_expression": "5", // 5% discount
      "tax_id": 789,
      "tax_percentage": 23
    }
  ]
}
```

**Retrieve Sales Documents**
```
GET /api/v1/commercial_sales_documents/{salesDocumentId}
GET /api/v1/commercial_sales_documents/  // List all
```

### 3. Purchase Document API (Supplier Invoices & Expenses)

**Base Endpoint:** `/api/v1/commercial_purchases_documents`

#### Document Types:
- **FC** - Fatura (Invoice)
- **DSP** - Fatura de despesas (Expense Invoice)

#### Key Endpoints:

**Create Purchase Document**
```
POST /api/v1/commercial_purchases_documents
```

**Request Structure:**
```json
{
  "document_type": "FC", // Invoice type
  "supplier_id": 123, // Optional
  "supplier_tax_registration_number": "999999990",
  "supplier_business_name": "Nome do fornecedor",
  "supplier_address_detail": "Morada do fornecedor",
  "supplier_city": "Cidade/Localidade",
  "supplier_postcode": "0000-000",
  "supplier_country": "PT",
  "date": "2023-01-01",
  "due_date": "2023-02-01",
  "currency_iso_code": "USD",
  "currency_conversion_rate": 1.21,
  "retention_total": 9.99,
  "retention_type": "TD",
  "lines": [
    {
      "item_type": "Product", // or "Purchases::ExpenseCategory"
      "item_id": 456,
      "description": "Product description",
      "quantity": 1,
      "unit_price": 100.00,
      "tax_id": 789
    }
  ]
}
```

**Retrieve Purchase Documents**
```
GET /api/v1/commercial_purchases_documents
```

### 4. Payment Processing API

**Sales Receipts**
```
POST /api/v1/commercial_sales_receipts
GET /api/v1/commercial_sales_receipts/{salesReceiptId}
PATCH /api/v1/commercial_sales_receipts/{salesReceiptId}/void
```

**Purchase Payments**
```
POST /api/v1/commercial_purchases_payments
GET /api/v1/commercial_purchases_payments/{id}
PATCH /api/v1/commercial_purchases_payments/{id}
```

### 5. PDF Generation & Document Distribution

**PDF Download Endpoints:**
```
GET /api/url_for_print/{salesDocumentId}  // Sales documents
GET /api/url_for_print/{purchasesDocumentId}  // Purchase documents
```

**Email Distribution:**
```
PATCH /api/email/document  // Send documents via email
```

### 6. Tax Authority Communication (AT - Portuguese Tax Authority)

**Compliance Endpoints:**
```
PATCH /api/send_document_at_webservice
```
- Automatically communicates documents to Portuguese tax authorities
- Required for legal compliance in Portugal
- Handles both sales and purchase documents

### 7. Company Master Data API

**Customer Management:**
```
GET /api/customers
POST /api/customers
PATCH /api/customers
DELETE /api/customers/{customerId}
```

**Supplier Management:**
```
GET /api/suppliers
POST /api/suppliers
PATCH /api/suppliers
DELETE /api/suppliers/{supplierId}
```

**Products & Services:**
```
GET /api/products
POST /api/products
GET /api/services
POST /api/services
```

### 8. Auxiliary APIs (Supporting Functions)

**Tax & Compliance:**
- Tax Descriptors: `/api/tax_descriptors`
- Tax Rates: `/api/taxes`
- Tax Exemption Reasons: `/api/tax_exemption_reasons`

**Reference Data:**
- Countries: `/api/countries`
- Currencies: `/api/currencies`
- Units of Measure: `/api/units_of_measure`
- Document Series: `/api/commercial_document_series`
- Bank Accounts: `/api/bank_accounts`
- Cash Accounts: `/api/cash_accounts`
- Expense Categories: `/api/expense_categories`

### 9. API Request Characteristics

**Headers:**
- `Content-Type: application/vnd.api+json`
- `Accept: application/json`
- `Authorization: Bearer <access_token>`

**Filtering & Pagination:**
- **Filtering:** `filter[parameter]=value`
- **Pagination:** `page[size]=10` (default)
- **Date Filtering:** `filter[created_at]>'2022-01-01'::date`

**Response Codes:**
- 200 - Success
- 400 - Authorization missing or invalid request
- 302 - Redirect for authorization code

### 10. Important Implementation Notes

#### Document Finalization
- **Sales Documents:** Automatically finalized upon creation in API v1
- **Purchase Documents:** Automatically finalized upon creation in API v1
- **No Modifications:** Finalized documents cannot be updated, voided, or deleted
- **Alternative:** Use Previous Versions API for non-finalized document creation

#### Portuguese Compliance Features
- **VAT Handling:** Comprehensive VAT support with Portuguese rates
- **Retention Tax:** IRS/IRC retention handling
- **Multi-region Support:** PT, PT-AC (Azores), PT-MA (Madeira)
- **Tax Authority Integration:** Automatic communication to AT
- **Document Series:** Proper numbering sequences for legal compliance

#### Required Helper API Calls
Before creating documents, you typically need to:
1. Get document series ID: `/commercial_document_series`
2. Get customer/supplier IDs: `/customers` or `/suppliers`
3. Get tax rates: `/taxes`
4. Get product/service IDs: `/products` or `/services`
5. Get unit of measure IDs: `/units_of_measure`

### 11. API Limitations & Considerations

**Current API (v1) Limitations:**
- Documents automatically finalized (no drafts)
- Cannot update/delete finalized documents
- Single-step document creation (header + lines together)

**Previous Versions Available:**
- Support for draft document creation
- Separate header/line creation endpoints
- Update and void operations available

### 12. Integration Recommendations

**For Invoice Automation:**
1. Implement OAuth2 authentication flow
2. Set up proper document series management
3. Create master data synchronization (customers, products, taxes)
4. Implement PDF generation and email distribution
5. Set up AT communication for compliance
6. Consider using Previous Versions API for more flexible workflows

**For Accounting Integration:**
1. Synchronize chart of accounts
2. Map tax codes to accounting categories
3. Set up automatic retention calculations
4. Implement multi-currency handling
5. Create payment reconciliation processes

## Conclusion

The TOCOnline API provides a comprehensive solution for Portuguese invoice and accounting document management with strong tax compliance features. The API is well-structured for both sales and purchase document processing, with extensive support for Portuguese tax requirements and AT integration. The automatic finalization design ensures compliance but may require workflow adjustments for draft document management scenarios.