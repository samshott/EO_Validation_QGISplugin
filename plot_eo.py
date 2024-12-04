from pathlib import Path
import csv
from typing import List, Dict, Any, Optional
from qgis.core import (QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
                      QgsField, QgsProject, QgsCoordinateReferenceSystem,
                      QgsSymbol, QgsSingleSymbolRenderer)
from qgis.PyQt.QtCore import QVariant
from PyQt5.QtGui import QColor

class EOPlotter:
    """A class to visualize EO data from multiple files in QGIS.
    
    This class reads Exterior Orientation files and creates a single vector
    layer showing all camera positions. The data is expected to be in CSV
    format with columns for filename, x, y, z coordinates (UTM Zone 10N),
    and a timestamp in the last column.
    """
    
    def __init__(self):
        # Get reference to the QGIS project instance
        self.project = QgsProject.instance()
        # Store the created layer for later reference
        self.current_layer = None
        
    def read_eo_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read and parse a single EO file.
        
        This method carefully reads the CSV file, handling potential variations
        in the data format and extracting the essential positioning information.
        
        Args:
            file_path: Path to the EO file to read
            
        Returns:
            List of dictionaries containing the parsed data from each row
            
        Raises:
            ValueError: If the file cannot be read or has invalid format
        """
        try:
            records = []
            with open(file_path, 'r') as f:
                # First, determine if we have a header
                first_line = f.readline().strip()
                f.seek(0)  # Go back to start of file
                
                # Try to intelligently determine if this is a header row
                first_fields = first_line.split(',')
                has_header = any(
                    field.lower() in {'filename', 'name', 'image'} 
                    for field in first_fields
                )
                
                # Read the CSV file
                reader = csv.reader(f)
                if has_header:
                    next(reader)  # Skip header row
                
                # Process each row
                for row in reader:
                    # Extract the key information
                    # We know timestamp is the last column
                    record = {
                        'filename': row[0],          # First column is filename
                        'x': float(row[1]),          # UTM Easting
                        'y': float(row[2]),          # UTM Northing
                        'z': float(row[3]),          # Elevation
                        'timestamp': row[-1].strip() # Last column is timestamp
                    }
                    records.append(record)
            
            return records
            
        except Exception as e:
            raise ValueError(f"Error reading EO file {file_path}: {str(e)}")
    
    def create_vector_layer(self, 
                          all_records: List[Dict[str, Any]], 
                          layer_name: str = "EO Positions") -> QgsVectorLayer:
        """Create a vector layer from the EO records.
        
        This method creates a temporary point layer showing all camera positions
        from the EO files, with attributes for identification and analysis.
        
        Args:
            all_records: List of dictionaries containing EO data
            layer_name: Name for the vector layer in QGIS
            
        Returns:
            The created QgsVectorLayer object
        """
        # Create a point layer with UTM Zone 10N CRS
        layer = QgsVectorLayer(
            "Point?crs=EPSG:32610", 
            layer_name, 
            "memory"
        )
        
        # Start editing the layer
        layer.startEditing()
        
        # Add fields for attributes we want to keep
        fields = [
            QgsField("filename", QVariant.String),
            QgsField("altitude", QVariant.Double),
            QgsField("timestamp", QVariant.String),
            QgsField("source_file", QVariant.String)
        ]
        
        layer.dataProvider().addAttributes(fields)
        layer.updateFields()
        
        # Add features for each record
        features = []
        for record in all_records:
            feature = QgsFeature()
            # Create point geometry from UTM coordinates
            point = QgsPointXY(record['x'], record['y'])
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            
            # Set attributes
            feature.setAttributes([
                record['filename'],
                record['z'],
                record['timestamp'],
                str(record.get('source_file', ''))
            ])
            
            features.append(feature)
        
        # Add all features to the layer
        layer.dataProvider().addFeatures(features)
        layer.commitChanges()
        
        # Apply some basic styling - blue points
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(QColor(0, 0, 255))
        symbol.setSize(2)
        
        renderer = QgsSingleSymbolRenderer(symbol)
        layer.setRenderer(renderer)
        
        # Add the layer to the project
        self.project.addMapLayer(layer)
        self.current_layer = layer
        
        return layer
    
    def plot_eo_files(self, eo_files: List[Path]) -> Optional[QgsVectorLayer]:
        """Main method to read and plot multiple EO files.
        
        This method coordinates the entire process:
        1. Reads all EO files
        2. Combines their data
        3. Creates a single vector layer showing all positions
        
        Args:
            eo_files: List of paths to EO files to plot
            
        Returns:
            The created QgsVectorLayer object, or None if no data was found
        """
        # Read all EO files
        all_records = []
        for file_path in eo_files:
            try:
                records = self.read_eo_file(file_path)
                # Add source file information to each record
                for record in records:
                    record['source_file'] = file_path.name
                all_records.extend(records)
                print(f"Read {len(records)} positions from {file_path.name}")
            except ValueError as e:
                print(f"Warning: {str(e)}")
                continue
        
        if not all_records:
            print("No valid EO data found in the provided files")
            return None
        
        # Create the vector layer with all positions
        print(f"\nCreating vector layer with {len(all_records)} total positions")
        return self.create_vector_layer(all_records)



# This code won't run directly as it needs QGIS environment
plotter = EOPlotter()

# Example list of EO files
eo_files = [
    Path(r"path\to\first_eo.txt"),
    Path(r"path\to\second_eo.txt")
]

# Create the vector layer
layer = plotter.plot_eo_files(eo_files)