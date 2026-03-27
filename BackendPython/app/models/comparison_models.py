"""
SQLAlchemy ORM models for product comparison history
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database_orm import Base


class ComparisonHistory(Base):
    """
    Stores product comparison history for users
    """
    __tablename__ = "comparison_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Product references
    product_id_1 = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    product_id_2 = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Product names for quick display
    product_name_1 = Column(String(500), nullable=False)
    product_name_2 = Column(String(500), nullable=False)
    
    # Comparison metadata
    comparison_type = Column(String(50), default="detailed")
    llm_model = Column(String(100), default="gpt-4")
    
    # Full comparison result
    snapshot_a = Column(JSON, nullable=True)
    snapshot_b = Column(JSON, nullable=True)
    comparison_result = Column(Text, nullable=False)
    summary_json = Column(JSON, nullable=True)
    
    # Original API request data
    api_request = Column(JSON, nullable=True)
    
    # User notes and metadata
    notes = Column(String(500), nullable=True)
    is_starred = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    product_1 = relationship("Product", foreign_keys=[product_id_1], lazy="joined")
    product_2 = relationship("Product", foreign_keys=[product_id_2], lazy="joined")

    def __repr__(self):
        return f"<ComparisonHistory(id={self.id}, user_id={self.user_id}, products={self.product_id_1} vs {self.product_id_2})>"
