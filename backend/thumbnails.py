"""
StarPrint Thumbnail Generator
Creates thumbnail images from GLB models using 2D projection (no OpenGL required)
"""

import trimesh
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
import io

# Thumbnail settings
THUMBNAIL_SIZE = (256, 256)
THUMBNAIL_DIR = Path(__file__).parent.parent / "cache"  # Same as CACHE_DIR in main.py

def ensure_thumbnail_dir():
    """Create thumbnail directory if it doesn't exist"""
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

def get_thumbnail_path(guid: str) -> Path:
    """Get the path where a thumbnail would be stored"""
    return THUMBNAIL_DIR / f"{guid}.png"

def thumbnail_exists(guid: str) -> bool:
    """Check if thumbnail already exists in cache"""
    return get_thumbnail_path(guid).exists()

def generate_thumbnail(glb_path: Path, guid: str) -> Path | None:
    """
    Generate a PNG thumbnail from a GLB file using 2D silhouette projection.
    
    Args:
        glb_path: Path to the GLB file
        guid: Unique identifier for caching
        
    Returns:
        Path to generated thumbnail, or None if failed
    """
    ensure_thumbnail_dir()
    thumbnail_path = get_thumbnail_path(guid)
    
    try:
        # Load the GLB file
        scene = trimesh.load(str(glb_path), force='scene')
        
        if scene is None:
            print(f"[Thumbnail] Could not load: {glb_path}")
            return create_placeholder_thumbnail(guid, "Load Error")
        
        # Get combined mesh from scene
        if isinstance(scene, trimesh.Trimesh):
            mesh = scene
        elif hasattr(scene, 'geometry') and len(scene.geometry) > 0:
            # Combine all meshes in scene
            meshes = list(scene.geometry.values())
            if len(meshes) == 1:
                mesh = meshes[0]
            else:
                mesh = trimesh.util.concatenate(meshes)
        else:
            print(f"[Thumbnail] Empty scene: {glb_path}")
            return create_placeholder_thumbnail(guid, "Empty")
        
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
            return create_placeholder_thumbnail(guid, "No Mesh")
        
        # Create the silhouette render
        img = render_mesh_silhouette(mesh)
        img.save(thumbnail_path, 'PNG')
        print(f"[Thumbnail] Rendered: {thumbnail_path.name} ({thumbnail_path.stat().st_size} bytes)")
        return thumbnail_path
            
    except Exception as e:
        print(f"[Thumbnail] Generation failed for {guid}: {e}")
        import traceback
        traceback.print_exc()
        return create_placeholder_thumbnail(guid, "Error")

