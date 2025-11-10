"""File management utilities for photo handling."""
import shutil
from pathlib import Path
from typing import List
import config

class FileManager:
    """Manages file operations for tag photos."""
    
    @staticmethod
    def save_tag_photos(tag_id: str, photo_paths: List[str]) -> List[str]:
        """Copy photos to tag directory and return saved paths."""
        tag_photo_dir = config.PHOTOS_DIR / tag_id
        tag_photo_dir.mkdir(parents=True, exist_ok=True)
        saved_photos = []
        
        for idx, photo_path in enumerate(photo_paths):
            ext = Path(photo_path).suffix
            dest_path = tag_photo_dir / f"photo_{idx}{ext}"
            shutil.copy2(photo_path, dest_path)
            saved_photos.append(str(dest_path))
        
        return saved_photos
    
    @staticmethod
    def delete_tag_photos(tag_id: str) -> bool:
        """Delete all photos associated with a tag."""
        tag_photo_dir = config.PHOTOS_DIR / tag_id
        if tag_photo_dir.exists():
            try:
                shutil.rmtree(tag_photo_dir)
                return True
            except Exception as e:
                print(f"❌ Error deleting photos: {e}")
                return False
        return True
