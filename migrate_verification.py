"""
Database migration script for human verification and quality control workflow.

This script creates the necessary database tables for the verification workflow system.
"""

import logging
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.db.session import SessionLocal
from app.models.verification import (
    VerificationTask, QualityReview, AIAssistanceLog, VerificationTeam,
    VerificationPerformance, VerificationWorkflow, VerificationAudit,
    VerificationStatus, PriorityLevel, VerificationType, QualityScore
)

def create_verification_tables():
    """Create all verification workflow tables."""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    db = SessionLocal()
    
    try:
        logger.info("Starting verification workflow database migration...")
        
        # Create all tables
        from app.models.verification import Base
        Base.metadata.create_all(bind=db.bind)
        
        logger.info("✓ Verification workflow tables created successfully")
        
        # Create default verification teams
        create_default_teams(db, logger)
        
        # Create default workflows
        create_default_workflows(db, logger)
        
        db.commit()
        logger.info("✓ Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def create_default_teams(db, logger):
    """Create default verification teams."""
    
    teams = [
        {
            'team_name': 'Invoice Processing Team',
            'team_code': 'invoice_team',
            'team_description': 'Specialized team for invoice document verification',
            'specialization_area': 'invoices',
            'expertise_level': 'senior',
            'max_concurrent_tasks': 15,
            'is_active': True
        },
        {
            'team_name': 'Receipt Processing Team',
            'team_code': 'receipt_team',
            'team_description': 'Specialized team for receipt document verification',
            'specialization_area': 'receipts',
            'expertise_level': 'senior',
            'max_concurrent_tasks': 20,
            'is_active': True
        },
        {
            'team_name': 'General Documents Team',
            'team_code': 'general_team',
            'team_description': 'General purpose document verification team',
            'specialization_area': 'general',
            'expertise_level': 'junior',
            'max_concurrent_tasks': 10,
            'is_active': True
        },
        {
            'team_name': 'Quality Assurance Team',
            'team_code': 'qa_team',
            'team_description': 'Quality control and review specialists',
            'specialization_area': 'quality_control',
            'expertise_level': 'expert',
            'max_concurrent_tasks': 8,
            'is_active': True
        }
    ]
    
    for team_data in teams:
        existing_team = db.query(VerificationTeam).filter(
            VerificationTeam.team_code == team_data['team_code']
        ).first()
        
        if not existing_team:
            team = VerificationTeam(
                **team_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by='system'
            )
            db.add(team)
            logger.info(f"✓ Created team: {team_data['team_name']}")
        else:
            logger.info(f"✓ Team already exists: {team_data['team_name']}")

def create_default_workflows(db, logger):
    """Create default verification workflows."""
    
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
            'version': '1.0'
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
            'version': '1.0'
        },
        {
            'workflow_name': 'Batch Processing Workflow',
            'workflow_type': 'custom',
            'document_type': 'batch',
            'steps': [
                {'step_name': 'batch_assignment', 'required': True, 'timeout_minutes': 5},
                {'step_name': 'bulk_verification', 'required': True, 'timeout_minutes': 480},
                {'step_name': 'batch_quality_review', 'required': False, 'timeout_minutes': 120}
            ],
            'assignment_rules': {
                'auto_assign': True,
                'batch_processing': True,
                'max_batch_size': 20
            },
            'escalation_rules': {
                'timeout_hours': 8,
                'max_escalations': 2
            },
            'quality_thresholds': {
                'excellent': 0.90,
                'good': 0.80,
                'acceptable': 0.65
            },
            'sla_time_hours': 48,
            'escalation_timeout_hours': 4,
            'auto_assignment_delay_minutes': 2,
            'is_active': True,
            'version': '1.0'
        }
    ]
    
    for workflow_data in workflows:
        existing_workflow = db.query(VerificationWorkflow).filter(
            VerificationWorkflow.workflow_name == workflow_data['workflow_name']
        ).first()
        
        if not existing_workflow:
            workflow = VerificationWorkflow(
                **workflow_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by='system'
            )
            db.add(workflow)
            logger.info(f"✓ Created workflow: {workflow_data['workflow_name']}")
        else:
            logger.info(f"✓ Workflow already exists: {workflow_data['workflow_name']}")

if __name__ == "__main__":
    create_verification_tables()
    print("\n" + "="*60)
    print("HUMAN VERIFICATION WORKFLOW MIGRATION COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Start the backend server: python run_server.sh")
    print("2. Start the frontend server: cd frontend/accounting-frontend && npm start")
    print("3. Access the verification dashboard at http://localhost:3000")
    print("\nDefault teams created:")
    print("  • Invoice Processing Team")
    print("  • Receipt Processing Team") 
    print("  • General Documents Team")
    print("  • Quality Assurance Team")
    print("\nDefault workflows created:")
    print("  • Standard Invoice Verification")
    print("  • Critical Document Verification")
    print("  • Batch Processing Workflow")
    print("\nDatabase tables created:")
    print("  • verification_tasks")
    print("  • quality_reviews")
    print("  • ai_assistance_logs")
    print("  • verification_teams")
    print("  • verification_performance")
    print("  • verification_workflows")
    print("  • verification_audit")