"""
Comparison History Repository
Handles CRUD operations for comparison history
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from models.comparison_models import ComparisonHistory  # ✅ LOCAL
from models.comparison_schemas import (  # ✅ LOCAL
    ComparisonHistoryResponse,
    ComparisonHistoryList,
    SaveComparisonRequest,
)

logger = logging.getLogger(__name__)


class ComparisonHistoryRepository:
    """Repository for comparison history operations"""

    @staticmethod
    def save_comparison(
        db: Session,
        user_id: int,
        product_id_1: int,
        product_id_2: int,
        product_name_1: str,
        product_name_2: str,
        snapshot_a: Dict[str, Any],
        snapshot_b: Dict[str, Any],
        comparison_result: str,
        summary_json: Optional[Dict[str, Any]] = None,
        api_request: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        comparison_type: str = "detailed",
        llm_model: str = "gpt-4",
    ) -> ComparisonHistory:
        """
        Save a new comparison to the database
        """
        try:
            comparison = ComparisonHistory(
                user_id=user_id,
                product_id_1=product_id_1,
                product_id_2=product_id_2,
                product_name_1=product_name_1,
                product_name_2=product_name_2,
                snapshot_a=snapshot_a,
                snapshot_b=snapshot_b,
                comparison_result=comparison_result,
                summary_json=summary_json,
                api_request=api_request,
                notes=notes,
                comparison_type=comparison_type,
                llm_model=llm_model,
                is_starred=False,
            )
            
            db.add(comparison)
            db.commit()
            db.refresh(comparison)
            
            logger.info(f"✅ Saved comparison {comparison.id} for user {user_id}")
            return comparison
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving comparison: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_comparison(
        db: Session,
        comparison_id: int,
        user_id: int,
    ) -> Optional[ComparisonHistory]:
        """
        Get a single comparison by ID (user must own it)
        """
        try:
            comparison = db.query(ComparisonHistory).filter(
                and_(
                    ComparisonHistory.id == comparison_id,
                    ComparisonHistory.user_id == user_id,
                )
            ).first()
            
            if not comparison:
                logger.warning(f"Comparison {comparison_id} not found for user {user_id}")
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error getting comparison: {str(e)}")
            raise

    @staticmethod
    def get_user_comparisons(
        db: Session,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
        starred_only: bool = False,
    ) -> tuple[List[ComparisonHistory], int]:
        """
        Get comparison history for a user with pagination
        
        Returns:
            (comparisons list, total count)
        """
        try:
            query = db.query(ComparisonHistory).filter(
                ComparisonHistory.user_id == user_id
            )
            
            if starred_only:
                query = query.filter(ComparisonHistory.is_starred.is_(True))
            
            # Get total count
            total = query.count()
            
            # Order by created_at desc and apply pagination
            comparisons = query.order_by(
                desc(ComparisonHistory.created_at)
            ).limit(limit).offset(offset).all()
            
            logger.info(
                f"Retrieved {len(comparisons)} comparisons for user {user_id} "
                f"(total: {total}, starred_only: {starred_only})"
            )
            
            return comparisons, total
            
        except Exception as e:
            logger.error(f"Error getting user comparisons: {str(e)}")
            raise

    @staticmethod
    def update_comparison(
        db: Session,
        comparison_id: int,
        user_id: int,
        notes: Optional[str] = None,
        is_starred: Optional[bool] = None,
    ) -> Optional[ComparisonHistory]:
        """
        Update comparison metadata (notes, starred status)
        """
        try:
            comparison = db.query(ComparisonHistory).filter(
                and_(
                    ComparisonHistory.id == comparison_id,
                    ComparisonHistory.user_id == user_id,
                )
            ).first()
            
            if not comparison:
                logger.warning(f"Comparison {comparison_id} not found for update")
                return None
            
            if notes is not None:
                comparison.notes = notes
            
            if is_starred is not None:
                comparison.is_starred = is_starred
            
            db.commit()
            db.refresh(comparison)
            
            logger.info(f"✅ Updated comparison {comparison_id}")
            return comparison
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating comparison: {str(e)}")
            raise

    @staticmethod
    def delete_comparison(
        db: Session,
        comparison_id: int,
        user_id: int,
    ) -> bool:
        """
        Delete a comparison (user must own it)
        """
        try:
            result = db.query(ComparisonHistory).filter(
                and_(
                    ComparisonHistory.id == comparison_id,
                    ComparisonHistory.user_id == user_id,
                )
            ).delete()
            
            db.commit()
            
            if result > 0:
                logger.info(f"✅ Deleted comparison {comparison_id}")
                return True
            else:
                logger.warning(f"Comparison {comparison_id} not found for deletion")
                return False
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting comparison: {str(e)}")
            raise

    @staticmethod
    def delete_all_user_comparisons(
        db: Session,
        user_id: int,
    ) -> int:
        """
        Delete all comparisons for a user (careful!)
        """
        try:
            count = db.query(ComparisonHistory).filter(
                ComparisonHistory.user_id == user_id
            ).delete()
            
            db.commit()
            logger.info(f"✅ Deleted {count} comparisons for user {user_id}")
            return count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user comparisons: {str(e)}")
            raise

    @staticmethod
    def get_comparison_stats(
        db: Session,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Get statistics about user's comparisons
        """
        try:
            total = db.query(ComparisonHistory).filter(
                ComparisonHistory.user_id == user_id
            ).count()
            
            starred = db.query(ComparisonHistory).filter(
                and_(
                    ComparisonHistory.user_id == user_id,
                    ComparisonHistory.is_starred.is_(True),
                )
            ).count()
            
            stats = {
                "total_comparisons": total,
                "starred_comparisons": starred,
                "unstarred_comparisons": total - starred,
            }
            
            logger.info(f"Comparison stats for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting comparison stats: {str(e)}")
            raise
