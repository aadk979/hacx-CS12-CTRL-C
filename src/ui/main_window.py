"""Main application window and UI orchestration."""
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
from datetime import datetime
import json
import sys

import config
from src.core.point_cloud_manager import PointCloudManager
from src.core.tag_manager import TagManager
from src.models.tag import Tag
from src.utils.geometry_utils import GeometryUtils
from src.utils.file_manager import FileManager
from src.handlers.mouse_handler import MouseHandler
from src.ui.panels.coordinate_panel import CoordinatePanel
from src.ui.panels.tag_info_panel import TagInfoPanel
from src.ui.panels.photo_panel import PhotoPanel

class MainWindow:
    """Main application window controller."""
    
    def __init__(self):
        self.window = None
        self.scene_widget = None
        self.pcd_manager = PointCloudManager()
        self.tag_manager = TagManager()
        self.selected_tag_id = None
        
        # UI Panels
        self.coord_panel = None
        self.info_panel = None
        self.photo_panel = None
        self.status_label = None
        self.stats_label = None
        self.tag_list = None
    
    def initialize(self):
        """Initialize the application window."""
        app = gui.Application.instance
        app.initialize()
        
        # Load data
        if not self.pcd_manager.load(config.POINT_CLOUD_FILE):
            sys.exit(1)
        self.tag_manager.load()
        
        # Create window
        self.window = app.create_window(
            config.WINDOW_TITLE,
            config.WINDOW_WIDTH,
            config.WINDOW_HEIGHT
        )
        em = self.window.theme.font_size
        
        # Create UI
        main_panel = self._create_main_panel(em)
        self.scene_widget = self._create_scene_widget()
        
        # Layout
        self._setup_layout(main_panel)
        
        # Add existing tags to scene
        self._render_existing_tags()
        
        print("✅ Application ready. Shift+Click to tag points in 3D space.")
    
    def _create_main_panel(self, em: float) -> gui.Vert:
        """Create the main control panel."""
        panel = gui.Vert(0, gui.Margins(em, em, em, em))
        
        # Header
        header = gui.Label("🏷️  Point Cloud Tagger")
        header.text_color = gui.Color(0.2, 0.4, 0.8)
        panel.add_child(header)
        panel.add_fixed(em * 0.5)
        
        # Status
        self.status_label = gui.Label(
            "✨ Ready. Shift+Click to pick points on the model."
        )
        self.status_label.text_color = gui.Color(0.3, 0.6, 0.9)
        panel.add_child(self.status_label)
        panel.add_fixed(em * 0.75)
        
        # Panels
        self.coord_panel = CoordinatePanel(em)
        panel.add_child(self.coord_panel.get_widget())
        panel.add_fixed(em * 0.5)
        
        self.info_panel = TagInfoPanel(em)
        panel.add_child(self.info_panel.get_widget())
        panel.add_fixed(em * 0.5)
        
        self.photo_panel = PhotoPanel(em, self._update_status)
        self.photo_panel.set_window(self.window)
        panel.add_child(self.photo_panel.get_widget())
        panel.add_fixed(em)
        
        # Action buttons
        button_row = gui.Horiz(em * 0.5)
        save_btn = gui.Button("💾 Save Tag")
        save_btn.set_on_clicked(self._on_save_tag)
        button_row.add_child(save_btn)
        
        delete_btn = gui.Button("🗑️ Delete")
        delete_btn.set_on_clicked(self._on_delete_tag)
        button_row.add_child(delete_btn)
        panel.add_child(button_row)
        panel.add_fixed(em * 0.5)
        
        # Export button
        export_btn = gui.Button("📦 Export Cloud + Tags")
        export_btn.set_on_clicked(self._on_export)
        panel.add_child(export_btn)
        panel.add_fixed(em)
        
        # Tag list
        list_section = gui.CollapsableVert(
            "📋 Existing Tags",
            em * 0.5,
            gui.Margins(em * 0.5, 0, 0, 0)
        )
        self.tag_list = gui.ListView()
        self.tag_list.set_on_selection_changed(self._on_tag_selected)
        self._update_tag_list()
        list_section.add_child(self.tag_list)
        panel.add_child(list_section)
        
        # Stats
        panel.add_fixed(em * 0.5)
        self.stats_label = gui.Label(
            f"📊 Total Tags: {len(self.tag_manager.tags)}"
        )
        self.stats_label.text_color = gui.Color(0.4, 0.4, 0.4)
        panel.add_child(self.stats_label)
        
        # Help
        panel.add_fixed(em * 0.5)
        help_section = gui.CollapsableVert(
            "💡 Help",
            em * 0.5,
            gui.Margins(em * 0.5, 0, 0, 0)
        )
        help_text = (
            "• Shift+Click: Pick 3D point\n"
            "• Upload: Add multiple photos\n"
            "• Save: Store tag permanently\n"
            "• Export: Create PLY with tags"
        )
        help_label = gui.Label(help_text)
        help_label.text_color = gui.Color(0.5, 0.5, 0.5)
        help_section.add_child(help_label)
        panel.add_child(help_section)
        
        panel.add_stretch()
        
        return panel
    
    def _create_scene_widget(self):
        """Create and configure the 3D scene widget."""
        widget = gui.SceneWidget()
        widget.scene = rendering.Open3DScene(self.window.renderer)
        widget.scene.set_background(config.BACKGROUND_COLOR)
        
        # Setup mouse handler
        mouse_handler = MouseHandler(
            widget,
            self.coord_panel.set_coordinates,
            self._update_status,
            self._show_temp_marker
        )
        widget.set_on_mouse(mouse_handler.handle_mouse_event)
        
        # Add point cloud
        mat = rendering.MaterialRecord()
        mat.shader = "defaultUnlit"
        mat.point_size = config.POINT_SIZE
        widget.scene.add_geometry(
            "cloud",
            self.pcd_manager.get_point_cloud(),
            mat
        )
        
        # Setup camera
        pcd = self.pcd_manager.get_point_cloud()
        bounds = pcd.get_axis_aligned_bounding_box()
        widget.setup_camera(60, bounds, bounds.get_center())
        
        # Lighting
        widget.scene.scene.set_sun_light([0.577, -0.577, -0.577], [1, 1, 1], 75000)
        widget.scene.scene.enable_sun_light(True)
        
        return widget
    
    def _setup_layout(self, main_panel):
        """Configure window layout."""
        def on_layout(layout_context):
            content_rect = self.window.content_rect
            main_panel.frame = gui.Rect(
                content_rect.width - config.PANEL_WIDTH, 0,
                config.PANEL_WIDTH, content_rect.height
            )
            self.scene_widget.frame = gui.Rect(
                0, 0,
                content_rect.width - config.PANEL_WIDTH,
                content_rect.height
            )
        
        self.window.set_on_layout(on_layout)
        self.window.add_child(self.scene_widget)
        self.window.add_child(main_panel)
    
    def _update_status(self, message: str, color: list):
        """Update status label."""
        self.status_label.text = message
        self.status_label.text_color = gui.Color(*color)
    
    def _show_temp_marker(self, world_point):
        """Show temporary marker at selected point."""
        temp_sphere, _ = GeometryUtils.create_marker(
            world_point,
            config.TEMP_MARKER_COLOR,
            config.TEMP_MARKER_RADIUS
        )
        
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        mat.base_color = config.TEMP_MARKER_COLOR + [1]
        
        if self.scene_widget.scene.has_geometry("temp_marker"):
            self.scene_widget.scene.remove_geometry("temp_marker")
        
        self.scene_widget.scene.add_geometry("temp_marker", temp_sphere, mat)
    
    def _on_save_tag(self):
        """Handle save tag action."""
        try:
            title = self.info_panel.get_title()
            description = self.info_panel.get_description()
            coords_text = self.coord_panel.get_coordinates()
            
            if not title or not description:
                self._update_status(
                    "❌ Title & description required",
                    [0.9, 0.2, 0.2]
                )
                return
            
            coords = [float(x) for x in coords_text.split(",")]
            if len(coords) != 3:
                raise ValueError("Need 3 coordinates")
            
            # Get photos
            photo_paths = self.photo_panel.get_photos()
            
            # Create tag
            tag_color = GeometryUtils.generate_random_color()
            tag = Tag(
                title=title,
                description=description,
                coords=coords,
                color=tag_color
            )
            
            # Save photos
            saved_photos = FileManager.save_tag_photos(tag.id, photo_paths)
            tag.photos = saved_photos
            
            # Add to manager
            self.tag_manager.add_tag(tag)
            
            # Add to scene
            marker, _ = GeometryUtils.create_marker(coords, tag_color)
            mat = rendering.MaterialRecord()
            mat.shader = "defaultLit"
            mat.base_color = tag_color + [1]
            self.scene_widget.scene.add_geometry(f"tag_{tag.id}", marker, mat)
            
            # Remove temp marker
            if self.scene_widget.scene.has_geometry("temp_marker"):
                self.scene_widget.scene.remove_geometry("temp_marker")
            
            # Update UI
            self._update_status(
                f"✅ Saved '{title}' with {len(saved_photos)} photo(s)",
                [0.2, 0.8, 0.3]
            )
            self.stats_label.text = f"📊 Total Tags: {len(self.tag_manager.tags)}"
            
            # Clear inputs
            self.info_panel.clear()
            self.coord_panel.set_coordinates("0.000, 0.000, 0.000")
            self.photo_panel.clear()
            self._update_tag_list()
            
        except Exception as e:
            self._update_status(f"❌ Error: {e}", [0.9, 0.2, 0.2])
    
    def _on_delete_tag(self):
        """Handle delete tag action."""
        if not self.selected_tag_id:
            self._update_status("⚠️ No tag selected", [0.9, 0.5, 0.2])
            return
        
        tag = self.tag_manager.get_tag_by_id(self.selected_tag_id)
        if not tag:
            return
        
        # Delete photos
        FileManager.delete_tag_photos(self.selected_tag_id)
        
        # Remove from scene
        if self.scene_widget.scene.has_geometry(f"tag_{self.selected_tag_id}"):
            self.scene_widget.scene.remove_geometry(f"tag_{self.selected_tag_id}")
        
        # Remove from manager
        self.tag_manager.remove_tag(self.selected_tag_id)
        
        self._update_status(f"🗑️ Deleted '{tag.title}'", [0.8, 0.4, 0.2])
        self.stats_label.text = f"📊 Total Tags: {len(self.tag_manager.tags)}"
        self.selected_tag_id = None
        self._update_tag_list()
    
    def _on_export(self):
        """Handle export action."""
        try:
            if not self.tag_manager.tags:
                self._update_status("⚠️ No tags to export", [0.9, 0.5, 0.2])
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"tagged_cloud_{timestamp}.ply"
            
            # Export point cloud
            tags_dict = [tag.to_dict() for tag in self.tag_manager.tags]
            success = self.pcd_manager.export_with_tags(
                tags_dict,
                output_filename
            )
            
            if success:
                # Save metadata
                metadata_filename = f"tagged_cloud_{timestamp}_metadata.json"
                pcd = self.pcd_manager.get_point_cloud()
                metadata = {
                    "original_file": str(config.POINT_CLOUD_FILE),
                    "export_date": timestamp,
                    "original_points": len(pcd.points),
                    "num_tags": len(self.tag_manager.tags),
                    "tags": tags_dict
                }
                
                with open(metadata_filename, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=4)
                
                self._update_status(
                    f"✅ Exported: {output_filename}",
                    [0.2, 0.8, 0.3]
                )
                print(f"✅ Exported point cloud with {len(self.tag_manager.tags)} tags")
                print(f"   📄 {output_filename}")
                print(f"   📄 {metadata_filename}")
            else:
                raise Exception("Failed to write file")
                
        except Exception as e:
            self._update_status(f"❌ Export failed: {e}", [0.9, 0.2, 0.2])
    
    def _on_tag_selected(self, new_val, is_double_click):
        """Handle tag selection from list."""
        if 0 <= new_val < len(self.tag_manager.tags):
            tag = self.tag_manager.tags[new_val]
            self.selected_tag_id = tag.id
            self._update_status(f"🔍 Selected: {tag.title}", [0.3, 0.6, 0.9])
    
    def _update_tag_list(self):
        """Update the tag list widget."""
        tag_items = [
            f"{t.title} - ({', '.join(f'{c:.2f}' for c in t.coords)})"
            for t in self.tag_manager.tags
        ]
        self.tag_list.set_items(tag_items)
    
    def _render_existing_tags(self):
        """Add existing tags to the scene."""
        for tag in self.tag_manager.tags:
            tag_dict = tag.to_dict()
            marker, _ = GeometryUtils.create_marker(
                tag_dict["coords"],
                tag_dict.get("color")
            )
            mat = rendering.MaterialRecord()
            mat.shader = "defaultLit"
            mat.base_color = tag_dict.get("color", [1, 0, 0]) + [1]
            self.scene_widget.scene.add_geometry(f"tag_{tag.id}", marker, mat)
    
    def run(self):
        """Run the application."""
        gui.Application.instance.run()
