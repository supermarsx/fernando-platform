"""
Application startup and initialization logic
"""
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, init_db
from app.services.enterprise_service import EnterpriseService
from app.services.queue_manager import QueueManager
from app.services.licensing_service import initialize_default_tiers
from app.services.cache.redis_cache import init_cache_service

logger = logging.getLogger(__name__)

class ApplicationStartup:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def initialize_application(self):
        """Initialize all application components"""
        # Initialize database
        init_db()
        
        # Initialize enterprise features
        await self._initialize_enterprise_features()
        
        # Initialize cache service
        await self._initialize_cache()
        
        self._print_startup_banner()
    
    async def _initialize_enterprise_features(self):
        """Initialize enterprise-specific features"""
        db = SessionLocal()
        try:
            # Initialize enterprise service
            enterprise_service = EnterpriseService(db)
            
            # Initialize licensing tiers
            initialize_default_tiers(db)
            
            # Initialize queue manager
            queue_manager = QueueManager(db)
            await queue_manager.initialize_queues()
            
            self.logger.info("Enterprise features and licensing initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing enterprise features: {e}")
            raise
        finally:
            db.close()
    
    async def _initialize_cache(self):
        """Initialize cache service"""
        try:
            await init_cache_service()
            self.logger.info("Cache service initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing cache service: {e}")
            raise
    
    def _print_startup_banner(self):
        """Print application startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════╗
║                    🚀 FERNANDO PLATFORM v2.0                    ║
║                  Enterprise Invoice Processing                   ║
║                                                                  ║
║  ✅ Database initialized                                         ║
║  ✅ Enterprise features active                                   ║
║  ✅ Cache service running                                        ║
║  ✅ OCR and LLM services ready                                  ║
║  ✅ TOCOnline integration enabled                                ║
║                                                                  ║
║  🌐 API Server: http://localhost:8000                           ║
║  📋 Admin Panel: http://localhost:3000                          ║
║  📊 Monitoring: http://localhost:8000/docs                      ║
║                                                                  ║
║  Ready to process Portuguese invoices with enterprise features! ║
╚══════════════════════════════════════════════════════════════════╝
        """
        print(banner)
        self.logger.info("Fernando Platform started successfully")