from models.crowd_visitor_model import CrowdVisitor
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime


def get_crowd_visitors(db: Session, visitor_id: int, user_id: int) -> CrowdVisitor:
    return db.query(CrowdVisitor).filter(CrowdVisitor.visitor_id == visitor_id).first()

def get_user_crowd_visitor(db: Session, user_id: int) -> CrowdVisitor:
    return db.query(CrowdVisitor).filter(CrowdVisitor.user_id == user_id).all()

def get_user_crowd_visitors_updated_at(db: Session, user_id: int, update_time: datetime) -> CrowdVisitor:
    return db.query(CrowdVisitor).filter(CrowdVisitor.user_id == user_id, CrowdVisitor.updated_at >= update_time).all()

def get_user_crowd_visitors_created_at(db: Session, user_id: int, create_time: datetime) -> CrowdVisitor:
    return db.query(CrowdVisitor).filter(CrowdVisitor.user_id == user_id, CrowdVisitor.created_at >= create_time).all()

def create_crowd_visitor(db: Session, visitor_id: int, user_id: int, visitor_type: str) -> CrowdVisitor:
    visitor = CrowdVisitor(visitor_id=visitor_id, user_id=user_id, visitor_type=visitor_type)
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    
    return visitor

def create_crowd_visitors_batch(db: Session, visitor_ids: list[int], user_id: int, visitor_types: list[str]) -> list[CrowdVisitor]:
    visitors = []
    now = datetime.now()

    for visitor_id, visitor_type in zip(visitor_ids, visitor_types):
        visitor = CrowdVisitor(visitor_id=visitor_id, user_id=user_id, visitor_type=visitor_type, created_at=now, updated_at=now)
        db.add(visitor)
        visitors.append(visitor)
    
    db.commit()
    
    return visitors

def create_or_update_crowd_visitor(db: Session, visitor_id: int, user_id: int, visitor_type: str) -> CrowdVisitor:
    visitor = db.query(CrowdVisitor).filter(CrowdVisitor.visitor_id == visitor_id).first()
    if visitor:
        visitor.user_id = user_id
        visitor.visitor_type = visitor_type
        visitor.updated_at = datetime.now()
        db.commit()
        db.refresh(visitor)
    else:
        visitor = create_crowd_visitor(db, visitor_id, user_id, visitor_type)
    
    return visitor

def delete_crowd_visitors(db: Session, visitor_ids: list[int], user_id: int = None) -> bool:
    db.execute(CrowdVisitor.__table__.delete().where(CrowdVisitor.user_id == user_id, CrowdVisitor.visitor_id.in_(visitor_ids)))
    db.commit()
    
    return True
    

def create_or_update_crowd_visitors_batch(db: Session, visitor_ids: list[int], user_id: int, visitor_types: list[str]) -> list[CrowdVisitor]:
    delete_crowd_visitors(db, visitor_ids, user_id)
    
    return create_crowd_visitors_batch(db, visitor_ids, user_id, visitor_types)

def update_crowd_visitor(db: Session, visitor_id: int, user_id: int, visitor_type: str) -> CrowdVisitor:
    visitor = db.query(CrowdVisitor).filter(CrowdVisitor.visitor_id == visitor_id).first()
    if visitor:
        visitor.user_id = user_id
        visitor.visitor_type = visitor_type
        visitor.updated_at = datetime.now()
        db.commit()
        db.refresh(visitor)
        
    return visitor

def update_crowd_visitors_batch(db: Session, visitor_ids: list[int], user_id: int, visitor_types: list[str]) -> CrowdVisitor:
    visitors = db.query(CrowdVisitor).filter(CrowdVisitor.visitor_id.in_(visitor_ids)).all()
    
    for visitor in visitors:
        visitor.user_id = user_id
        visitor.visitor_type = visitor_types[visitor_ids.index(visitor.visitor_id)]
        visitor.updated_at = datetime.now()
    
    db.commit()
    
    return visitors