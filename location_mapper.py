from pathlib import Path
import json
from typing import List, Dict, Any, Optional
from qgis.core import (QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
                      QgsField, QgsProject, QgsCoordinateReferenceSystem,
                      QgsCoordinateTransform, QgsFeatureRequest)
from qgis.PyQt.QtCore import QVariant
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

class LocationMapper:
    """A class to create QGIS vector layers from image location data.
    
    This class handles the conversion of GPS coordinates from our JSON file
    into a temporary QGIS point layer, including coordinate system transformations
    and attribute mapping.
    """
    
    def __init__(self):
        # Get reference to the QGIS project instance
        self.project = QgsProject.instance()
        
        # Define the source CRS (WGS84)
        self.source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        # Define the target CRS (UTM Zone 10N)
        self.target_crs = QgsCoordinateReferenceSystem("EPSG:32610")
        
        # Store the created layer for later reference
        self.current_layer = None
    
    def load_json_data(self, json_path: str) -> List[Dict[str, Any]]:
        """Load and validate the image location data from JSON.
        
        Args:
            json_path: Path to the JSON file containing image locations
            
        Returns:
            List of dictionaries containing image data
            
        Raises:
            ValueError: If the JSON file cannot be read or has invalid format
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Basic validation that we got a list of dictionaries
            if not isinstance(data, list):
                raise ValueError("JSON file must contain a list of image records")
            
            # Verify each record has required fields
            required_fields = {'latitude', 'longitude', 'altitude', 'filename'}
            for record in data:
                missing_fields = required_fields - set(record.keys())
                if missing_fields:
                    raise ValueError(f"Record missing required fields: {missing_fields}")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading JSON file: {str(e)}")
    
    def create_vector_layer(self, 
                          image_data: List[Dict[str, Any]], 
                          layer_name: str = "Image Locations") -> QgsVectorLayer:
        """Create a temporary point vector layer from image locations.
        
        This method:
        1. Creates a new memory layer with WGS84 CRS
        2. Adds appropriate fields for image attributes
        3. Creates point features from the image coordinates
        4. Configures basic styling for the layer
        
        Args:
            image_data: List of dictionaries containing image information
            layer_name: Name for the vector layer in QGIS
            
        Returns:
            The created QgsVectorLayer object
        """
        # Create a temporary point layer
        layer = QgsVectorLayer("Point?crs=EPSG:4326", layer_name, "memory")
        
        # Start editing the layer
        layer.startEditing()
        
        # Add fields for attributes
        fields = [
            QgsField("filename", QVariant.String),
            QgsField("altitude", QVariant.Double),
            QgsField("timestamp", QVariant.String),
            QgsField("capture_id", QVariant.String)
        ]
        
        layer.dataProvider().addAttributes(fields)
        layer.updateFields()
        
        # Add features to the layer
        features = []
        for record in image_data:
            feature = QgsFeature()
            point = QgsPointXY(record['longitude'], record['latitude'])
            feature.setGeometry(QgsGeometry.fromPointXY(point))
            
            # Set attributes
            feature.setAttributes([
                record['filename'],
                record['altitude'],
                record.get('timestamp', ''),  # Use empty string if not present
                record.get('capture_id', '')   # Use empty string if not present
            ])
            
            features.append(feature)
        
        layer.dataProvider().addFeatures(features)
        layer.commitChanges()
        
        # Basic styling - red points
        symbol = layer.renderer().symbol()
        symbol.setColor(QColor(255, 0, 0))
        symbol.setSize(2)
        
        # Add the layer to the project
        self.project.addMapLayer(layer)
        self.current_layer = layer
        
        return layer
    
    def update_layer_crs(self, output_crs: str = "EPSG:32610") -> None:
        """Transform the layer to a different coordinate system.
        
        This is useful for converting from WGS84 to UTM for distance calculations.
        
        Args:
            output_crs: EPSG code for the desired output coordinate system
        """
        if not self.current_layer:
            raise ValueError("No layer has been created yet")
            
        # Create the target CRS
        target_crs = QgsCoordinateReferenceSystem(output_crs)
        
        # Create a new layer with the target CRS
        transformed_layer = QgsVectorLayer(
            f"Point?crs={output_crs}",
            f"{self.current_layer.name()} (UTM)",
            "memory"
        )
        
        # Copy the fields
        transformed_layer.dataProvider().addAttributes(
            self.current_layer.fields()
        )
        transformed_layer.updateFields()
        
        # Create the coordinate transform
        transform = QgsCoordinateTransform(
            self.source_crs,
            target_crs,
            self.project
        )
        
        # Transform each feature
        features = []
        for feature in self.current_layer.getFeatures():
            new_feature = QgsFeature()
            # Transform the geometry
            geom = feature.geometry()
            geom.transform(transform)
            new_feature.setGeometry(geom)
            # Copy attributes
            new_feature.setAttributes(feature.attributes())
            features.append(new_feature)
        
        # Add the features to the new layer
        transformed_layer.dataProvider().addFeatures(features)
        
        # Add the transformed layer to the project
        self.project.addMapLayer(transformed_layer)
        
        # Remove the original layer if desired
        self.project.removeMapLayer(self.current_layer)
        self.current_layer = transformed_layer
    
    def map_locations(self, json_path: str, transform_to_utm: bool = True) -> QgsVectorLayer:
        """Main method to create a vector layer from JSON image locations.
        
        This method orchestrates the whole process:
        1. Loads the JSON data
        2. Creates a vector layer
        3. Optionally transforms to UTM
        4. Returns the final layer
        
        Args:
            json_path: Path to the JSON file with image locations
            transform_to_utm: Whether to transform the layer to UTM Zone 10N
            
        Returns:
            The created QgsVectorLayer object
        """
        # Load the data
        image_data = self.load_json_data(json_path)
        
        # Create the initial WGS84 layer
        layer = self.create_vector_layer(image_data)
        
        # Transform to UTM if requested
        if transform_to_utm:
            self.update_layer_crs()
        
        return self.current_layer



# This code won't run directly as it needs QGIS environment
mapper = LocationMapper()

# Map the image locations
layer = mapper.map_locations(
    r"C:\0DATA\240920_Arc_graveyard\Combined\Altum_image_locations.json",
    transform_to_utm=True
)

