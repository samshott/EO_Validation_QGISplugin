from pathlib import Path
from PIL import Image
import os
from typing import List, Callable, Optional, Dict, Any
import json
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ImageData:
    """Structure for storing image location data."""
    file_path: str
    filename: str
    latitude: float
    longitude: float
    altitude: float
    timestamp: str
    capture_id: str

class ImageFinder:
    """A class to find MicaSense images and extract their location data."""
    
    GPS_TAG_MAP = {
        'GPSLatitudeRef': 1,
        'GPSLatitude': 2,
        'GPSLongitudeRef': 3,
        'GPSLongitude': 4,
        'GPSAltitudeRef': 5,
        'GPSAltitude': 6,
        'GPSTimeStamp': 7,
    }
    
    def __init__(self):
        self._files_processed = 0
        self._total_files = 0
    
    def _find_set_folders(self, root_path: Path) -> List[Path]:
        """Find all folders ending in 'SET' and their subfolders.
        
        This method searches the directory tree and identifies:
        1. Folders that end with 'SET'
        2. Any subfolders within those SET folders
        
        Args:
            root_path: The starting directory for the search
            
        Returns:
            List of Path objects for all relevant folders to search
        """
        set_folders = []
        
        # Walk through all directories
        for dir_path in root_path.rglob('*'):
            if dir_path.is_dir():
                # Check if this directory ends with 'SET'
                if dir_path.name.endswith('SET'):
                    set_folders.append(dir_path)
                    # Also add all its subdirectories
                    set_folders.extend([p for p in dir_path.rglob('*') if p.is_dir()])
                # If this directory is under a 'SET' folder, it's already included
                elif any(str(dir_path).startswith(str(set_folder)) 
                        for set_folder in set_folders):
                    continue
        
        print(f"\nFound {len(set_folders)} SET folders and their subdirectories:")
        for folder in set_folders:
            print(f"  {folder}")
            
        return set_folders

    def _convert_gps_coords(self, coords: tuple, ref: str) -> float:
        """Convert GPS coordinates from degrees/minutes/seconds to decimal degrees."""
        degrees = float(coords[0])
        minutes = float(coords[1])
        seconds = float(coords[2])
        
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        if ref in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    
    def _extract_capture_id(self, xmp_data: bytes) -> str:
        """Extract the MicaSense capture ID from XMP metadata."""
        try:
            xmp_str = xmp_data.decode('utf-8')
            if 'MicaSense:CaptureId' in xmp_str:
                start = xmp_str.find('MicaSense:CaptureId') + len('MicaSense:CaptureId') + 1
                end = xmp_str.find('</MicaSense:CaptureId>')
                return xmp_str[start:end].strip()
        except:
            pass
        return ""
    
    def _extract_image_data(self, img: Image.Image, file_path: Path) -> Optional[ImageData]:
        """Extract all relevant data from an image into our structured format."""
        try:
            gps_data = img.getexif().get_ifd(34853)
            if not gps_data:
                return None
                
            # Extract GPS coordinates
            if not all(tag in gps_data for tag in [
                self.GPS_TAG_MAP['GPSLatitude'],
                self.GPS_TAG_MAP['GPSLatitudeRef'],
                self.GPS_TAG_MAP['GPSLongitude'],
                self.GPS_TAG_MAP['GPSLongitudeRef'],
                self.GPS_TAG_MAP['GPSAltitude']
            ]):
                return None
            
            lat = gps_data[self.GPS_TAG_MAP['GPSLatitude']]
            lat_ref = gps_data[self.GPS_TAG_MAP['GPSLatitudeRef']]
            if isinstance(lat_ref, bytes):
                lat_ref = lat_ref.decode()
            latitude = self._convert_gps_coords(lat, lat_ref)
            
            lon = gps_data[self.GPS_TAG_MAP['GPSLongitude']]
            lon_ref = gps_data[self.GPS_TAG_MAP['GPSLongitudeRef']]
            if isinstance(lon_ref, bytes):
                lon_ref = lon_ref.decode()
            longitude = self._convert_gps_coords(lon, lon_ref)
            
            altitude = float(gps_data[self.GPS_TAG_MAP['GPSAltitude']])
            timestamp = img.tag.get(306, ('',))[0]  # DateTime tag
            
            capture_id = ""
            if 700 in img.tag:  # XMP tag
                capture_id = self._extract_capture_id(img.tag[700][0])
            
            return ImageData(
                file_path=str(file_path),
                filename=file_path.name,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                timestamp=timestamp,
                capture_id=capture_id
            )
            
        except Exception as e:
            print(f"Error extracting image data: {str(e)}")
            return None
    
    def process_images(self, 
                      root_dir: str, 
                      progress_callback: Optional[Callable[[float], None]] = None
                      ) -> List[ImageData]:
        """Find all band 1 images in SET folders and extract their data.
        
        This method:
        1. Identifies all relevant SET folders to search
        2. Finds band 1 images within those folders
        3. Extracts location data from valid images
        4. Saves the results to a JSON file in the root directory
        
        Args:
            root_dir: String path to the root directory to search
            progress_callback: Optional function for progress updates
            
        Returns:
            List of ImageData objects containing image information
        """
        root_path = Path(root_dir)
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"Invalid directory path: {root_dir}")
        
        # Find all SET folders and their subfolders
        set_folders = self._find_set_folders(root_path)
        if not set_folders:
            print("No SET folders found!")
            return []
            
        valid_images = []
        total_files = sum(1 for folder in set_folders 
                         for _ in folder.rglob('*_1.tif'))
        processed_files = 0
        
        # Process each SET folder
        for folder in set_folders:
            for file_path in folder.rglob('*_1.tif'):
                processed_files += 1
                
                if progress_callback:
                    progress = processed_files / total_files
                    progress_callback(progress)
                
                try:
                    with Image.open(file_path) as img:
                        # Verify it's a MicaSense image
                        make = img.tag.get(271)
                        model = img.tag.get(272)
                        if make and model and make[0] == 'MicaSense' and model[0] == 'Altum':
                            image_data = self._extract_image_data(img, file_path)
                            if image_data:
                                valid_images.append(image_data)
                                print(f"\nFound valid image: {file_path}")
                                print(f"Latitude: {image_data.latitude:.6f}")
                                print(f"Longitude: {image_data.longitude:.6f}")
                                print(f"Altitude: {image_data.altitude:.2f} meters")
                                print(f"Timestamp: {image_data.timestamp}")
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")
        
        if progress_callback:
            progress_callback(1.0)
        
        # Save results to JSON in root directory
        output_file = root_path / 'Altum_image_locations.json'
        self.save_to_json(valid_images, output_file)
            
        return valid_images
    
    def save_to_json(self, image_data: List[ImageData], output_file: Path):
        """Save the image data to a JSON file."""
        data_dicts = [asdict(data) for data in image_data]
        
        with open(output_file, 'w') as f:
            json.dump(data_dicts, f, indent=2)
            
        print(f"\nSaved {len(data_dicts)} image records to {output_file}")

def print_progress(progress: float):
    print(f"Progress: {progress * 100:.1f}%")

finder = ImageFinder()
try:
    # Process images and save results
    images = finder.process_images(
        r"D:\241107_PetersonP6", 
        progress_callback=print_progress
    )
    
except ValueError as e:
    print(f"Error: {e}")