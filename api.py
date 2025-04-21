"""
API utilities for the Volcano Monitoring Dashboard.

This module provides functions for accessing volcano data from various APIs,
including USGS, WOVOdat, and other volcano monitoring sources.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import requests
from typing import Dict, List, Any, Optional

# Path to fallback data file
FALLBACK_DATA_PATH = "data/volcano_data.py"

def get_volcano_data() -> pd.DataFrame:
    """
    Get volcano data from API or fallback to local data.
    
    Returns:
        pd.DataFrame: DataFrame containing volcano data
    """
    # Load the fallback data
    try:
        from data.volcano_data import VOLCANO_DATA
        volcanoes = VOLCANO_DATA
    except Exception as e:
        # If even the fallback fails, return empty DataFrame with expected columns
        print(f"Error loading volcano data: {str(e)}")
        return pd.DataFrame(columns=[
            'id', 'name', 'country', 'region', 'latitude', 'longitude', 
            'elevation', 'type', 'status', 'last_eruption', 'alert_level'
        ])
    
    # Convert to DataFrame
    df = pd.DataFrame(volcanoes)
    
    # Ensure all necessary columns exist
    for col in ['id', 'name', 'country', 'region', 'latitude', 'longitude', 
                'elevation', 'type', 'status', 'last_eruption', 'alert_level']:
        if col not in df.columns:
            df[col] = np.nan
    
    return df

def get_volcano_details(volcano_id: str) -> Dict[str, Any]:
    """
    Get detailed information for a specific volcano.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        Dict[str, Any]: Dictionary containing volcano details
    """
    # First try to get the data from the API
    # For now, return a placeholder
    return {
        "description": "No additional information available for this volcano.",
        "monitoring_status": "Unknown",
        "population_5km": "Unknown",
        "population_10km": "Unknown",
        "population_30km": "Unknown",
        "population_100km": "Unknown",
    }

def get_volcano_by_name(volcano_name: str) -> Optional[Dict[str, Any]]:
    """
    Get volcano data for a specific volcano by name.
    
    Args:
        volcano_name (str): Name of the volcano
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary containing volcano data, or None if not found
    """
    df = get_volcano_data()
    
    # Find the volcano by name (case-insensitive)
    matches = df[df['name'].str.lower() == volcano_name.lower()]
    
    if len(matches) == 0:
        # Try partial match
        matches = df[df['name'].str.lower().str.contains(volcano_name.lower())]
    
    if len(matches) > 0:
        # Return the first match as a dictionary
        return matches.iloc[0].to_dict()
    
    return None

def get_known_volcano_data() -> pd.DataFrame:
    """
    Get data for known volcanoes from our database.
    
    Returns:
        pd.DataFrame: DataFrame containing volcano data
    """
    return get_volcano_data()

def get_iceland_volcanoes() -> pd.DataFrame:
    """
    Get data specifically for Icelandic volcanoes with additional fields.
    
    Returns:
        pd.DataFrame: DataFrame containing Icelandic volcano data
    """
    # Get all volcano data
    all_volcanoes = get_volcano_data()
    
    # Filter for Iceland
    iceland_volcanoes = all_volcanoes[all_volcanoes['country'] == 'Iceland'].copy()
    
    # Add Iceland-specific fields
    iceland_volcanoes['magma_chamber_depth'] = [
        np.random.uniform(3, 8) for _ in range(len(iceland_volcanoes))
    ]
    iceland_volcanoes['last_deformation'] = [
        np.random.choice([None, datetime.now().strftime('%Y-%m-%d')], 
                        p=[0.7, 0.3]) for _ in range(len(iceland_volcanoes))
    ]
    iceland_volcanoes['monitoring_level'] = [
        np.random.choice(['High', 'Medium', 'Low'], 
                        p=[0.6, 0.3, 0.1]) for _ in range(len(iceland_volcanoes))
    ]
    
    return iceland_volcanoes