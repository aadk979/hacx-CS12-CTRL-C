"""Coordinate display panel."""
import open3d.visualization.gui as gui

class CoordinatePanel:
    """Panel for displaying and editing 3D coordinates."""
    
    def __init__(self, em: float):
        self.em = em
        self.coord_edit = None
        self.section = self._create_panel()
    
    def _create_panel(self) -> gui.CollapsableVert:
        """Create the coordinate panel UI."""
        section = gui.CollapsableVert(
            "📍 Coordinates", 
            self.em * 0.5, 
            gui.Margins(self.em * 0.5, 0, 0, 0)
        )
        
        section.add_child(gui.Label("X, Y, Z Position:"))
        self.coord_edit = gui.TextEdit()
        self.coord_edit.text_value = "0.000, 0.000, 0.000"
        section.add_child(self.coord_edit)
        
        return section
    
    def get_widget(self) -> gui.CollapsableVert:
        """Get the panel widget."""
        return self.section
    
    def set_coordinates(self, coord_str: str):
        """Update displayed coordinates."""
        self.coord_edit.text_value = coord_str
    
    def get_coordinates(self) -> str:
        """Get current coordinate string."""
        return self.coord_edit.text_value.strip()
