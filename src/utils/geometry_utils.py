"""Geometry creation and manipulation utilities."""
import open3d as o3d
import numpy as np
import random
from typing import List, Tuple

class GeometryUtils:
    """Utility functions for 3D geometry operations."""
    
    @staticmethod
    def create_marker(coords: List[float], color: List[float] = None, 
                     radius: float = 0.15) -> Tuple[o3d.geometry.TriangleMesh, List[float]]:
        """Create a colored sphere marker at given coordinates."""
        if color is None:
            color = [
                random.random() * 0.5 + 0.5,
                random.random() * 0.5 + 0.5,
                random.random() * 0.5 + 0.5
            ]
        
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius=radius)
        sphere.paint_uniform_color(color)
        sphere.compute_vertex_normals()
        sphere.translate(coords)
        return sphere, color
    
    @staticmethod
    def paint_point_cloud(pcd: o3d.geometry.PointCloud, 
                         color: List[float]) -> None:
        """Paint all points in a point cloud with the given color."""
        colors = np.tile(color, (len(pcd.points), 1))
        pcd.colors = o3d.utility.Vector3dVector(colors)
    
    @staticmethod
    def generate_random_color() -> List[float]:
        """Generate a random bright color."""
        return [
            random.random() * 0.4 + 0.5,
            random.random() * 0.4 + 0.5,
            random.random() * 0.4 + 0.5
        ]
