from pathlib import Path
from typing import List, Set
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QCheckBox, 
                                QPushButton, QLabel, QScrollArea, 
                                QWidget, QGroupBox)
from qgis.PyQt.QtCore import Qt

class EOFileSelector(QDialog):
    """A dialog for selecting EO files from a list of candidates.
    
    This dialog presents a user-friendly interface showing text files whose names
    contain 'altum' or 'eo'. Each file can be selected via a checkbox, making it
    easy for users to identify and choose their specific EO files.
    """
    
    def __init__(self, file_paths: List[Path], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.selected_files: Set[Path] = set()
        self.setup_ui()
        
    def setup_ui(self):
        """Create and arrange the user interface elements."""
        # Set up the main window
        self.setWindowTitle("Select Altum EO Files")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Add clear instructions for the user
        instructions = QLabel(
            "Select the Exterior Orientation files for your Altum imagery.\n"
            "These are typically text files with names containing 'altum' and/or 'eo'."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Create a scrollable area for the file list
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Add checkboxes for each file, grouped by directory
        self.checkboxes = {}
        current_dir = None
        
        # Sort files by directory for easier navigation
        sorted_files = sorted(self.file_paths, key=lambda x: (x.parent, x.name))
        
        for file_path in sorted_files:
            # Add directory label if we've moved to a new directory
            if current_dir != file_path.parent:
                current_dir = file_path.parent
                dir_label = QLabel(f"\nDirectory: {current_dir}")
                dir_label.setStyleSheet("font-weight: bold;")
                scroll_layout.addWidget(dir_label)
            
            # Create checkbox with just the filename (full path visible in tooltip)
            checkbox = QCheckBox(file_path.name)
            checkbox.setToolTip(str(file_path))  # Show full path on hover
            self.checkboxes[checkbox] = file_path
            scroll_layout.addWidget(checkbox)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Add convenience buttons
        button_group = QGroupBox("Selection Options")
        button_layout = QVBoxLayout()
        
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all)
        button_layout.addWidget(select_all)
        
        clear_all = QPushButton("Clear All")
        clear_all.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_all)
        
        button_group.setLayout(button_layout)
        layout.addWidget(button_group)
        
        # Add OK/Cancel buttons
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button)
        
        self.setLayout(layout)
    
    def select_all(self):
        """Select all checkboxes in the list."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
    
    def clear_all(self):
        """Clear all checkbox selections."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
    
    def get_selected_files(self) -> List[Path]:
        """Get the paths of all selected files."""
        return [
            self.checkboxes[checkbox]
            for checkbox in self.checkboxes
            if checkbox.isChecked()
        ]


class EOFinder:
    """A class to find and select Altum EO files based on filename patterns.
    
    This class searches for text files whose names contain 'altum' or 'eo'
    (case insensitive) and allows users to select which ones are the actual
    Exterior Orientation files they want to use.
    """
    
    def find_eo_files(self, root_dir: str) -> List[Path]:
        """Find all potential EO files in a directory tree based on filename.
        
        This method searches recursively through the directory tree for .txt files
        whose names contain either 'altum' or 'eo' (case insensitive).
        
        Args:
            root_dir: Path to the root directory to search
            
        Returns:
            List of paths to potential EO files
            
        Raises:
            ValueError: If the directory doesn't exist
        """
        root_path = Path(root_dir)
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"Invalid directory path: {root_dir}")
        
        # Find all .txt files with 'altum' or 'eo' in the name
        potential_files = []
        for txt_file in root_path.rglob('*.txt'):
            filename_lower = txt_file.name.lower()
            if 'altum' in filename_lower or 'eo' in filename_lower:
                potential_files.append(txt_file)
        
        print(f"Found {len(potential_files)} potential EO files")
        return potential_files
    
    def find_and_select_eo_files(self, root_dir: str) -> List[Path]:
        """Main method to find potential EO files and let user select the correct ones.
        
        This method coordinates the entire process:
        1. Searches for text files with matching filenames
        2. Shows them to the user in a selection dialog
        3. Returns the list of files the user selected
        
        Args:
            root_dir: Path to the root directory to search
            
        Returns:
            List of paths to the selected EO files
        """
        potential_files = self.find_eo_files(root_dir)
        if not potential_files:
            print("No potential EO files found")
            return []
        
        # Show selection dialog
        dialog = EOFileSelector(potential_files)
        if dialog.exec_() == QDialog.Accepted:
            selected_files = dialog.get_selected_files()
            print(f"User selected {len(selected_files)} EO files")
            return selected_files
        
        return []  # Return empty list if user cancelled

# Example usage:
finder = EOFinder()
try:
    selected_files = finder.find_and_select_eo_files(
        r"D:\241107_PetersonP6"
    )
    print("\nSelected EO files:")
    for file in selected_files:
        print(f"  {file}")
except ValueError as e:
    print(f"Error: {e}")