def render_mesh_silhouette(mesh: trimesh.Trimesh) -> Image.Image:
    """
    Render a mesh as a silhouette by projecting faces to 2D.
    Creates a nice visualization without requiring OpenGL.
    """
    width, height = THUMBNAIL_SIZE
    padding = 20
    
    # Create dark background
    img = Image.new('RGB', (width, height), color=(15, 23, 42))  # Slate-900
    draw = ImageDraw.Draw(img)
    
    # Get mesh vertices and faces
    vertices = mesh.vertices.copy()
    faces = mesh.faces
    
    if len(vertices) == 0:
        return img
    
    # Center the mesh
    centroid = vertices.mean(axis=0)
    vertices -= centroid
    
    # Apply a slight rotation to show 3/4 view (more interesting than front view)
    # Rotate 30 degrees around Y axis
    angle_y = np.radians(30)
    rotation_y = np.array([
        [np.cos(angle_y), 0, np.sin(angle_y)],
        [0, 1, 0],
        [-np.sin(angle_y), 0, np.cos(angle_y)]
    ])
    
    # Rotate -15 degrees around X axis (slight tilt)
    angle_x = np.radians(-15)
    rotation_x = np.array([
        [1, 0, 0],
        [0, np.cos(angle_x), -np.sin(angle_x)],
        [0, np.sin(angle_x), np.cos(angle_x)]
    ])
    
    vertices = vertices @ rotation_y @ rotation_x
    
    # Project to 2D (orthographic projection, XY plane)
    vertices_2d = vertices[:, :2]  # Just X and Y
    
    # Scale to fit in image with padding
    mins = vertices_2d.min(axis=0)
    maxs = vertices_2d.max(axis=0)
    ranges = maxs - mins
    
    if ranges.max() == 0:
        return img
    
    # Calculate scale to fit in image
    available_size = min(width, height) - 2 * padding
    scale = available_size / ranges.max()
    
    # Center in image
    center_offset = np.array([width / 2, height / 2])
    mesh_center = (mins + maxs) / 2
    
    # Transform vertices to image coordinates
    # Flip Y axis (image Y is inverted)
    vertices_img = (vertices_2d - mesh_center) * scale * np.array([1, -1]) + center_offset
    
    # Calculate face depths for z-sorting (use average z of each face)
    face_depths = vertices[faces].mean(axis=1)[:, 2]  # Z coordinate
    
    # Sort faces by depth (back to front)
    sorted_indices = np.argsort(face_depths)  # Far to near
    
    # Draw faces with shading based on normal
    face_normals = mesh.face_normals
    light_dir = np.array([0.3, 0.3, 1.0])  # Light coming from camera-ish
    light_dir = light_dir / np.linalg.norm(light_dir)
    
    # Base colors
    base_color = np.array([100, 180, 230])  # Cyan-ish
    ambient = 0.3
    
    for idx in sorted_indices:
        face = faces[idx]
        face_verts = vertices_img[face]
        
        # Get normal for shading
        normal = face_normals[idx]
        diffuse = max(0, np.dot(normal, light_dir))
        brightness = ambient + (1 - ambient) * diffuse
        
        # Calculate face color
        color = tuple(int(c * brightness) for c in base_color)
        
        # Draw filled polygon
        polygon = [(v[0], v[1]) for v in face_verts]
        try:
            draw.polygon(polygon, fill=color, outline=(50, 80, 120))
        except:
            pass  # Skip invalid polygons
    
    return img

def create_placeholder_thumbnail(guid: str, label: str = "") -> Path | None:
    """Create a simple placeholder thumbnail when rendering fails"""
    try:
        thumbnail_path = get_thumbnail_path(guid)
        
        # Create a dark gray image with a cube icon
        img = Image.new('RGB', THUMBNAIL_SIZE, color=(30, 41, 59))  # Slate-800
        draw = ImageDraw.Draw(img)
        
        # Draw a simple cube outline
        cx, cy = THUMBNAIL_SIZE[0] // 2, THUMBNAIL_SIZE[1] // 2
        size = 40
        
        # Front face
        draw.rectangle(
            [cx - size, cy - size//2, cx + size//2, cy + size],
            outline=(100, 116, 139),  # Slate-500
            width=2
        )
        
        # Top edge
        draw.line([(cx - size, cy - size//2), (cx - size//2, cy - size)], fill=(100, 116, 139), width=2)
        draw.line([(cx + size//2, cy - size//2), (cx + size, cy - size)], fill=(100, 116, 139), width=2)
        draw.line([(cx - size//2, cy - size), (cx + size, cy - size)], fill=(100, 116, 139), width=2)
        
        # Right edge
        draw.line([(cx + size//2, cy + size), (cx + size, cy + size//2)], fill=(100, 116, 139), width=2)
        draw.line([(cx + size, cy - size), (cx + size, cy + size//2)], fill=(100, 116, 139), width=2)
        
        # Label
        if label:
            draw.text((cx - 30, cy + size + 10), label, fill=(100, 116, 139))
        
        img.save(thumbnail_path, 'PNG')
        print(f"[Thumbnail] Created placeholder: {thumbnail_path.name}")
        return thumbnail_path
        
    except Exception as e:
        print(f"[Thumbnail] Placeholder creation failed: {e}")
        return None

