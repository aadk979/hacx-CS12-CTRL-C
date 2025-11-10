"""Tag data model."""
import uuid
from dataclasses import dataclass, field
from typing import List

@dataclass
class Tag:
    """Represents a 3D annotation tag."""
    title: str
    description: str
    coords: List[float]
    photos: List[str] = field(default_factory=list)
    color: List[float] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> dict:
        """Convert tag to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "coords": self.coords,
            "title": self.title,
            "description": self.description,
            "photos": self.photos,
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tag':
        """Create Tag instance from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data["title"],
            description=data["description"],
            coords=data["coords"],
            photos=data.get("photos", []),
            color=data.get("color", [])
        )
