"""
Full open-source pipeline for:
    - Loading a .ply point cloud
    - Generating a top-down 2D floor plan projection
    - Extracting individual walls as 2D "sheets"
    - Computing automatic measurements
    - Exporting each wall/ceiling as separate files

FIXED: Coordinates now start at (0, 0) for easy viewing
FIXED: Added .buffer(0) to clean polygons and prevent TopologyException
"""

import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon, MultiPoint, GeometryCollection
from shapely.ops import unary_union
from shapely import affinity
from skimage import measure
import os

# ======== STEP 1: LOAD POINT CLOUD ========

PLY_FILE = "../tagged_cloud_20251104_114651.ply"
pcd = o3d.io.read_point_cloud(PLY_FILE)
print(f"[+] Loaded point cloud with {np.asarray(pcd.points).shape[0]} points")

points = np.asarray(pcd.points)

# ======== NORMALIZE COORDINATES TO START AT (0,0,0) ========
x_min_orig, y_min_orig, z_min_orig = points.min(axis=0)
points_normalized = points - np.array([x_min_orig, y_min_orig, z_min_orig])
print(f"[+] Normalized coordinates - Origin offset: X={x_min_orig:.2f}, Y={y_min_orig:.2f}, Z={z_min_orig:.2f}")

# Use normalized points for all subsequent operations
points = points_normalized

# ======== STEP 2: AUTO-ALIGN USING PCA ========
# Align the point cloud to principal axes to remove tilt
floor_threshold_temp = np.percentile(points[:, 2], 2) + 0.05
floor_points_temp = points[points[:, 2] < floor_threshold_temp]
floor_xy_temp = floor_points_temp[:, :2]

# Compute PCA on floor points (XY plane)
mean_xy = floor_xy_temp.mean(axis=0)
centered = floor_xy_temp - mean_xy
cov_matrix = np.cov(centered.T)
eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)

# Sort eigenvectors by eigenvalues (largest first)
idx = eigenvalues.argsort()[::-1]
eigenvectors = eigenvectors[:, idx]

# Ensure right-handed coordinate system (determinant should be positive)
if np.linalg.det(eigenvectors) < 0:
    eigenvectors[:, 1] = -eigenvectors[:, 1]

# Create rotation matrix to align to axes
rotation_matrix_2d = eigenvectors.T

# Apply rotation to all points (XY plane only)
points_xy = points[:, :2]
points_xy_centered = points_xy - mean_xy
points_xy_rotated = points_xy_centered @ rotation_matrix_2d.T
points[:, :2] = points_xy_rotated

# Recenter after rotation to start at (0,0)
xy_min = points[:, :2].min(axis=0)
points[:, :2] = points[:, :2] - xy_min

print(f"[+] Applied PCA alignment - removed tilt from floor plan")

# ======== STEP 3: ORIENT AND SLICE TO FLOOR PLANE ========
# Align Z as height; we assume floor is near the lowest z-values
floor_threshold = np.percentile(points[:, 2], 2) + 0.05  # 5cm above lowest point
floor_points = points[points[:, 2] < floor_threshold]

# 2D projection (x,y)
floor_xy = floor_points[:, :2]

# ======== STEP 3: BUILD FLOOR PLAN OUTLINE ========
# Convert XY points into density grid
resolution = 0.02  # 2 cm/pixel
x_min, y_min = floor_xy.min(axis=0)
x_max, y_max = floor_xy.max(axis=0)

x_bins = np.arange(x_min, x_max, resolution)
y_bins = np.arange(y_min, y_max, resolution)

grid, _, _ = np.histogram2d(
    floor_xy[:, 0], floor_xy[:, 1],
    bins=(x_bins, y_bins)
)

# Threshold and contour extraction
binary = grid.T > 1  # basic occupancy threshold
contours = measure.find_contours(binary.astype(float), 0.5)

polygons = []
for contour in contours:
    px = contour[:, 1] * resolution + x_min
    py = contour[:, 0] * resolution + y_min
    poly = Polygon(np.column_stack((px, py)))
    if poly.area > 0.05:  # filter tiny noise
        # **FIX APPLIED HERE**: Clean the polygon to prevent errors
        clean_poly = poly.buffer(0)
        if not clean_poly.is_empty:
            polygons.append(clean_poly)

# --- Safe floor extraction ---
if polygons:
    merged_floor = unary_union(polygons)
else:
    print("[!] No valid floor polygons found — using convex hull fallback")
    floor_threshold = np.percentile(points[:, 2], 5) + 0.05
    floor_points = points[points[:, 2] < floor_threshold]
    floor_xy = floor_points[:, :2]
    merged_floor = MultiPoint(floor_xy).convex_hull

# ======== STEP 4: EXTRACT WALL PROJECTIONS ========
# Simple approach: slice by Z intervals
z_values = points[:, 2]
z_min, z_max = z_values.min(), z_values.max()

wall_slices = []
n_slices = 4  # number of vertical slices
slice_thickness = (z_max - z_min) / n_slices

for i in range(n_slices):
    z_low = z_min + i * slice_thickness
    z_high = z_low + slice_thickness
    slice_points = points[(z_values >= z_low) & (z_values < z_high)]
    if len(slice_points) < 500:
        continue
    wall_xy = slice_points[:, :2]
    grid, _, _ = np.histogram2d(
        wall_xy[:, 0], wall_xy[:, 1],
        bins=(x_bins, y_bins)
    )
    binary = grid.T > 1
    contours = measure.find_contours(binary.astype(float), 0.5)
    wall_polys = []
    for contour in contours:
        px = contour[:, 1] * resolution + x_min
        py = contour[:, 0] * resolution + y_min
        poly = Polygon(np.column_stack((px, py)))
        if poly.area > 0.05:
            # **FIX APPLIED HERE**: Clean each polygon before adding to the list
            clean_poly = poly.buffer(0)
            if not clean_poly.is_empty:
                 wall_polys.append(clean_poly)
    if wall_polys:
        # This line is now safe from the TopologyException
        wall_slices.append((i, unary_union(wall_polys), slice_points))

