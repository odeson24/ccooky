"""
Database models and cache management for GitLab MR Lister
"""
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# Database setup
DATABASE_URL = "sqlite:///./mr_cache.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class MergeRequestCache(Base):
    """Cache table for GitLab merge requests"""
    __tablename__ = "merge_request_cache"

    id = Column(Integer, primary_key=True, index=True)
    mr_iid = Column(Integer, index=True)  # GitLab MR internal ID
    state = Column(String(20), index=True)  # opened, merged, closed, all
    project_id = Column(String(100), index=True)
    mr_data = Column(Text)  # JSON string of MR data
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)


class ClickUpTaskCache(Base):
    """Cache table for ClickUp tasks"""
    __tablename__ = "clickup_task_cache"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, index=True)
    task_data = Column(Text)  # JSON string of task data
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)


class CacheMetadata(Base):
    """Cache metadata for tracking refresh times"""
    __tablename__ = "cache_metadata"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(Text)
    last_updated = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CacheManager:
    """Manages caching operations"""

    def __init__(self, mr_ttl_minutes=5, clickup_ttl_minutes=10):
        self.mr_ttl = timedelta(minutes=mr_ttl_minutes)
        self.clickup_ttl = timedelta(minutes=clickup_ttl_minutes)

    def is_cache_valid(self, last_updated: datetime, ttl: timedelta) -> bool:
        """Check if cache entry is still valid"""
        if not last_updated:
            return False
        return datetime.utcnow() - last_updated < ttl

    def get_cached_merge_requests(self, db, project_id: str, state: str) -> list:
        """Get cached merge requests if valid"""
        try:
            # Get all MRs for this project and state
            cached_mrs = db.query(MergeRequestCache).filter(
                MergeRequestCache.project_id == project_id,
                MergeRequestCache.state == state
            ).all()

            if not cached_mrs:
                return None

            # Check if any cache entry is expired
            for mr in cached_mrs:
                if not self.is_cache_valid(mr.last_updated, self.mr_ttl):
                    logger.info(f"MR cache expired for project {project_id}, state {state}")
                    return None

            # All entries are valid, return the data
            result = []
            for mr in cached_mrs:
                try:
                    result.append(json.loads(mr.mr_data))
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode MR data for MR {mr.mr_iid}")
                    return None

            logger.info(f"Returning {len(result)} cached MRs for project {project_id}, state {state}")
            return result

        except Exception as e:
            logger.error(f"Error getting cached MRs: {e}")
            return None

    def cache_merge_requests(self, db, project_id: str, state: str, merge_requests: list):
        """Cache merge requests"""
        try:
            # Clear old cache for this project and state
            db.query(MergeRequestCache).filter(
                MergeRequestCache.project_id == project_id,
                MergeRequestCache.state == state
            ).delete()

            # Cache new data
            for mr in merge_requests:
                cache_entry = MergeRequestCache(
                    mr_iid=mr.get('iid'),
                    state=state,
                    project_id=project_id,
                    mr_data=json.dumps(mr),
                    last_updated=datetime.utcnow()
                )
                db.add(cache_entry)

            db.commit()
            logger.info(f"Cached {len(merge_requests)} MRs for project {project_id}, state {state}")

        except Exception as e:
            logger.error(f"Error caching MRs: {e}")
            db.rollback()

    def get_cached_clickup_task(self, db, task_id: str) -> dict:
        """Get cached ClickUp task if valid"""
        try:
            cached_task = db.query(ClickUpTaskCache).filter(
                ClickUpTaskCache.task_id == task_id
            ).first()

            if not cached_task:
                return None

            if not self.is_cache_valid(cached_task.last_updated, self.clickup_ttl):
                logger.info(f"ClickUp task cache expired for task {task_id}")
                return None

            logger.info(f"Returning cached ClickUp task {task_id}")
            return json.loads(cached_task.task_data)

        except Exception as e:
            logger.error(f"Error getting cached ClickUp task: {e}")
            return None

    def cache_clickup_task(self, db, task_id: str, task_data: dict):
        """Cache ClickUp task"""
        try:
            # Check if task already exists
            cached_task = db.query(ClickUpTaskCache).filter(
                ClickUpTaskCache.task_id == task_id
            ).first()

            if cached_task:
                # Update existing
                cached_task.task_data = json.dumps(task_data)
                cached_task.last_updated = datetime.utcnow()
            else:
                # Create new
                cached_task = ClickUpTaskCache(
                    task_id=task_id,
                    task_data=json.dumps(task_data),
                    last_updated=datetime.utcnow()
                )
                db.add(cached_task)

            db.commit()
            logger.info(f"Cached ClickUp task {task_id}")

        except Exception as e:
            logger.error(f"Error caching ClickUp task: {e}")
            db.rollback()

    def clear_all_cache(self, db):
        """Clear all cache entries"""
        try:
            db.query(MergeRequestCache).delete()
            db.query(ClickUpTaskCache).delete()
            db.commit()
            logger.info("All cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            db.rollback()

    def get_cache_stats(self, db) -> dict:
        """Get cache statistics"""
        try:
            mr_count = db.query(MergeRequestCache).count()
            clickup_count = db.query(ClickUpTaskCache).count()

            # Get oldest and newest entries
            oldest_mr = db.query(MergeRequestCache).order_by(
                MergeRequestCache.last_updated.asc()
            ).first()
            newest_mr = db.query(MergeRequestCache).order_by(
                MergeRequestCache.last_updated.desc()
            ).first()

            return {
                'mr_cache_count': mr_count,
                'clickup_cache_count': clickup_count,
                'oldest_mr_update': oldest_mr.last_updated.isoformat() if oldest_mr else None,
                'newest_mr_update': newest_mr.last_updated.isoformat() if newest_mr else None,
                'mr_ttl_minutes': int(self.mr_ttl.total_seconds() / 60),
                'clickup_ttl_minutes': int(self.clickup_ttl.total_seconds() / 60)
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
