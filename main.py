"""Application entry point."""
import open3d.visualization.rendering as rendering
from src.ui.main_window import MainWindow

# Compatibility patch for older Open3D versions
if not hasattr(rendering.Open3DScene, "pick"):
    def _fake_pick(self, x, y, camera, width, height):
        class DummyPick:
            is_hittable = False
            object_name = None
        return DummyPick()
    
    rendering.Open3DScene.pick = _fake_pick

def main():
    """Main application entry point."""
    app = MainWindow()
    app.initialize()
    app.run()

if __name__ == "__main__":
    main()
