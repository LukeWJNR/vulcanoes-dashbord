"""
GeoJSON strain utilities for the Volcano Monitoring Dashboard.

This module provides functions to generate, process, and visualize high-resolution
crustal strain data using GeoJSON format for the Climate & Volcanoes page.

These utilities enhance the dashboard's ability to show detailed strain patterns
and their relationship to volcanic activity at up to 10m resolution.
"""

import os
import json
import numpy as np
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from math import radians, cos, sin
import streamlit as st
from typing import Dict, List, Tuple, Any, Optional, Union

@st.cache_data
def convert_to_geojson(
    strain_data: pd.DataFrame, 
    resolution: int = 10
) -> Dict[str, Any]:
    """
    Convert strain data DataFrame to GeoJSON format with specified resolution.
    
    Args:
        strain_data: DataFrame containing strain data with latitude, longitude, SHmax, SHmag
        resolution: Target resolution in meters
        
    Returns:
        GeoJSON dictionary with strain vectors as features
    """
    if strain_data.empty:
        return {"type": "FeatureCollection", "features": []}
        
    # Ensure required columns exist
    required_cols = ['latitude', 'longitude', 'SHmax']
    for col in required_cols:
        if col not in strain_data.columns:
            st.error(f"Required column '{col}' missing from strain data.")
            return {"type": "FeatureCollection", "features": []}
            
    # Add magnitude if missing
    if 'SHmag' not in strain_data.columns:
        strain_data['SHmag'] = 1.0
        
    # Add quality if missing
    if 'quality' not in strain_data.columns:
        strain_data['quality'] = 'C'
    
    # Create GeoJSON features
    features = []
    
    for _, row in strain_data.iterrows():
        try:
            lat = float(row['latitude'])
            lon = float(row['longitude'])
            azimuth = float(row['SHmax'])
            magnitude = float(row['SHmag'])
            quality = str(row['quality']) if 'quality' in row else 'C'
            
            # Calculate strain vector endpoints
            # Using resolution to determine vector length
            # Azimuth is in degrees clockwise from north
            # Converting to cartesian coordinates using spherical math
            scale_factor = magnitude * (resolution / 1000)  # Scale by resolution (km)
            
            # Calculate offset points in cardinal directions
            coords = compute_strain_vector_coordinates(lat, lon, azimuth, scale_factor)
            
            # Create GeoJSON feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "azimuth": azimuth,
                    "magnitude": magnitude,
                    "quality": quality,
                    # Add more properties as needed
                }
            }
            
            features.append(feature)
        except (ValueError, KeyError) as e:
            # Skip this row if there's an issue
            continue
    
    # Create the GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return geojson

def compute_strain_vector_coordinates(
    lat: float, 
    lon: float, 
    azimuth: float,
    scale: float
) -> List[List[float]]:
    """
    Compute strain vector coordinates for a point with given azimuth.
    
    Args:
        lat: Latitude of the point
        lon: Longitude of the point
        azimuth: Direction of maximum horizontal stress (SHmax) in degrees
        scale: Scale factor based on magnitude and resolution
        
    Returns:
        List of coordinate pairs for LineString geometry
    """
    # Convert azimuth to radians
    angle_rad = radians(azimuth)
    
    # Earth's radius in km
    earth_radius = 6371.0
    
    # Compute offsets
    lat_offset = (scale / earth_radius) * cos(angle_rad) * (180 / np.pi)
    lon_offset = (scale / earth_radius) * sin(angle_rad) * (180 / np.pi) / cos(radians(lat))
    
    # For a proper strain tensor representation, we need both endpoints
    end1_lat = lat + lat_offset
    end1_lon = lon + lon_offset
    end2_lat = lat - lat_offset
    end2_lon = lon - lon_offset
    
    # Create coordinate array
    coords = [
        [float(end1_lon), float(end1_lat)],  # GeoJSON uses [lon, lat]
        [float(end2_lon), float(end2_lat)]
    ]
    
    return coords

