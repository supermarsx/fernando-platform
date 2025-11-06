# TOCOnline API Research - Files & Screenshots Summary

## Screenshots Captured

1. **toconline_api_main_page.png** - Main documentation homepage (Introduction)
2. **toconline_api_simplified_auth.png** - Simplified authentication documentation
3. **toconline_api_company.png** - Company API overview page
4. **toconline_api_sales.png** - Sales API overview page
5. **toconline_api_sales_documents.png** - Detailed sales documents/invoices API
6. **toconline_api_purchases.png** - Purchases API overview page
7. **toconline_api_purchase_documents.png** - Detailed purchase documents/invoices API
8. **toconline_api_request_characteristics.png** - API request characteristics and patterns
9. **toconline_api_auxiliary_apis.png** - Auxiliary APIs overview
10. **toconline_swagger_spec.png** - OpenAPI/SwaggerHub specification page

## Extracted Content Files

1. **toconline_api_intro.json** - Introduction page content
2. **toconline_simplified_authentication.json** - Authentication details
3. **toconline_company_api_overview.json** - Company API overview
4. **toconline_sales_api_overview.json** - Sales API overview
5. **toconline_sales_documents_api.json** - Detailed sales document API (invoices, quotes, etc.)
6. **toconline_compras_api_overview.json** - Purchases API overview
7. **toconline_purchase_documents_api.json** - Detailed purchase document API (supplier invoices)
8. **api_request_characteristics.json** - API request patterns and conventions
9. **toconline_auxiliary_apis.json** - Auxiliary APIs overview
10. **toconline_open_api_1.0.0_swagger_hub.json** - Complete Swagger/OpenAPI specification

## Key Technical Findings

### Authentication
- OAuth2 3-step process with automatic finalization
- Bearer token authentication for API calls
- Simplified setup via TOConline platform

### Invoice & Accounting Document Types
- **Sales Documents:** FT (Invoice), FS (Simplified Invoice), FR (Invoice-Receipt), Estimates, Proforma, Delivery Notes
- **Purchase Documents:** FC (Invoice), DSP (Expense Invoice)
- **Payment Processing:** Sales receipts, purchase payments
- **Compliance:** Automatic AT (Portuguese Tax Authority) communication

### API Structure
- RESTful design with JSON:API conventions
- Automatic document finalization in v1
- Comprehensive filtering and pagination support
- Extensive auxiliary APIs for master data management

### Portuguese Compliance Features
- Multi-region support (PT, PT-AC, PT-MA)
- VAT handling with Portuguese rates
- Retention tax support (IRS/IRC)
- Document series management
- Tax authority integration

## Implementation Resources
- Complete OpenAPI specification available on SwaggerHub
- Postman configuration files available
- Comprehensive helper API endpoints for data relationships
- PDF generation and email distribution built-in