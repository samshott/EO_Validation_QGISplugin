from pathlib import Path
from typing import List, Set
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QCheckBox, 
                                QPushButton, QLabel, QScrollArea, 
                                QWidget, QGroupBox)
from qgis.PyQt.QtCore import Qt

class EOFileSelector(QDialog):
    """A dialog for selecting EO files from a list of candidates.
    
    This dialog presents users with checkboxes for each potential EO file found,
    allowing them to select which files are actually Altum EO files. It includes
    a scrollable area to handle many files and shows the full path of each file
    to help users make informed selections.
    """
    
    def __init__(self, file_paths: List[Path], parent=None):
        """Initialize the dialog with a list of file paths to display.
        
        Args:
            file_paths: List of Path objects representing potential EO files
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.file_paths = file_paths
        self.selected_files: Set[Path] = set()
        self.setup_ui()
        
    def setup_ui(self):
        """Create and arrange the user interface elements."""
        self.setWindowTitle("Select Altum EO Files")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Add instructions
        instructions = QLabel(
            "Please select the text files that contain Altum Exterior Orientation data:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Create a scroll area for the checkboxes
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Create a checkbox for each file
        self.checkboxes = {}
        for file_path in self.file_paths:
            checkbox = QCheckBox(str(file_path))
            self.checkboxes[checkbox] = file_path
            scroll_layout.addWidget(checkbox)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Add buttons
        button_layout = QVBoxLayout()
        
        # Quick selection buttons
        select_group = QGroupBox("Quick Selection")
        select_layout = QVBoxLayout()
        
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all)
        select_layout.addWidget(select_all)
        
        clear_all = QPushButton("Clear All")
        clear_all.clicked.connect(self.clear_all)
        select_layout.addWidget(clear_all)
        
        select_group.setLayout(select_layout)
        button_layout.addWidget(select_group)
        
        # OK/Cancel buttons
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def select_all(self):
        """Select all checkboxes."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
    
    def clear_all(self):
        """Clear all checkboxes."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)
    
    def get_selected_files(self) -> List[Path]:
        """Get the paths of all selected files.
        
        Returns:
            List of Path objects for the selected files
        """
        return [
            self.checkboxes[checkbox]
            for checkbox in self.checkboxes
            if checkbox.isChecked()
        ]


class EOFinder:
    """A class to find and select Altum EO files.
    
    This class handles searching through directories to find potential EO files
    and presents them to the user for selection. It combines automatic filtering
    based on file content with user confirmation to ensure accurate results.
    """
    
    def __init__(self):
        self.search_terms = {'altum', 'eo'}  # Case-insensitive search terms
    
    def _is_potential_eo_file(self, file_path: Path) -> bool:
        """Check if a file might be an EO file based on its content.
        
        This method:
        1. Verifies the file is a text file
        2. Searches for key terms that indicate it might be an EO file
        3. Returns True if the file is a potential match
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Boolean indicating if the file might be an EO file
        """
        if not file_path.suffix.lower() == '.txt':
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first few lines where identifiers are likely to be
                content = f.read(1000).lower()
                return any(term in content for term in self.search_terms)
        except Exception as e:
            print(f"Error reading {file_path}: {str(e)}")
            return False
    
    def find_eo_files(self, root_dir: str) -> List[Path]:
        """Find all potential EO files in a directory tree.
        
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
        
        # Find all .txt files that might be EO files
        potential_files = [
            path for path in root_path.rglob('*.txt')
            if self._is_potential_eo_file(path)
        ]
        
        print(f"Found {len(potential_files)} potential EO files")
        return potential_files
    
    def get_user_selected_files(self, file_paths: List[Path]) -> List[Path]:
        """Show the selection dialog and get user's choices.
        
        Args:
            file_paths: List of paths to potential EO files
            
        Returns:
            List of paths that the user selected
        """
        dialog = EOFileSelector(file_paths)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_selected_files()
        return []
    
    def find_and_select_eo_files(self, root_dir: str) -> List[Path]:
        """Main method to find and select EO files.
        
        This method:
        1. Searches for potential EO files
        2. Shows them to the user for selection
        3. Returns the selected files
        
        Args:
            root_dir: Path to the root directory to search
            
        Returns:
            List of paths to the selected EO files
        """
        potential_files = self.find_eo_files(root_dir)
        if not potential_files:
            print("No potential EO files found")
            return []
            
        selected_files = self.get_user_selected_files(potential_files)
        print(f"User selected {len(selected_files)} EO files")
        return selected_files


# Example usage:
finder = EOFinder()
try:
    selected_files = finder.find_and_select_eo_files(
        r"C:\0DATA\240920_Arc_graveyard\Combined"
    )
    print("\nSelected EO files:")
    for file in selected_files:
        print(f"  {file}")
except ValueError as e:
    print(f"Error: {e}")