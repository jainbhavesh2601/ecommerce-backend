"""
Geocoding service to convert address strings to latitude/longitude coordinates.
Uses OpenStreetMap Nominatim API (free, no API key required).
"""
import requests
from typing import Optional, Tuple
import time


class GeocodingService:
    """Service to convert address strings to lat/lon coordinates using Nominatim."""
    
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    
    @staticmethod
    def geocode_address(address: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Geocode an address string to latitude and longitude.
        
        Args:
            address: The address string to geocode
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if geocoding fails
        """
        if not address or not address.strip():
            return None, None
        
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1
            }
            headers = {
                'User-Agent': 'ArtisanAlley-Ecommerce/1.0'
            }
            
            # Make request to Nominatim
            response = requests.get(
                GeocodingService.BASE_URL,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    return lat, lon
            
            return None, None
            
        except Exception as e:
            print(f"Error geocoding address '{address}': {str(e)}")
            return None, None
    
    @staticmethod
    def geocode_address_with_delay(address: str, delay_seconds: float = 1.0) -> Tuple[Optional[float], Optional[float]]:
        """
        Geocode an address with a delay to respect rate limits.
        
        Args:
            address: The address string to geocode
            delay_seconds: Delay in seconds before making the request
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if geocoding fails
        """
        time.sleep(delay_seconds)
        return GeocodingService.geocode_address(address)
    
    @staticmethod
    def reverse_geocode(lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocode coordinates to an address.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Address string or None if reverse geocoding fails
        """
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json'
            }
            headers = {
                'User-Agent': 'ArtisanAlley-Ecommerce/1.0'
            }
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'display_name' in data:
                    return data['display_name']
            
            return None
            
        except Exception as e:
            print(f"Error reverse geocoding coordinates ({lat}, {lon}): {str(e)}")
            return None

