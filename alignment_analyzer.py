from pathlib import Path
from typing import List, Dict, Tuple, Optional
import math
from qgis.core import (QgsVectorLayer, QgsFeature, QgsGeometry,
                      QgsProject, QgsFeatureRequest, QgsRectangle)
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                QPushButton, QLabel, QSpinBox,
                                QGroupBox, QTableWidget, QTableWidgetItem)
from qgis.PyQt.QtCore import Qt, pyqtSignal

class AlignmentAnalyzer:
    """
    A class to analyze and compare the alignment between image GPS locations
    and EO file positions. It provides methods to calculate distances and
    shift timestamp associations to find the best match.
    """
    
    def __init__(self, image_layer: QgsVectorLayer, eo_layer: QgsVectorLayer):
        """
        Initialize with the two vector layers we want to compare.
        
        Args:
            image_layer: Vector layer containing image GPS positions
            eo_layer: Vector layer containing EO file positions
        """
        self.image_layer = image_layer
        self.eo_layer = eo_layer
        self.current_shift = 0
        
    def _extract_base_filename(self, filename: str) -> str:
        """
        Extract the base part of the filename for matching between layers.
        Handles differences in filename formats between image and EO files.
        
        Args:
            filename: The full filename from either layer
            
        Returns:
            The base filename for matching
        """
        # Remove common suffixes and prefixes to match filenames
        # This might need adjustment based on your specific naming conventions
        filename = filename.replace('_1.tif', '')
        return filename.strip()
    
    def calculate_distances(self, shift: int = 0) -> List[Dict]:
        """
        Calculate distances between corresponding points with an optional shift.
        
        Args:
            shift: Number of positions to shift the EO timestamps (positive or negative)
            
        Returns:
            List of dictionaries containing match information and distances
        """
        results = []
        
        # Get all features from both layers
        image_features = list(self.image_layer.getFeatures())
        eo_features = list(self.eo_layer.getFeatures())
        
        # Create lookup dictionaries for faster matching
        image_dict = {self._extract_base_filename(f['filename']): f 
                     for f in image_features}
        eo_dict = {self._extract_base_filename(f['photo_id']): f 
                  for f in eo_features}
        
        # Sort EO features by timestamp to enable shifting
        eo_items = sorted(eo_dict.items(), key=lambda x: x[1]['event_time'])
        
        # Apply shift if needed
        if shift != 0:
            shifted_eo = {}
            for i, (key, feature) in enumerate(eo_items):
                # Calculate shifted index with wraparound
                shifted_idx = (i + shift) % len(eo_items)
                shifted_eo[key] = eo_items[shifted_idx][1]
            eo_dict = shifted_eo
        
        # Calculate distances for matching points
        for image_id, image_feature in image_dict.items():
            if image_id in eo_dict:
                eo_feature = eo_dict[image_id]
                
                # Get point geometries
                image_point = image_feature.geometry().asPoint()
                eo_point = eo_feature.geometry().asPoint()
                
                # Calculate 3D distance
                dx = image_point.x() - eo_point.x()
                dy = image_point.y() - eo_point.y()
                dz = image_feature['altitude'] - eo_feature['ellipsoid_height']
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                
                # Calculate horizontal distance
                horiz_distance = math.sqrt(dx*dx + dy*dy)
                
                results.append({
                    'image_id': image_id,
                    'distance_3d': distance,
                    'distance_2d': horiz_distance,
                    'dx': dx,
                    'dy': dy,
                    'dz': dz,
                    'image_time': image_feature['timestamp'],
                    'eo_time': eo_feature['event_time']
                })
        
        return results
    
    def get_alignment_stats(self, shift: int = 0) -> Dict:
        """
        Calculate statistical measures of alignment quality for a given shift.
        
        Args:
            shift: Number of positions to shift the EO timestamps
            
        Returns:
            Dictionary containing various statistical measures
        """
        distances = self.calculate_distances(shift)
        if not distances:
            return {
                'avg_3d': float('inf'),
                'avg_2d': float('inf'),
                'max_3d': float('inf'),
                'matches': 0
            }
        
        return {
            'avg_3d': sum(d['distance_3d'] for d in distances) / len(distances),
            'avg_2d': sum(d['distance_2d'] for d in distances) / len(distances),
            'max_3d': max(d['distance_3d'] for d in distances),
            'matches': len(distances)
        }


