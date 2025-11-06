"""
Simple database migration script for human verification workflow.

This script creates the verification workflow tables without relying on the full application configuration.
"""

import logging
import os
import sys

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Simple database setup without app configuration
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Create a simple database engine
Base = declarative_base()

# Define models directly (simplified versions)
class VerificationStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    BATCH_PROCESSING = "batch_processing"

class PriorityLevel:
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class VerificationType:
    INITIAL = "initial"
    PEER_REVIEW = "peer_review"
    SUPERVISOR_REVIEW = "supervisor_review"
    QUALITY_CHECK = "quality_check"
    REWORK = "rework"
    BATCH_VERIFICATION = "batch_verification"

class QualityScore:
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"

# Simplified Verification Task model
class VerificationTask(Base):
    __tablename__ = "verification_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    document_id = Column(String(255), index=True, nullable=False)
    extraction_id = Column(String(255), index=True, nullable=False)
    task_type = Column(String(100), nullable=False)
    status = Column(String(100), default=VerificationStatus.PENDING)
    priority = Column(String(50), default=PriorityLevel.NORMAL)
    
    assigned_to = Column(String(255), index=True)
    assigned_team = Column(String(255), index=True)
    assigned_at = Column(DateTime)
    due_date = Column(DateTime)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_time_seconds = Column(Integer)
    
    ai_confidence_score = Column(Float)
    ai_suggestions = Column(JSON)
    ai_detected_anomalies = Column(JSON)
    
    verified_data = Column(JSON)
    verification_comments = Column(Text)
    corrections_made = Column(JSON)
    quality_score = Column(String(50))
    verification_accuracy = Column(Float)
    
    parent_task_id = Column(Integer, ForeignKey("verification_tasks.id"))
    escalation_level = Column(Integer, default=0)
    is_urgent = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    last_modified_by = Column(String(255))

# Simplified Quality Review model
class QualityReview(Base):
    __tablename__ = "quality_reviews"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String(255), unique=True, index=True, nullable=False)
    verification_task_id = Column(Integer, ForeignKey("verification_tasks.id"), nullable=False)
    
    reviewer_id = Column(String(255), index=True)
    reviewer_role = Column(String(100))
    review_type = Column(String(100), nullable=False)
    
    quality_score = Column(Float)
    overall_rating = Column(String(50))
    is_approved = Column(Boolean)
    
    accuracy_score = Column(Float)
    completeness_score = Column(Float)
    consistency_score = Column(Float)
    efficiency_score = Column(Float)
    
    strengths = Column(JSON)
    weaknesses = Column(JSON)
    recommendations = Column(JSON)
    corrective_actions = Column(JSON)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    review_time_seconds = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    review_notes = Column(Text)

# Simplified Verification Team model
class VerificationTeam(Base):
    __tablename__ = "verification_teams"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(255), unique=True, index=True, nullable=False)
    team_code = Column(String(50), unique=True, nullable=False)
    team_description = Column(Text)
    
    specialization_area = Column(String(100))
    expertise_level = Column(String(50))
    
    team_lead = Column(String(255))
    members = Column(JSON)
    
    max_concurrent_tasks = Column(Integer, default=10)
    average_processing_time = Column(Float)
    quality_accuracy_rate = Column(Float)
    
    is_active = Column(Boolean, default=True)
    working_hours_start = Column(DateTime)
    working_hours_end = Column(DateTime)
    timezone = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))

# Simplified Verification Workflow model
class VerificationWorkflow(Base):
    __tablename__ = "verification_workflows"

    id = Column(Integer, primary_key=True, index=True)
    workflow_name = Column(String(255), unique=True, index=True, nullable=False)
    workflow_type = Column(String(100))
    document_type = Column(String(100))
    
    steps = Column(JSON)
    current_step = Column(String(100))
    step_status = Column(String(100))
    
    assignment_rules = Column(JSON)
    escalation_rules = Column(JSON)
    quality_thresholds = Column(JSON)
    
    sla_time_hours = Column(Integer)
    escalation_timeout_hours = Column(Integer)
    auto_assignment_delay_minutes = Column(Integer)
    
    is_active = Column(Boolean, default=True)
    version = Column(String(50), default="1.0")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))

