"""
Code2Test Intent Database

SQLite-based persistence for inferred intents with JSON storage.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from code2test.core.models import Intent, IntentEvidence


class IntentDatabase:
    """Manages intent storage and retrieval using SQLite."""
    
    def __init__(self, db_path: str):
        """
        Initialize intent database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intents (
                    component_id TEXT PRIMARY KEY,
                    component_path TEXT NOT NULL,
                    intent_text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence TEXT NOT NULL,
                    user_edited INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intents_path 
                ON intents(component_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intents_confidence 
                ON intents(confidence)
            """)
            conn.commit()
    
    def save_intent(self, intent: Intent) -> None:
        """
        Save or update an intent.
        
        Args:
            intent: Intent to save
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO intents 
                (component_id, component_path, intent_text, confidence, 
                 evidence, user_edited, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                intent.component_id,
                intent.component_path,
                intent.intent_text,
                intent.confidence,
                intent.evidence.model_dump_json(),
                1 if intent.user_edited else 0,
                intent.created_at.isoformat(),
                intent.updated_at.isoformat(),
            ))
            conn.commit()
    
    def get_intent(self, component_id: str) -> Optional[Intent]:
        """
        Retrieve intent by component ID.
        
        Args:
            component_id: Unique identifier for the component
            
        Returns:
            Intent if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM intents WHERE component_id = ?",
                (component_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return self._row_to_intent(row)
    
    def get_intents_by_path(self, path_prefix: str) -> List[Intent]:
        """
        Get all intents for components under a path.
        
        Args:
            path_prefix: Path prefix to filter by
            
        Returns:
            List of matching intents
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM intents WHERE component_path LIKE ?",
                (f"{path_prefix}%",)
            )
            return [self._row_to_intent(row) for row in cursor.fetchall()]
    
    def get_low_confidence_intents(self, threshold: float = 0.6) -> List[Intent]:
        """
        Get intents with confidence below threshold.
        
        Args:
            threshold: Confidence threshold
            
        Returns:
            List of low-confidence intents
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM intents WHERE confidence < ? AND user_edited = 0",
                (threshold,)
            )
            return [self._row_to_intent(row) for row in cursor.fetchall()]
    
    def get_all_intents(self) -> List[Intent]:
        """
        Get all stored intents.
        
        Returns:
            List of all intents
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM intents ORDER BY component_path")
            return [self._row_to_intent(row) for row in cursor.fetchall()]

    def get_all_intents_dict(self) -> Dict[str, Intent]:
        """
        Get all stored intents as a dictionary keyed by component_id.
        
        Returns:
            Dictionary of all intents
        """
        intents = self.get_all_intents()
        return {intent.component_id: intent for intent in intents}
    
    def delete_intent(self, component_id: str) -> bool:
        """
        Delete an intent.
        
        Args:
            component_id: Unique identifier for the component
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM intents WHERE component_id = ?",
                (component_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_all(self) -> None:
        """Delete all intents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM intents")
            conn.commit()
    
    def _row_to_intent(self, row: sqlite3.Row) -> Intent:
        """Convert database row to Intent model."""
        evidence_data = json.loads(row["evidence"])
        return Intent(
            component_id=row["component_id"],
            component_path=row["component_path"],
            intent_text=row["intent_text"],
            confidence=row["confidence"],
            evidence=IntentEvidence(**evidence_data),
            user_edited=bool(row["user_edited"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM intents").fetchone()[0]
            user_edited = conn.execute(
                "SELECT COUNT(*) FROM intents WHERE user_edited = 1"
            ).fetchone()[0]
            low_confidence = conn.execute(
                "SELECT COUNT(*) FROM intents WHERE confidence < 0.6"
            ).fetchone()[0]
            avg_confidence = conn.execute(
                "SELECT AVG(confidence) FROM intents"
            ).fetchone()[0] or 0.0
            
            return {
                "total_intents": total,
                "user_edited": user_edited,
                "low_confidence": low_confidence,
                "avg_confidence": round(avg_confidence, 2),
            }
