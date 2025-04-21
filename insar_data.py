"""
InSAR data utilities for the Volcano Monitoring Dashboard.

This module provides functions for accessing and processing InSAR
(Interferometric Synthetic Aperture Radar) data for volcano monitoring.
"""

from typing import Dict, List, Any, Optional, Tuple

def get_insar_url_for_volcano(volcano_id: str, volcano_name: str) -> str:
    """
    Get the URL for InSAR data for a specific volcano.
    
    Args:
        volcano_id (str): Volcano ID
        volcano_name (str): Volcano name
        
    Returns:
        str: URL to InSAR data
    """
    # In a production environment, this would use a mapping table or API
    # For now, use a generic URL format
    
    # Format the volcano name for the URL
    formatted_name = volcano_name.lower().replace(" ", "_")
    
    # Return the COMET Volcano Portal URL
    return f"https://comet.nerc.ac.uk/volcanoes/{formatted_name}/"

def generate_sentinel_hub_url(latitude: float, longitude: float) -> str:
    """
    Generate a URL to view the volcano area in Sentinel Hub.
    
    Args:
        latitude (float): Volcano latitude
        longitude (float): Volcano longitude
        
    Returns:
        str: Sentinel Hub URL
    """
    return f"https://apps.sentinel-hub.com/eo-browser/?zoom=12&lat={latitude}&lng={longitude}&themeId=DEFAULT-THEME"

def generate_copernicus_url(latitude: float, longitude: float) -> str:
    """
    Generate a URL to view the volcano area in Copernicus Open Access Hub.
    
    Args:
        latitude (float): Volcano latitude
        longitude (float): Volcano longitude
        
    Returns:
        str: Copernicus URL
    """
    # Calculate a small bounding box around the volcano
    lat_delta = 0.1
    lon_delta = 0.1
    
    min_lat = latitude - lat_delta
    max_lat = latitude + lat_delta
    min_lon = longitude - lon_delta
    max_lon = longitude + lon_delta
    
    # Format the coordinates for the Copernicus query string
    footprint = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    
    return f"https://scihub.copernicus.eu/dhus/#/search?footprint={footprint}&platformname=Sentinel-1"

def generate_smithsonian_wms_url(volcano_id: str) -> str:
    """
    Generate a URL to access Smithsonian's WMS data for a volcano.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        str: Smithsonian WMS URL
    """
    return f"https://volcano.si.edu/geoserver/GVP-VSWMS/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=GVP-VSWMS:Volcanoes&SRS=EPSG:4326&STYLES=&WIDTH=768&HEIGHT=384&BBOX=-180,-90,180,90&QUERY_LAYERS=GVP-VSWMS:Volcanoes&FEATURE_COUNT=1&INFO_FORMAT=application/json&FILTER=GVP-VSWMS:Volcanoes/volcano_id={volcano_id}"

def get_recent_insar_data(volcano_id: str) -> List[Dict[str, Any]]:
    """
    Get recent InSAR data for a volcano.
    
    In a production environment, this would fetch data from an API or database.
    For now, we'll return a placeholder message.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        List[Dict[str, Any]]: List of InSAR data entries
    """
    return [
        {
            'volcano_id': volcano_id,
            'message': 'InSAR data would be fetched from a real API in production.',
            'source': 'Placeholder'
        }
    ]