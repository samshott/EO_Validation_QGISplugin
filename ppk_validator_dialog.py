from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QLabel, QFileDialog, 
                                QSpinBox, QLineEdit, QGroupBox)
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMessageBar

class PPKValidatorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Create and setup the user interface"""
        self.setWindowTitle('PPK Image Validator')
        self.resize(600, 400)

        # Main layout
        layout = QVBoxLayout()
        
        # Message bar for notifications
        self.message_bar = QgsMessageBar()
        layout.addWidget(self.message_bar)

        # Input group
        input_group = QGroupBox("Input Settings")
        input_layout = QVBoxLayout()

        # Image folder selection
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        folder_button = QPushButton("Browse...")
        folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(QLabel("Image Folder:"))
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(folder_button)
        input_layout.addLayout(folder_layout)

        # PPK file selection
        ppk_layout = QHBoxLayout()
        self.ppk_edit = QLineEdit()
        ppk_button = QPushButton("Browse...")
        ppk_button.clicked.connect(self.select_ppk)
        ppk_layout.addWidget(QLabel("PPK File:"))
        ppk_layout.addWidget(self.ppk_edit)
        ppk_layout.addWidget(ppk_button)
        input_layout.addLayout(ppk_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Shift control group
        shift_group = QGroupBox("Time Shift Control")
        shift_layout = QHBoxLayout()
        
        self.shift_spinbox = QSpinBox()
        self.shift_spinbox.setRange(-100, 100)
        self.shift_spinbox.setValue(0)
        self.shift_spinbox.valueChanged.connect(self.on_shift_changed)
        
        shift_layout.addWidget(QLabel("Timestamp Shift:"))
        shift_layout.addWidget(self.shift_spinbox)
        shift_layout.addStretch()
        
        shift_group.setLayout(shift_layout)
        layout.addWidget(shift_group)

        # Results group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        
        self.avg_distance_label = QLabel("Average Distance: --")
        results_layout.addWidget(self.avg_distance_label)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Add stretch to push everything up
        layout.addStretch()

        # Button box at the bottom
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Image Folder", ""
        )
        if folder:
            self.folder_edit.setText(folder)
            self.validate_inputs()

    def select_ppk(self):
        """Open PPK file selection dialog"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select PPK File", "", "Text Files (*.txt)"
        )
        if filename:
            self.ppk_edit.setText(filename)
            self.validate_inputs()

    def validate_inputs(self):
        """Validate input fields and enable/disable processing"""
        folder = self.folder_edit.text()
        ppk_file = self.ppk_edit.text()
        
        if folder and os.path.isdir(folder) and ppk_file and os.path.isfile(ppk_file):
            self.process_data()
        
    def on_shift_changed(self, value):
        """Handle changes to the shift value"""
        # This will be implemented later to process data with the new shift
        self.process_data()

    def process_data(self):
        """Process the data with current settings"""
        # This will be implemented later to handle the actual processing
        pass