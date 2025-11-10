"""Mouse event handling for 3D point picking."""
import open3d.visualization.gui as gui
import numpy as np

class MouseHandler:
    """Handles mouse events for 3D scene interaction."""
    
    def __init__(self, scene_widget, coord_callback, status_callback, 
                 marker_callback):
        self.scene_widget = scene_widget
        self.coord_callback = coord_callback
        self.status_callback = status_callback
        self.marker_callback = marker_callback
    
    def handle_mouse_event(self, event):
        """Process mouse events for Shift+Click picking."""
        if event.type == gui.MouseEvent.Type.BUTTON_DOWN:
            if event.is_modifier_down(gui.KeyModifier.SHIFT):
                self._handle_shift_click(event.x, event.y)
                return gui.Widget.EventCallbackResult.HANDLED
        
        return gui.Widget.EventCallbackResult.IGNORED
    
    def _handle_shift_click(self, x: int, y: int):
        """Handle Shift+Click to pick 3D point."""
        def depth_callback(depth_image):
            depth = np.asarray(depth_image)
            if y < depth.shape[0] and x < depth.shape[1]:
                depth_value = depth[y, x]
                if depth_value < 1.0:
                    widget = self.scene_widget
                    world_point = widget.scene.camera.unproject(
                        x, y, depth_value,
                        widget.frame.width,
                        widget.frame.height
                    )
                    
                    coord_str = (f"{world_point[0]:.3f}, "
                               f"{world_point[1]:.3f}, "
                               f"{world_point[2]:.3f}")
                    
                    self.coord_callback(coord_str)
                    self.status_callback(
                        f"📍 Point selected: ({coord_str})",
                        [0.2, 0.8, 0.3]
                    )
                    self.marker_callback(world_point)
        
        self.scene_widget.scene.scene.render_to_depth_image(depth_callback)