@st.cache_data
def generate_interpolated_strain_grid(
    strain_data: pd.DataFrame,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    resolution: int = 10000,  # 10km resolution by default
    interpolation_method: str = 'linear'
) -> pd.DataFrame:
    """
    Generate an interpolated grid of strain data at specified resolution.
    
    Args:
        strain_data: DataFrame with latitude, longitude, SHmax and SHmag
        lat_min, lat_max: Latitude bounds
        lon_min, lon_max: Longitude bounds
        resolution: Resolution in meters
        interpolation_method: Method for interpolation ('linear', 'cubic', etc.)
        
    Returns:
        DataFrame with interpolated points for high-resolution strain mapping
    """
    from scipy.interpolate import griddata
    
    if strain_data.empty:
        return pd.DataFrame()
    
    # Calculate grid dimensions based on resolution
    # 111,111 meters is roughly 1 degree at the equator
    meters_per_degree = 111111.0
    
    # Calculate number of points
    lat_degrees = lat_max - lat_min
    lon_degrees = lon_max - lon_min
    
    # Adjust longitude density based on latitude (convergence at poles)
    avg_lat = (lat_min + lat_max) / 2
    lon_scale_factor = cos(radians(avg_lat))
    
    # Calculate grid dimensions
    num_lat_points = max(10, int(lat_degrees * meters_per_degree / resolution))
    num_lon_points = max(10, int(lon_degrees * meters_per_degree * lon_scale_factor / resolution))
    
    # Create the grid
    grid_lats = np.linspace(lat_min, lat_max, num_lat_points)
    grid_lons = np.linspace(lon_min, lon_max, num_lon_points)
    grid_lon, grid_lat = np.meshgrid(grid_lons, grid_lats)
    
    # Flatten the grid coordinates
    points = np.column_stack((strain_data['latitude'].values, strain_data['longitude'].values))
    grid_points = np.column_stack((grid_lat.flatten(), grid_lon.flatten()))
    
    # Interpolate SHmax values
    shmax_values = strain_data['SHmax'].values
    grid_shmax = griddata(points, shmax_values, grid_points, method=interpolation_method, fill_value=np.nan)
    
    # Interpolate SHmag values if available
    if 'SHmag' in strain_data.columns:
        shmag_values = strain_data['SHmag'].values
        grid_shmag = griddata(points, shmag_values, grid_points, method=interpolation_method, fill_value=np.nan)
    else:
        grid_shmag = np.ones_like(grid_shmax)  # Default magnitude of 1
    
    # Create DataFrame from interpolated values
    interpolated_df = pd.DataFrame({
        'latitude': grid_points[:, 0],
        'longitude': grid_points[:, 1],
        'SHmax': grid_shmax,
        'SHmag': grid_shmag,
        'quality': 'I'  # Mark as interpolated
    })
    
    # Remove NaN values
    interpolated_df = interpolated_df.dropna(subset=['SHmax'])
    
    return interpolated_df

def add_geojson_strain_to_map(
    map_obj: folium.Map,
    geojson_data: Dict[str, Any],
    cluster: bool = True
) -> folium.Map:
    """
    Add GeoJSON strain data to a Folium map.
    
    Args:
        map_obj: Folium Map object
        geojson_data: GeoJSON dictionary with strain vectors
        cluster: Whether to cluster the strain vectors for performance
        
    Returns:
        Updated Folium Map object
    """
    if not geojson_data.get('features'):
        st.warning("No GeoJSON strain features to add to the map.")
        return map_obj
    
    # Define a style function for the strain vectors
    def style_function(feature):
        magnitude = feature['properties']['magnitude']
        quality = feature['properties']['quality']
        
        # Color based on quality
        color_map = {
            'A': 'green',
            'B': 'blue',
            'C': 'orange',
            'D': 'gray',
            'I': 'purple'  # Interpolated points
        }
        
        return {
            'color': color_map.get(quality, 'gray'),
            'weight': min(5, max(1, magnitude * 2)),  # Scale line weight by magnitude
            'opacity': 0.8,
            'dashArray': '5, 5' if quality == 'I' else 'none'  # Dashed line for interpolated
        }
    
    # Define popup function
    def popup_function(feature, layer):
        azimuth = feature['properties']['azimuth']
        magnitude = feature['properties']['magnitude']
        quality = feature['properties']['quality']
        
        popup_html = f"""
        <div style="font-family: Arial; width: 150px;">
            <b>Strain Vector</b><br>
            SHmax: {azimuth:.1f}°<br>
            Magnitude: {magnitude:.2f}<br>
            Quality: {quality}
        </div>
        """
        layer.bindPopup(popup_html)
    
    if cluster:
        # Use marker cluster for better performance with large datasets
        marker_cluster = MarkerCluster().add_to(map_obj)
        
        # Add individual vectors to the cluster
        for feature in geojson_data['features']:
            if feature['geometry']['type'] == 'LineString':
                coords = feature['geometry']['coordinates']
                mid_lon = (coords[0][0] + coords[1][0]) / 2
                mid_lat = (coords[0][1] + coords[1][1]) / 2
                
                # Create a mini GeoJSON just for this feature
                mini_geojson = {
                    "type": "FeatureCollection",
                    "features": [feature]
                }
                
                folium.GeoJson(
                    mini_geojson,
                    style_function=style_function,
                    name=f"Strain Vector",
                ).add_to(marker_cluster)
    else:
        # Add all vectors at once (better for small to medium datasets)
        folium.GeoJson(
            geojson_data,
            name="Strain Vectors",
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=['azimuth', 'magnitude', 'quality'],
                aliases=['SHmax Direction:', 'Magnitude:', 'Quality:'],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #F0EFEF;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                """
            ),
        ).add_to(map_obj)
    
    return map_obj

