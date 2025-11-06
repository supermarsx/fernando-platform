"""
Main application entry point - REFACTORED VERSION
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.app_config import create_app
from app.core.middleware_config import setup_middleware
from app.core.exception_handlers import setup_exception_handlers
from app.core.router_config import setup_routes
from app.core.startup import ApplicationStartup

# Create application
app = create_app()

# Setup middleware
setup_middleware(app)

# Setup exception handlers  
setup_exception_handlers(app)

# Register routes
setup_routes(app)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Add basic endpoints
@app.get("/")
def root():
    return {
        "app": "Fernando Platform - Enterprise Edition",
        "version": "2.0.0-enterprise", 
        "status": "running",
        "docs": "/docs",
        "features": {
            "multi_tenant": True,
            "advanced_rbac": True,
            "batch_processing": True,
            "export_import": True,
            "audit_trails": True,
            "rate_limiting": True,
            "scheduling": True,
            "licensing_management": True,
            "billing_and_subscriptions": True,
            "usage_based_billing": True,
            "invoice_management": True,
            "usage_tracking_and_metering": True,
            "quota_enforcement": True,
            "usage_analytics_and_forecasting": True,
            "fraud_detection": True,
            "enterprise_billing": True,
            "multi_entity_billing": True,
            "department_allocation": True,
            "contract_management": True,
            "budget_tracking": True,
            "approval_workflows": True,
            "dispute_management": True,
            "financial_integration": True,
            "comprehensive_alerting": True,
            "human_verification_workflow": True,
            "ai_assisted_verification": True,
            "quality_control_system": True,
            "team_management": True,
            "performance_analytics": True
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0-enterprise",
        "enterprise_features": True
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    startup = ApplicationStartup()
    await startup.initialize_application()

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)