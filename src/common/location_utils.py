import math
from typing import Optional, Tuple

class LocationUtils:
    """Utility class for location-based operations"""
    
    @staticmethod
    def haversine_distance(
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        
        Returns distance in kilometers
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    @staticmethod
    def calculate_distance(
        user_lat: Optional[float],
        user_lon: Optional[float],
        seller_lat: Optional[float],
        seller_lon: Optional[float]
    ) -> Optional[float]:
        """
        Calculate distance between user and seller locations
        Returns None if any coordinate is missing
        """
        if user_lat is None or user_lon is None or seller_lat is None or seller_lon is None:
            return None
        
        return LocationUtils.haversine_distance(user_lat, user_lon, seller_lat, seller_lon)
    
    @staticmethod
    def is_within_radius(
        distance: Optional[float],
        max_distance_km: Optional[float]
    ) -> bool:
        """
        Check if distance is within the specified radius
        If distance is None, returns True (don't filter out)
        If max_distance_km is None, returns True (no radius filter)
        """
        if distance is None or max_distance_km is None:
            return True
        
        return distance <= max_distance_km
    
    @staticmethod
    def format_distance(distance: Optional[float]) -> str:
        """
        Format distance for display
        """
        if distance is None:
            return "Distance unavailable"
        
        if distance < 1:
            return f"{int(distance * 1000)} meters"
        elif distance < 10:
            return f"{distance:.1f} km"
        else:
            return f"{int(distance)} km"