class AlignmentDialog(QDialog):
    """
    Dialog for interactively analyzing and adjusting the alignment between
    image GPS positions and EO file positions.
    """
    
    alignmentChanged = pyqtSignal(int)  # Signal emitted when shift changes
    
    def __init__(self, analyzer: AlignmentAnalyzer, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.current_shift = 0
        self.setup_ui()
        self.update_results()
        
    def setup_ui(self):
        """Create and arrange the user interface elements."""
        self.setWindowTitle("Alignment Analysis")
        self.setMinimumWidth(600)
        layout = QVBoxLayout()
        
        # Shift control group
        shift_group = QGroupBox("Timestamp Shift Control")
        shift_layout = QHBoxLayout()
        
        self.shift_spinbox = QSpinBox()
        self.shift_spinbox.setRange(-100, 100)
        self.shift_spinbox.setValue(0)
        self.shift_spinbox.valueChanged.connect(self.on_shift_changed)
        
        shift_layout.addWidget(QLabel("Shift Amount:"))
        shift_layout.addWidget(self.shift_spinbox)
        shift_group.setLayout(shift_layout)
        layout.addWidget(shift_group)
        
        # Results group
        results_group = QGroupBox("Alignment Results")
        results_layout = QVBoxLayout()
        
        self.avg_3d_label = QLabel("Average 3D Distance: --")
        self.avg_2d_label = QLabel("Average 2D Distance: --")
        self.max_dist_label = QLabel("Maximum Distance: --")
        self.matches_label = QLabel("Matching Points: --")
        
        results_layout.addWidget(self.avg_3d_label)
        results_layout.addWidget(self.avg_2d_label)
        results_layout.addWidget(self.max_dist_label)
        results_layout.addWidget(self.matches_label)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Details table
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(5)
        self.details_table.setHorizontalHeaderLabels([
            "Image ID", "3D Distance", "2D Distance", 
            "Image Time", "EO Time"
        ])
        layout.addWidget(self.details_table)
        
        self.setLayout(layout)
    
    def on_shift_changed(self, value: int):
        """Handle changes to the shift value."""
        self.current_shift = value
        self.update_results()
        self.alignmentChanged.emit(value)
    
    def update_results(self):
        """Update all display elements with current results."""
        # Get statistics for current shift
        stats = self.analyzer.get_alignment_stats(self.current_shift)
        
        # Update labels
        self.avg_3d_label.setText(f"Average 3D Distance: {stats['avg_3d']:.2f} m")
        self.avg_2d_label.setText(f"Average 2D Distance: {stats['avg_2d']:.2f} m")
        self.max_dist_label.setText(f"Maximum Distance: {stats['max_3d']:.2f} m")
        self.matches_label.setText(f"Matching Points: {stats['matches']}")
        
        # Update details table
        distances = self.analyzer.calculate_distances(self.current_shift)
        self.details_table.setRowCount(len(distances))
        
        for row, data in enumerate(distances):
            self.details_table.setItem(row, 0, 
                QTableWidgetItem(data['image_id']))
            self.details_table.setItem(row, 1, 
                QTableWidgetItem(f"{data['distance_3d']:.2f}"))
            self.details_table.setItem(row, 2, 
                QTableWidgetItem(f"{data['distance_2d']:.2f}"))
            self.details_table.setItem(row, 3, 
                QTableWidgetItem(data['image_time']))
            self.details_table.setItem(row, 4, 
                QTableWidgetItem(data['eo_time']))
        
        self.details_table.resizeColumnsToContents()

# First, let's get references to your existing layers
project = QgsProject.instance()
eo_layer = project.mapLayersByName("EO Positions")[0]
image_layer = project.mapLayersByName("Image Locations (UTM)")[0]

# Create an instance of our analyzer
analyzer = AlignmentAnalyzer(image_layer, eo_layer)

# Create and show the dialog
dialog = AlignmentDialog(analyzer)
dialog.show()