print(f"[+] Extracted {len(wall_slices)} wall slices")


# ======== STEP 5: AUTO MEASUREMENTS ========

def measure_polygon(poly):
    bounds = poly.bounds
    width = abs(bounds[2] - bounds[0])
    height = abs(bounds[3] - bounds[1])
    area = getattr(poly, "area", 0.0)
    return width, height, area


floor_w, floor_h, floor_area = measure_polygon(merged_floor)
print(f"    Floor width: {floor_w:.2f} m, height: {floor_h:.2f} m, area: {floor_area:.2f} m²")

for i, wall_poly, _ in wall_slices:
    w, h, a = measure_polygon(wall_poly)
    print(f"    Wall slice {i + 1}: {w:.2f} m x {h:.2f} m (area {a:.2f} m²)")


# ======== STEP 6: VISUALIZE AND EXPORT SEPARATELY ========

def draw_polygon(ax, poly, color="lightblue"):
    """Recursively draw any Shapely geometry type"""
    if isinstance(poly, GeometryCollection):
        for geom in poly.geoms:
            draw_polygon(ax, geom, color=color)
        return
    if isinstance(poly, MultiPolygon):
        for p in poly.geoms:
            x, y = p.exterior.xy
            ax.fill(x, y, color=color, alpha=0.5)
    elif isinstance(poly, Polygon):
        x, y = poly.exterior.xy
        ax.fill(x, y, color=color, alpha=0.5)


os.makedirs("exports", exist_ok=True)

# Export floor separately
fig, ax = plt.subplots(figsize=(10, 10))
draw_polygon(ax, merged_floor, color="skyblue")
ax.set_title("Floor Plan (2D Projection) - Origin at (0,0)", fontsize=14, fontweight='bold')
ax.set_aspect('equal', 'box')
ax.set_xlim(left=0)  # Force X axis to start at 0
ax.set_ylim(bottom=0)  # Force Y axis to start at 0
ax.grid(True, alpha=0.3, linewidth=0.5)
plt.xlabel("X (m)", fontsize=12)
plt.ylabel("Y (m)", fontsize=12)
plt.tight_layout()
plt.savefig("exports/floor_plan.png", dpi=300)
print("[+] Exported floor plan to exports/floor_plan.png")
plt.close()

# Export floor point cloud
o3d.io.write_point_cloud(
    "exports/floor_points.ply",
    o3d.geometry.PointCloud(o3d.utility.Vector3dVector(floor_points))
)
print("[+] Exported floor points to exports/floor_points.ply")

# Export each wall slice separately
colors = ["#FFB347", "#FF6961", "#77DD77", "#AEC6CF"]
for idx, (i, wall_poly, slice_points) in enumerate(wall_slices):
    # Create individual visualization
    fig, ax = plt.subplots(figsize=(10, 10))
    draw_polygon(ax, wall_poly, color=colors[idx % len(colors)])
    ax.set_title(f"Wall Slice {i + 1} (2D Projection) - Origin at (0,0)", fontsize=14, fontweight='bold')
    ax.set_aspect('equal', 'box')
    ax.set_xlim(left=0)  # Force X axis to start at 0
    ax.set_ylim(bottom=0)  # Force Y axis to start at 0
    ax.grid(True, alpha=0.3, linewidth=0.5)
    plt.xlabel("X (m)", fontsize=12)
    plt.ylabel("Y (m)", fontsize=12)
    plt.tight_layout()

    # Save individual PNG
    filename = f"exports/wall_slice_{i + 1}.png"
    plt.savefig(filename, dpi=300)
    print(f"[+] Exported wall slice {i + 1} to {filename}")
    plt.close()

    # Save individual point cloud
    ply_filename = f"exports/wall_slice_{i + 1}_points.ply"
    o3d.io.write_point_cloud(
        ply_filename,
        o3d.geometry.PointCloud(o3d.utility.Vector3dVector(slice_points))
    )
    print(f"[+] Exported wall slice {i + 1} points to {ply_filename}")

# Optional: Create a combined overview for reference
fig, ax = plt.subplots(figsize=(10, 10))
draw_polygon(ax, merged_floor, color="skyblue")
for idx, (i, wall_poly, _) in enumerate(wall_slices):
    draw_polygon(ax, wall_poly, color=colors[idx % len(colors)])
ax.set_title("Combined Overview: Floor + All Wall Slices - Origin at (0,0)", fontsize=14, fontweight='bold')
ax.set_aspect('equal', 'box')
ax.set_xlim(left=0)  # Force X axis to start at 0
ax.set_ylim(bottom=0)  # Force Y axis to start at 0
ax.grid(True, alpha=0.3, linewidth=0.5)
plt.xlabel("X (m)", fontsize=12)
plt.ylabel("Y (m)", fontsize=12)
plt.tight_layout()
plt.savefig("exports/combined_overview.png", dpi=300)
print("[+] Exported combined overview to exports/combined_overview.png")
plt.show()

print("\n[✓] Export complete! Check the 'exports' folder for all files.")
print(f"[✓] All coordinates normalized - Floor plan starts at (0, 0)")