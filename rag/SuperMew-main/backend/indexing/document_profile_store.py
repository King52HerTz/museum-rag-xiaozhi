from datetime import datetime
from typing import List

from backend.db.models import DocumentProfile
from backend.infra.database import SessionLocal


def _normalize_profile_value(value: str | None) -> str:
    return str(value or "").strip()


class DocumentProfileStore:
    """文档业务画像存储，用于结构化检索过滤。"""

    def upsert_profile(
        self,
        *,
        filename: str,
        file_type: str = "",
        museum: str = "",
        exhibition: str = "",
        exhibit_id: str = "",
        era: str = "",
        category: str = "",
    ) -> None:
        key = _normalize_profile_value(filename)
        if not key:
            return

        payload = {
            "file_type": _normalize_profile_value(file_type),
            "museum": _normalize_profile_value(museum),
            "exhibition": _normalize_profile_value(exhibition),
            "exhibit_id": _normalize_profile_value(exhibit_id),
            "era": _normalize_profile_value(era),
            "category": _normalize_profile_value(category),
            "updated_at": datetime.utcnow(),
        }

        db = SessionLocal()
        try:
            profile = db.query(DocumentProfile).filter(DocumentProfile.filename == key).first()
            if profile:
                for field, value in payload.items():
                    setattr(profile, field, value)
            else:
                db.add(DocumentProfile(filename=key, **payload))
            db.commit()
        finally:
            db.close()

    def delete_by_filename(self, filename: str) -> int:
        key = _normalize_profile_value(filename)
        if not key:
            return 0

        db = SessionLocal()
        try:
            deleted = db.query(DocumentProfile).filter(DocumentProfile.filename == key).delete(synchronize_session=False)
            db.commit()
            return int(deleted or 0)
        finally:
            db.close()

    def get_profile_map(self, filenames: List[str]) -> dict[str, dict]:
        keys = [item.strip() for item in filenames if str(item or "").strip()]
        if not keys:
            return {}

        db = SessionLocal()
        try:
            rows = db.query(DocumentProfile).filter(DocumentProfile.filename.in_(keys)).all()
            return {
                row.filename: {
                    "museum": row.museum,
                    "exhibition": row.exhibition,
                    "exhibit_id": row.exhibit_id,
                    "era": row.era,
                    "category": row.category,
                }
                for row in rows
            }
        finally:
            db.close()

    def find_filenames(
        self,
        *,
        museum: str = "",
        exhibition: str = "",
        exhibit_id: str = "",
        era: str = "",
        category: str = "",
    ) -> list[str]:
        filters = {
            "museum": _normalize_profile_value(museum),
            "exhibition": _normalize_profile_value(exhibition),
            "exhibit_id": _normalize_profile_value(exhibit_id),
            "era": _normalize_profile_value(era),
            "category": _normalize_profile_value(category),
        }
        active_filters = {key: value for key, value in filters.items() if value}
        if not active_filters:
            return []

        db = SessionLocal()
        try:
            query = db.query(DocumentProfile.filename)
            if active_filters.get("museum"):
                query = query.filter(DocumentProfile.museum == active_filters["museum"])
            if active_filters.get("exhibition"):
                query = query.filter(DocumentProfile.exhibition == active_filters["exhibition"])
            if active_filters.get("exhibit_id"):
                query = query.filter(DocumentProfile.exhibit_id == active_filters["exhibit_id"])
            if active_filters.get("era"):
                query = query.filter(DocumentProfile.era == active_filters["era"])
            if active_filters.get("category"):
                query = query.filter(DocumentProfile.category == active_filters["category"])
            return [row[0] for row in query.all() if row and row[0]]
        finally:
            db.close()
