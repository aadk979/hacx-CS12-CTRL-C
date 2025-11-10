"""Photo upload and management panel."""
import open3d.visualization.gui as gui
import queue
import threading
from tkinter import Tk, filedialog
from typing import Callable

class PhotoPanel:
    """Panel for managing tag photos."""
    
    def __init__(self, em: float, status_callback: Callable):
        self.em = em
        self.status_callback = status_callback
        self.photo_count_label = None
        self.current_photos = []
        self.file_queue = queue.Queue()
        self.section = self._create_panel()
        self.window = None
    
    def set_window(self, window):
        """Set reference to main window for threading."""
        self.window = window
    
    def _create_panel(self) -> gui.CollapsableVert:
        """Create the photo panel UI."""
        section = gui.CollapsableVert(
            "📷 Photos",
            self.em * 0.5,
            gui.Margins(self.em * 0.5, 0, 0, 0)
        )
        
        button_row = gui.Horiz(self.em * 0.3)
        
        upload_btn = gui.Button("Upload Photos")
        upload_btn.set_on_clicked(self._on_upload)
        button_row.add_child(upload_btn)
        
        clear_btn = gui.Button("Clear")
        clear_btn.set_on_clicked(self._on_clear)
        button_row.add_child(clear_btn)
        
        section.add_child(button_row)
        
        self.photo_count_label = gui.Label("📸 Photos: 0")
        self.photo_count_label.text_color = gui.Color(0.5, 0.5, 0.5)
        section.add_child(self.photo_count_label)
        
        return section
    
    def get_widget(self) -> gui.CollapsableVert:
        """Get the panel widget."""
        return self.section
    
    def _on_upload(self):
        """Handle photo upload button click."""
        def file_dialog_thread():
            try:
                root = Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                file_paths = filedialog.askopenfilenames(
                    title="Select Photos",
                    filetypes=[
                        ("Image Files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                        ("All Files", "*.*")
                    ]
                )
                root.destroy()
                
                if file_paths:
                    self.file_queue.put(list(file_paths))
                else:
                    self.file_queue.put(None)
            except Exception as e:
                print(f"❌ Error in file dialog: {e}")
                self.file_queue.put(None)
        
        threading.Thread(target=file_dialog_thread, daemon=True).start()
        self.status_callback("📂 Opening file dialog...", [0.5, 0.5, 0.5])
        self._check_queue()
    
    def _check_queue(self):
        """Check file dialog queue for results."""
        try:
            file_paths = self.file_queue.get_nowait()
            if file_paths:
                self.current_photos.extend(file_paths)
                self.photo_count_label.text = f"📸 Photos: {len(self.current_photos)}"
                self.status_callback(
                    f"✅ Added {len(file_paths)} photo(s)",
                    [0.2, 0.8, 0.3]
                )
            else:
                self.status_callback(
                    "⚠️ No photos selected",
                    [0.8, 0.5, 0.2]
                )
        except queue.Empty:
            if self.window:
                gui.Application.instance.post_to_main_thread(
                    self.window,
                    self._check_queue
                )
    
    def _on_clear(self):
        """Clear photo selection."""
        self.current_photos.clear()
        self.photo_count_label.text = "📸 Photos: 0"
        self.status_callback("🗑️ Photos cleared", [0.8, 0.5, 0.2])
    
    def get_photos(self):
        """Get current photo list."""
        return self.current_photos.copy()
    
    def clear(self):
        """Clear photos."""
        self.current_photos.clear()
        self.photo_count_label.text = "📸 Photos: 0"