def create_simple_verification_tables():
    """Create verification workflow tables using simplified models."""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Create database engine
        engine = create_engine("sqlite:///./accounting_automation.db", echo=False)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Verification workflow tables created successfully")
        
        # Create default teams
        create_default_teams_simple(engine, logger)
        
        # Create default workflows
        create_default_workflows_simple(engine, logger)
        
        logger.info("✓ Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

def create_default_teams_simple(engine, logger):
    """Create default verification teams using direct SQL."""
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    teams = [
        {
            'team_name': 'Invoice Processing Team',
            'team_code': 'invoice_team',
            'team_description': 'Specialized team for invoice document verification',
            'specialization_area': 'invoices',
            'expertise_level': 'senior',
            'max_concurrent_tasks': 15,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system'
        },
        {
            'team_name': 'Receipt Processing Team',
            'team_code': 'receipt_team',
            'team_description': 'Specialized team for receipt document verification',
            'specialization_area': 'receipts',
            'expertise_level': 'senior',
            'max_concurrent_tasks': 20,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system'
        },
        {
            'team_name': 'General Documents Team',
            'team_code': 'general_team',
            'team_description': 'General purpose document verification team',
            'specialization_area': 'general',
            'expertise_level': 'junior',
            'max_concurrent_tasks': 10,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system'
        },
        {
            'team_name': 'Quality Assurance Team',
            'team_code': 'qa_team',
            'team_description': 'Quality control and review specialists',
            'specialization_area': 'quality_control',
            'expertise_level': 'expert',
            'max_concurrent_tasks': 8,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system'
        }
    ]
    
    for team_data in teams:
        # Check if team already exists
        existing = db.query(VerificationTeam).filter(
            VerificationTeam.team_code == team_data['team_code']
        ).first()
        
        if not existing:
            team = VerificationTeam(**team_data)
            db.add(team)
            logger.info(f"✓ Created team: {team_data['team_name']}")
        else:
            logger.info(f"✓ Team already exists: {team_data['team_name']}")
    
    db.commit()
    db.close()

def create_default_workflows_simple(engine, logger):
    """Create default verification workflows using direct SQL."""
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    workflows = [
        {
            'workflow_name': 'Standard Invoice Verification',
            'workflow_type': 'standard',
            'document_type': 'invoice',
            'steps': [
                {'step_name': 'initial_verification', 'required': True, 'timeout_minutes': 30},
                {'step_name': 'peer_review', 'required': False, 'timeout_minutes': 60},
                {'step_name': 'quality_check', 'required': False, 'timeout_minutes': 45}
            ],
            'assignment_rules': {
                'auto_assign': True,
                'team_specialization': 'invoices',
                'load_balancing': True
            },
            'escalation_rules': {
                'timeout_hours': 2,
                'max_escalations': 3,
                'escalate_to_supervisor': True
            },
            'quality_thresholds': {
                'excellent': 0.95,
                'good': 0.85,
                'acceptable': 0.70
            },
            'sla_time_hours': 24,
            'escalation_timeout_hours': 2,
            'auto_assignment_delay_minutes': 5,
            'is_active': True,
            'version': '1.0',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system'
        },
        {
            'workflow_name': 'Critical Document Verification',
            'workflow_type': 'emergency',
            'document_type': 'critical',
            'steps': [
                {'step_name': 'initial_verification', 'required': True, 'timeout_minutes': 15},
                {'step_name': 'peer_review', 'required': True, 'timeout_minutes': 30},
                {'step_name': 'supervisor_review', 'required': True, 'timeout_minutes': 60}
            ],
            'assignment_rules': {
                'auto_assign': True,
                'team_specialization': 'senior',
                'load_balancing': False,
                'priority_override': True
            },
            'escalation_rules': {
                'timeout_hours': 1,
                'max_escalations': 5,
                'escalate_to_supervisor': True,
                'notify_management': True
            },
            'quality_thresholds': {
                'excellent': 0.98,
                'good': 0.90,
                'acceptable': 0.80
            },
            'sla_time_hours': 4,
            'escalation_timeout_hours': 1,
            'auto_assignment_delay_minutes': 1,
            'is_active': True,
            'version': '1.0',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': 'system'
        }
    ]
    
    for workflow_data in workflows:
        # Check if workflow already exists
        existing = db.query(VerificationWorkflow).filter(
            VerificationWorkflow.workflow_name == workflow_data['workflow_name']
        ).first()
        
        if not existing:
            workflow = VerificationWorkflow(**workflow_data)
            db.add(workflow)
            logger.info(f"✓ Created workflow: {workflow_data['workflow_name']}")
        else:
            logger.info(f"✓ Workflow already exists: {workflow_data['workflow_name']}")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    create_simple_verification_tables()
    print("\n" + "="*60)
    print("HUMAN VERIFICATION WORKFLOW MIGRATION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Start the backend server: cd backend && python run_server.sh")
    print("2. Start the frontend server: cd frontend/accounting-frontend && npm start")
    print("3. Access the verification dashboard at http://localhost:3000")
    print("\nDatabase tables created:")
    print("  • verification_tasks")
    print("  • quality_reviews")
    print("  • verification_teams")
    print("  • verification_workflows")
    print("\nDefault teams created:")
    print("  • Invoice Processing Team")
    print("  • Receipt Processing Team") 
    print("  • General Documents Team")
    print("  • Quality Assurance Team")
    print("\nDefault workflows created:")
    print("  • Standard Invoice Verification")
    print("  • Critical Document Verification")
    print("\nThe verification workflow system is now ready for use!")