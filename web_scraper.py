"""
Web scraping utilities for the Volcano Monitoring Dashboard.

This module provides functions for scraping data from volcano monitoring websites,
including SO2 data, volcanic ash data, and radon measurements.
"""

import requests
from typing import Dict, List, Any, Optional
import random
from datetime import datetime, timedelta

def get_so2_data(latitude: float, longitude: float, radius: float = 50.0) -> List[Dict[str, Any]]:
    """
    Get SO2 data for a given location from satellite sources.
    
    In a production environment, this would fetch real-time data from
    satellite sources like NASA AIRS or OMI.
    
    Args:
        latitude (float): Latitude of the volcano
        longitude (float): Longitude of the volcano
        radius (float): Radius around the volcano to search (in km)
        
    Returns:
        List[Dict[str, Any]]: List of SO2 measurements
    """
    # In a production environment, this would call a real API
    # For now, we'll simulate data
    
    # Random number of data points (1-5)
    num_points = random.randint(1, 5)
    
    # Generate random SO2 data
    so2_data = []
    for _ in range(num_points):
        # Random offset from volcano location
        lat_offset = random.uniform(-0.1, 0.1) * (radius / 50)
        lon_offset = random.uniform(-0.1, 0.1) * (radius / 50)
        
        # Random SO2 level (in Dobson Units)
        so2_level = random.uniform(5, 300)
        
        # Random date within the last 30 days
        days_ago = random.randint(0, 30)
        date_str = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - 
                   timedelta(days=days_ago)).isoformat()
        
        so2_data.append({
            'latitude': latitude + lat_offset,
            'longitude': longitude + lon_offset,
            'so2_level': so2_level,
            'date': date_str,
            'source': 'Satellite imagery (simulated)',
            'unit': 'DU'
        })
    
    return so2_data

def get_volcanic_ash_data(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
    """
    Get volcanic ash advisories for a given location.
    
    In a production environment, this would fetch data from 
    Volcanic Ash Advisory Centers (VAACs).
    
    Args:
        latitude (float): Latitude of the volcano
        longitude (float): Longitude of the volcano
        
    Returns:
        Optional[Dict[str, Any]]: Ash advisory or None if not found
    """
    # In a production environment, this would call a real API
    # For now, we'll simulate data with a 20% chance of an ash advisory
    
    if random.random() < 0.2:
        # Generate a random ash advisory
        wind_direction = random.randint(0, 359)
        wind_speed = random.uniform(5, 50)
        
        return {
            'latitude': latitude,
            'longitude': longitude,
            'advisory_level': random.choice(['Low', 'Medium', 'High']),
            'date': datetime.now().isoformat(),
            'wind_direction': wind_direction,
            'wind_speed': wind_speed,
            'ash_cloud_height': random.uniform(1, 15),
            'source': 'Volcanic Ash Advisory Center (simulated)',
            'description': f'Ash cloud moving in direction {wind_direction}° at {wind_speed:.1f} km/h'
        }
    
    return None

def get_radon_data(latitude: float, longitude: float, radius: float = 20.0) -> List[Dict[str, Any]]:
    """
    Get radon gas measurements around a volcano.
    
    In a production environment, this would fetch data from monitoring stations.
    
    Args:
        latitude (float): Latitude of the volcano
        longitude (float): Longitude of the volcano
        radius (float): Radius around the volcano to search (in km)
        
    Returns:
        List[Dict[str, Any]]: List of radon measurements
    """
    # In a production environment, this would call a real API
    # For now, we'll simulate data
    
    # Random number of stations (0-3)
    num_stations = random.randint(0, 3)
    
    # Generate random radon data
    radon_data = []
    for i in range(num_stations):
        # Random offset from volcano location
        lat_offset = random.uniform(-0.05, 0.05) * (radius / 20)
        lon_offset = random.uniform(-0.05, 0.05) * (radius / 20)
        
        # Random radon level (in Bq/m³)
        radon_level = random.uniform(10, 500)
        
        radon_data.append({
            'station_id': f'RDN{i+1}',
            'latitude': latitude + lat_offset,
            'longitude': longitude + lon_offset,
            'radon_level': radon_level,
            'date': datetime.now().isoformat(),
            'source': 'Monitoring station (simulated)',
            'unit': 'Bq/m³'
        })
    
    return radon_data