"""
Type definitions for volcano data objects

This module contains type definitions and helper functions for working with
volcano data throughout the application.
"""
from typing import Dict, List, Optional, Any, TypedDict
from dataclasses import dataclass


class VolcanoDict(TypedDict, total=False):
    """TypedDict representation of a Volcano"""
    name: str
    country: str
    latitude: float
    longitude: float
    alert_level: Optional[str]
    last_eruption: str
    insar_url: Optional[str]
    # Additional fields from USGS data
    id: str
    elevation: float
    type: str
    region: str
    description: Optional[str]
    activity: Optional[str]


@dataclass
class Volcano:
    """Dataclass representation of a Volcano"""
    name: str
    country: str
    latitude: float
    longitude: float
    alert_level: Optional[str] = None
    last_eruption: str = "Unknown"
    insar_url: Optional[str] = None
    id: Optional[str] = None
    elevation: Optional[float] = None
    type: Optional[str] = None
    region: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Volcano':
        """
        Create a Volcano object from a dictionary
        
        Args:
            data: Dictionary containing volcano data
            
        Returns:
            Volcano: A new Volcano object
        """
        # Map snake_case keys to camelCase if needed
        key_mapping = {
            'alert_level': 'alertLevel',
            'last_eruption': 'lastEruption',
            'insar_url': 'insarUrl'
        }
        
        kwargs = {}
        for field in cls.__dataclass_fields__:
            snake_case = field
            camel_case = key_mapping.get(field, field)
            
            # Try both snake_case and camelCase keys
            if snake_case in data:
                kwargs[field] = data[snake_case]
            elif camel_case in data:
                kwargs[field] = data[camel_case]
        
        return cls(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Volcano object to a dictionary
        
        Returns:
            Dict: Dictionary representation of the Volcano
        """
        return {k: v for k, v in self.__dict__.items() if v is not None}