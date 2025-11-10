"""Application configuration and constants."""
from pathlib import Path

# File paths
TAGS_FILE = Path("data/tags.json")
POINT_CLOUD_FILE = Path("./CS12-MockWarehouse.ply")
PHOTOS_DIR = Path("data/tag_photos")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# UI Constants
WINDOW_TITLE = "Point Cloud Annotation Studio"
WINDOW_WIDTH = 1800
WINDOW_HEIGHT = 1000
PANEL_WIDTH = 450

# Marker settings
MARKER_RADIUS = 0.15
TEMP_MARKER_RADIUS = 0.12
POINT_SIZE = 2

# Colors
BACKGROUND_COLOR = [0.12, 0.14, 0.18, 1]
TEMP_MARKER_COLOR = [1, 0.843, 0]
