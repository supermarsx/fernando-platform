"""
Router configuration and registration
"""
from fastapi import FastAPI

def setup_routes(app: FastAPI):
    """Register all API routers"""
    
    # Import routers
    from app.api import (
        auth, jobs, extractions, toconline, admin, enterprise, 
        queue, export_import, licenses, billing, payments, 
        usage, enterprise_billing, revenue_operations, alerting, 
        user_management, enhanced_documents, verification, system
    )
    
    # Enterprise and feature routers
    app.include_router(verification.router, prefix="/api/verification", tags=["verification"])  # Human verification workflow
    app.include_router(enterprise.router, prefix="/api/v1")
    app.include_router(queue.router, prefix="/api/v1")
    app.include_router(export_import.router, prefix="/api/v1")
    app.include_router(licenses.router)
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
    app.include_router(usage.router, prefix="/api/v1", tags=["usage"])
    app.include_router(enterprise_billing.router)  # Enterprise billing features
    app.include_router(revenue_operations.router, prefix="/api/v1/revenue-ops", tags=["revenue-operations"])  # Revenue operations & analytics
    app.include_router(alerting.router, prefix="/api/v1/alerts", tags=["alerts"])  # Alerting system
    
    # Original API routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(extractions.router, prefix="/api/v1")
    app.include_router(toconline.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(user_management.router, prefix="/api/v1")
    app.include_router(enhanced_documents.router, prefix="/api/v1")  # Enhanced document processing
    app.include_router(system.router, prefix="/api/v1")  # System monitoring and health checks