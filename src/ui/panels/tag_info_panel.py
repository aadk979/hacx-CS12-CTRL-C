"""Tag information input panel."""
import open3d.visualization.gui as gui

class TagInfoPanel:
    """Panel for entering tag title and description."""
    
    def __init__(self, em: float):
        self.em = em
        self.title_input = None
        self.desc_input = None
        self.section = self._create_panel()
    
    def _create_panel(self) -> gui.CollapsableVert:
        """Create the tag info panel UI."""
        section = gui.CollapsableVert(
            "📝 Tag Information",
            self.em * 0.5,
            gui.Margins(self.em * 0.5, 0, 0, 0)
        )
        
        section.add_child(gui.Label("Title:"))
        self.title_input = gui.TextEdit()
        self.title_input.placeholder_text = "Enter a descriptive title..."
        section.add_child(self.title_input)
        
        section.add_fixed(self.em * 0.3)
        section.add_child(gui.Label("Description:"))
        self.desc_input = gui.TextEdit()
        self.desc_input.placeholder_text = "Add detailed description..."
        section.add_child(self.desc_input)
        
        return section
    
    def get_widget(self) -> gui.CollapsableVert:
        """Get the panel widget."""
        return self.section
    
    def get_title(self) -> str:
        """Get entered title."""
        return self.title_input.text_value.strip()
    
    def get_description(self) -> str:
        """Get entered description."""
        return self.desc_input.text_value.strip()
    
    def clear(self):
        """Clear input fields."""
        self.title_input.text_value = ""
        self.desc_input.text_value = ""
