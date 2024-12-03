from pathlib import Path
from PIL import Image
import os
from typing import List, Callable, Optional, Dict, Any, Tuple
from fractions import Fraction

class ImageFinder:
    """A class to find and extract GPS coordinates from MicaSense Altum images.
    
    This class handles the complexities of GPS data storage in TIFF files, including:
    - Finding the GPS IFD (Image File Directory) within the TIFF structure
    - Converting GPS coordinates from their raw rational number format
    - Handling the various coordinate reference indicators (N/S, E/W)
    """
    
    # Define GPS tag IDs according to the EXIF specification
    GPS_TAG_MAP = {
        'GPSLatitudeRef': 1,    # N or S
        'GPSLatitude': 2,       # Latitude degrees, minutes, seconds
        'GPSLongitudeRef': 3,   # E or W
        'GPSLongitude': 4,      # Longitude degrees, minutes, seconds
        'GPSAltitudeRef': 5,    # Above/below sea level
        'GPSAltitude': 6,       # Altitude in meters
        'GPSTimeStamp': 7,      # UTC timestamp
    }
    
    def __init__(self):
        self._files_processed = 0
        self._total_files = 0
    
    def _convert_gps_coords(self, coords: Tuple, ref: str) -> float:
        """Convert GPS coordinates from degrees/minutes/seconds to decimal degrees.
        
        Args:
            coords: Tuple of three rational numbers (degrees, minutes, seconds)
            ref: Direction reference ('N', 'S', 'E', or 'W')
            
        Returns:
            Float representing the decimal degrees, negative for S or W
        """
        # Convert each component from rational numbers to float
        degrees = float(coords[0])
        minutes = float(coords[1])
        seconds = float(coords[2])
        
        # Calculate decimal degrees
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        # Make negative if South or West
        if ref in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    
    def _extract_gps_info(self, img: Image.Image) -> Dict[str, Any]:
        """Extract GPS information from a TIFF image.
        
        This method handles the complex structure of GPS data in TIFF files by:
        1. Finding the GPS IFD offset
        2. Reading the raw GPS values
        3. Converting coordinates to decimal degrees
        
        Args:
            img: PIL Image object of the TIFF file
            
        Returns:
            Dictionary containing extracted GPS information
        """
        try:
            if not hasattr(img, 'tag'):
                return {}
                
            # The GPS IFD is stored in tag 34853
            gps_ifd_offset = img.tag.get(34853)
            if not gps_ifd_offset:
                return {}
                
            # The GPS data is stored in a separate IFD
            gps_tags = img.tag.get(34853)
            if not gps_tags:
                return {}
                
            gps_info = {}
            
            # Extract GPS data if available
            # Note: We're using img.getexif().get_ifd(34853) as a more reliable
            # way to access the GPS IFD
            gps_data = img.getexif().get_ifd(34853)
            if not gps_data:
                return {}
                
            # Debug: Print out the GPS data we found
            print("\nGPS Data found:")
            for tag_id, value in gps_data.items():
                tag_name = next((name for name, id in self.GPS_TAG_MAP.items() if id == tag_id), str(tag_id))
                print(f"{tag_name}: {value} (type: {type(value)})")
            
            # Get latitude
            if (self.GPS_TAG_MAP['GPSLatitude'] in gps_data and 
                self.GPS_TAG_MAP['GPSLatitudeRef'] in gps_data):
                lat = gps_data[self.GPS_TAG_MAP['GPSLatitude']]
                lat_ref = gps_data[self.GPS_TAG_MAP['GPSLatitudeRef']]
                # Handle reference value whether it's bytes or string
                if isinstance(lat_ref, bytes):
                    lat_ref = lat_ref.decode()
                gps_info['latitude'] = self._convert_gps_coords(lat, lat_ref)
            
            # Get longitude
            if (self.GPS_TAG_MAP['GPSLongitude'] in gps_data and 
                self.GPS_TAG_MAP['GPSLongitudeRef'] in gps_data):
                lon = gps_data[self.GPS_TAG_MAP['GPSLongitude']]
                lon_ref = gps_data[self.GPS_TAG_MAP['GPSLongitudeRef']]
                # Handle reference value whether it's bytes or string
                if isinstance(lon_ref, bytes):
                    lon_ref = lon_ref.decode()
                gps_info['longitude'] = self._convert_gps_coords(lon, lon_ref)
            
            # Get altitude
            if self.GPS_TAG_MAP['GPSAltitude'] in gps_data:
                alt = gps_data[self.GPS_TAG_MAP['GPSAltitude']]
                # Altitude is stored as a single rational number
                gps_info['altitude'] = float(alt)
            
            return gps_info
            
        except Exception as e:
            print(f"Error extracting GPS info: {str(e)}")
            return {}
    
    def _is_valid_image(self, file_path: Path) -> bool:
        """Validate if an image has the required GPS metadata.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Boolean indicating if the image has valid GPS data
        """
        try:
            with Image.open(file_path) as img:
                # First check if it's a MicaSense Altum image
                make = img.tag.get(271)
                model = img.tag.get(272)
                if not (make and model and 
                       make[0] == 'MicaSense' and 
                       model[0] == 'Altum'):
                    return False
                
                # Extract GPS information
                gps_info = self._extract_gps_info(img)
                
                # Check if we got the minimum required GPS data
                has_coords = all(key in gps_info for key in ['latitude', 'longitude'])
                
                if has_coords:
                    print(f"\nFound valid image: {file_path}")
                    print(f"Latitude: {gps_info['latitude']:.6f}")
                    print(f"Longitude: {gps_info['longitude']:.6f}")
                    if 'altitude' in gps_info:
                        print(f"Altitude: {gps_info['altitude']:.2f} meters")
                
                return has_coords
                
        except Exception as e:
            print(f"Error validating image {file_path}: {str(e)}")
            return False
    
    def find_band_one_images(self, 
                            root_dir: str, 
                            progress_callback: Optional[Callable[[float], None]] = None
                            ) -> List[Path]:
        """Find all valid band 1 images with GPS data in the given directory.
        
        Args:
            root_dir: String path to the root directory to search
            progress_callback: Optional function for progress updates
            
        Returns:
            List of Path objects pointing to valid band 1 images
        """
        root_path = Path(root_dir)
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"Invalid directory path: {root_dir}")
            
        self._files_processed = 0
        self._total_files = sum(1 for _ in root_path.rglob('*'))
        
        valid_images = []
        
        for file_path in root_path.rglob('*'):
            self._files_processed += 1
            
            if progress_callback and self._total_files > 0:
                progress = self._files_processed / self._total_files
                progress_callback(progress)
            
            if file_path.name.endswith('_1.tif'):
                if self._is_valid_image(file_path):
                    valid_images.append(file_path)
        
        if progress_callback:
            progress_callback(1.0)
            
        return valid_images
def print_progress(progress: float):
    """Example progress callback that prints percentage."""
    print(f"Progress: {progress * 100:.0f}%")
    
finder = ImageFinder()
try:
    images = finder.find_band_one_images(
        r"C:\0DATA\240920_Arc_graveyard\Combined\Flight2\Altum\0000SET\004", 
        progress_callback=print_progress
    )
    print(f"\nFound {len(images)} valid band 1 images:")
    for image in images:
        print(f"  {image}")
except ValueError as e:
    print(f"Error: {e}")