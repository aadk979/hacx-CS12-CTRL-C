"""Point cloud loading and management."""
import open3d as o3d
from pathlib import Path
from typing import Optional

class PointCloudManager:
    """Manages point cloud loading and operations."""
    
    def __init__(self):
        self.pcd: Optional[o3d.geometry.PointCloud] = None
    
    def load(self, path: Path) -> bool:
        """Load point cloud from file."""
        if not path.exists():
            print(f"❌ File not found: {path}")
            return False
        
        try:
            self.pcd = o3d.io.read_point_cloud(str(path))
            if not self.pcd.has_points():
                print("❌ Empty point cloud.")
                return False
            print(f"✅ Loaded {len(self.pcd.points):,} points.")
            return True
        except Exception as e:
            print(f"❌ Error loading point cloud: {e}")
            return False
    
    def get_point_cloud(self) -> Optional[o3d.geometry.PointCloud]:
        """Get the loaded point cloud."""
        return self.pcd
    
    def export_with_tags(self, tags: list, output_path: Path) -> bool:
        """Export point cloud with tag markers embedded."""
        if not self.pcd:
            return False
        
        try:
            from src.utils.geometry_utils import GeometryUtils
            
            combined_cloud = o3d.geometry.PointCloud(self.pcd)
            
            for tag in tags:
                marker_sphere = o3d.geometry.TriangleMesh.create_sphere(
                    radius=0.15
                )
                marker_sphere.translate(tag["coords"])
                marker_pcd = marker_sphere.sample_points_uniformly(
                    number_of_points=500
                )
                
                tag_color = tag.get("color", [1.0, 0.0, 0.0])
                GeometryUtils.paint_point_cloud(marker_pcd, tag_color)
                combined_cloud += marker_pcd
            
            return o3d.io.write_point_cloud(str(output_path), combined_cloud)
        except Exception as e:
            print(f"❌ Export error: {e}")
            return False