def save_geojson_to_file(
    geojson_data: Dict[str, Any],
    region_name: str,
    resolution: int
) -> str:
    """
    Save GeoJSON data to a file and return the path.
    
    Args:
        geojson_data: GeoJSON dictionary
        region_name: Name of the region (for filename)
        resolution: Resolution in meters (for filename)
        
    Returns:
        Path to the saved file
    """
    # Create data directory if it doesn't exist
    os.makedirs('data/geojson', exist_ok=True)
    
    # Create filename
    filename = f"data/geojson/strain_{region_name.lower().replace(' ', '_')}_{resolution}m.geojson"
    
    # Write to file
    with open(filename, 'w') as f:
        json.dump(geojson_data, f)
    
    return filename

def load_geojson_from_file(filename: str) -> Dict[str, Any]:
    """
    Load GeoJSON data from a file.
    
    Args:
        filename: Path to the GeoJSON file
        
    Returns:
        GeoJSON dictionary
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading GeoJSON file: {str(e)}")
        return {"type": "FeatureCollection", "features": []}

def get_geojson_strain_legend() -> str:
    """
    Get HTML legend for GeoJSON strain data.
    
    Returns:
        HTML string for the legend
    """
    legend_html = """
    <div style="width: 200px; padding: 10px; background-color: white; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.2);">
        <h4 style="margin-top: 0; text-align: center;">Strain Vector Legend</h4>
        <div style="margin-bottom: 5px;">
            <hr style="display: inline-block; width: 30px; height: 2px; background-color: green; vertical-align: middle; margin-right: 5px;">
            <span>Quality A (High)</span>
        </div>
        <div style="margin-bottom: 5px;">
            <hr style="display: inline-block; width: 30px; height: 2px; background-color: blue; vertical-align: middle; margin-right: 5px;">
            <span>Quality B (Good)</span>
        </div>
        <div style="margin-bottom: 5px;">
            <hr style="display: inline-block; width: 30px; height: 2px; background-color: orange; vertical-align: middle; margin-right: 5px;">
            <span>Quality C (Moderate)</span>
        </div>
        <div style="margin-bottom: 5px;">
            <hr style="display: inline-block; width: 30px; height: 2px; background-color: gray; vertical-align: middle; margin-right: 5px;">
            <span>Quality D (Low)</span>
        </div>
        <div style="margin-bottom: 5px;">
            <hr style="display: inline-block; width: 30px; height: 2px; background-color: purple; vertical-align: middle; margin-right: 5px; border-top: 1px dashed;">
            <span>Interpolated</span>
        </div>
        <p style="font-size: 0.8em; margin-top: 10px;">
        Line thickness indicates strain magnitude. Direction shows SHmax orientation.
        </p>
    </div>
    """
    return legend_html