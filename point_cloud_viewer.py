import open3d as o3d

# Load a PLY point cloud
pcd = o3d.io.read_point_cloud("tagged_cloud_20251104_114651.ply")
o3d.visualization.draw_geometries([pcd])