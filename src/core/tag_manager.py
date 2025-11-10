"""Tag storage and management operations."""
import json
from pathlib import Path
from typing import List
from src.models.tag import Tag
import config

class TagManager:
    """Manages tag persistence and operations."""
    
    def __init__(self, storage_path: Path = config.TAGS_FILE):
        self.storage_path = storage_path
        self.tags: List[Tag] = []
    
    def load(self) -> List[Tag]:
        """Load tags from JSON file."""
        if not self.storage_path.exists():
            return []
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.tags = [Tag.from_dict(tag_dict) for tag_dict in data]
                return self.tags
        except Exception as e:
            print(f"❌ Error loading tags: {e}")
            return []
    
    def save(self) -> bool:
        """Save tags to JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    [tag.to_dict() for tag in self.tags],
                    f,
                    indent=4
                )
            print("✅ Tags saved.")
            return True
        except Exception as e:
            print(f"❌ Failed to save tags: {e}")
            return False
    
    def add_tag(self, tag: Tag) -> None:
        """Add a new tag."""
        self.tags.append(tag)
        self.save()
    
    def remove_tag(self, tag_id: str) -> bool:
        """Remove tag by ID."""
        original_length = len(self.tags)
        self.tags = [t for t in self.tags if t.id != tag_id]
        
        if len(self.tags) < original_length:
            self.save()
            return True
        return False
    
    def get_tag_by_id(self, tag_id: str) -> Tag:
        """Retrieve tag by ID."""
        return next((t for t in self.tags if t.id == tag_id), None)
