"""
Map utilities for the Volcano Monitoring Dashboard.

This module provides functions for creating maps, markers, popups,
and other map-related visualizations using Folium.
"""

import folium
from folium.plugins import MarkerCluster
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import random
import json
import math
import streamlit as st
from utils.risk_assessment import calculate_lava_buildup_index
from utils.crustal_strain_utils import create_strain_graph_component

def create_volcano_map(df: pd.DataFrame, include_monitoring_data: bool = False, 
                  show_earthquakes: bool = True, show_swarms: bool = True, show_deformation: bool = True):
    """
    Create a folium map with volcano markers based on the provided DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame containing volcano data
        include_monitoring_data (bool): Whether to include monitoring data layers
        show_earthquakes (bool): Whether to display recent earthquake data (24h)
        show_swarms (bool): Whether to display earthquake swarm data
        show_deformation (bool): Whether to display ground deformation data
        
    Returns:
        folium.Map: Folium map object with volcano markers
    """
    # Create a map centered on the mean of coordinates
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    # If we don't have any volcanoes in the filtered list, use a default center
    if pd.isna(center_lat) or pd.isna(center_lon):
        center_lat, center_lon = 0, 0
    
    # Create the map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=3,
        tiles="CartoDB positron",
        control_scale=True
    )
    
    # Add alternative tile layers
    folium.TileLayer('CartoDB dark_matter', name='Dark Mode').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Satellite'
    ).add_to(m)
    
    # Create a marker cluster for better performance with many markers
    marker_cluster = MarkerCluster(name="Volcanoes").add_to(m)
    
    # Add each volcano as a marker
    for _, row in df.iterrows():
        # Skip rows with missing coordinates
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue
            
        # Determine marker color based on alert level
        alert_level = row.get('alert_level', 'Unknown')
        marker_color = {
            'Normal': 'green',
            'Advisory': 'blue',
            'Watch': 'orange',
            'Warning': 'red',
            'Unknown': 'gray'
        }.get(alert_level, 'gray')
        
        # Create popup content with HTML
        popup_content = create_popup_html(row)
        
        # Create marker with popup
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=row['name'],
            icon=folium.Icon(color=marker_color, icon="fire", prefix="fa")
        ).add_to(marker_cluster)
    
    # Add monitoring data layers if requested
    if include_monitoring_data:
        # Add global SO2 layer
        # Use alternative WMS service for SO2 data that doesn't require authentication
        so2_layer = folium.WmsTileLayer(
            url="https://firms.modaps.eosdis.nasa.gov/wms/key/cdf6b8b8a58c4b2e3faf37b1a59b8b0f/",
            layers="fires_snpp_24",  # Use VIIRS active fire data as a proxy for volcanic activity
            transparent=True,
            control=True,
            name="NASA FIRMS Active Fires (24h)",
            overlay=True,
            show=False,
            fmt="image/png"
        )
        so2_layer.add_to(m)
        
        # Add simulated volcano monitoring points (normally from real API)
        # In a real implementation, this would fetch data from monitoring APIs
        add_monitoring_points(m, df, show_earthquakes, show_swarms, show_deformation)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

from utils.risk_assessment import calculate_lava_buildup_index

def create_popup_html(volcano: pd.Series, include_strain_data: bool = True) -> str:
    """
    Create HTML content for volcano popup.
    
    Args:
        volcano (pd.Series): Row from volcano DataFrame
        include_strain_data (bool): Whether to include strain data information
        
    Returns:
        str: HTML content for popup
    """
    # Get alert level color
    alert_level = volcano.get('alert_level', 'Unknown')
    alert_color = {
        'Normal': '#4CAF50',
        'Advisory': '#2196F3',
        'Watch': '#FF9800',
        'Warning': '#F44336',
        'Unknown': '#9E9E9E'
    }.get(alert_level, '#9E9E9E')
    
    # Calculate Lava Build-Up Index if not already present
    lava_buildup = volcano.get('lava_buildup_index')
    if lava_buildup is None:
        # Calculate it on-the-fly if not pre-calculated
        lava_buildup = calculate_lava_buildup_index(volcano.to_dict())
    
    # Determine color for Lava Build-Up Index
    if lava_buildup >= 7.0:
        lava_color = '#F44336'  # Red for high build-up
    elif lava_buildup >= 5.0:
        lava_color = '#FF9800'  # Orange for moderate-high build-up
    elif lava_buildup >= 3.0:
        lava_color = '#FFEB3B'  # Yellow for moderate build-up
    else:
        lava_color = '#4CAF50'  # Green for low build-up
    
    # Check if strain data is available in session state
    strain_info = ""
    if include_strain_data and 'jma_data' in st.session_state:
        # Get nearest strain station
        from utils.crustal_strain_utils import get_jma_station_locations
        
        # Find closest strain station to this volcano
        volcano_lat = volcano.get('latitude')
        volcano_lon = volcano.get('longitude')
        
        if volcano_lat is not None and volcano_lon is not None:
            stations = get_jma_station_locations()
            closest_station = None
            min_distance = float('inf')
            
            for station, (lat, lon) in stations.items():
                distance = ((lat - volcano_lat) ** 2 + (lon - volcano_lon) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_station = station
            
            # Check if the closest station is close enough (arbitrary threshold)
            if min_distance < 20 and closest_station:  # Within ~2000km (very rough estimation)
                # Get the strain values for this station
                jma_data = st.session_state['jma_data']
                if closest_station in jma_data.columns:
                    # Get the last few values to assess trend
                    recent_values = jma_data[closest_station].tail(24)  # Last 24 hours
                    
                    # Calculate change (simple trend indicator)
                    if len(recent_values) >= 2:
                        first_valid = recent_values.dropna().iloc[0] if not recent_values.dropna().empty else 0
                        last_valid = recent_values.dropna().iloc[-1] if not recent_values.dropna().empty else 0
                        change = last_valid - first_valid
                        
                        # Determine trend and color
                        if abs(change) < 0.01:
                            trend = "Stable"
                            trend_color = "#4CAF50"  # Green
                        elif change > 0:
                            trend = "Expanding"
                            trend_color = "#F44336"  # Red - expansion often precedes eruptions
                        else:
                            trend = "Contracting"
                            trend_color = "#2196F3"  # Blue
                        
                        # Create strain info section
                        strain_info = f"""
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;">
                            <h4 style="margin: 0 0 5px 0; font-size: 14px;">Crustal Strain Data</h4>
                            <p style="margin: 0; font-size: 12px;">
                                <strong>Nearest station:</strong> {closest_station} ({min_distance:.1f}° away)<br>
                                <strong>Trend (24h):</strong> <span style="color: {trend_color};">{trend}</span><br>
                                <strong>Change:</strong> {change:.6f} strain units
                            </p>
                        </div>
                        """
    
    # Create HTML content
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 300px;">
        <h3 style="margin-bottom: 5px;">{volcano['name']}</h3>
        <div style="margin-bottom: 10px;">
            <span style="background-color: {alert_color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-weight: bold;">
                {alert_level}
            </span>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
            <tr>
                <td style="font-weight: bold; padding: 3px; border-bottom: 1px solid #eee;">Type:</td>
                <td style="padding: 3px; border-bottom: 1px solid #eee;">{volcano.get('type', 'Unknown')}</td>
            </tr>
            <tr>
                <td style="font-weight: bold; padding: 3px; border-bottom: 1px solid #eee;">Elevation:</td>
                <td style="padding: 3px; border-bottom: 1px solid #eee;">{volcano.get('elevation', 'Unknown')} m</td>
            </tr>
            <tr>
                <td style="font-weight: bold; padding: 3px; border-bottom: 1px solid #eee;">Status:</td>
                <td style="padding: 3px; border-bottom: 1px solid #eee;">{volcano.get('status', 'Unknown')}</td>
            </tr>
            <tr>
                <td style="font-weight: bold; padding: 3px; border-bottom: 1px solid #eee;">Last Eruption:</td>
                <td style="padding: 3px; border-bottom: 1px solid #eee;">{volcano.get('last_eruption', 'Unknown')}</td>
            </tr>
            <tr>
                <td style="font-weight: bold; padding: 3px; border-bottom: 1px solid #eee;">Country:</td>
                <td style="padding: 3px; border-bottom: 1px solid #eee;">{volcano.get('country', 'Unknown')}</td>
            </tr>
            <tr>
                <td style="font-weight: bold; padding: 3px; border-bottom: 1px solid #eee;">Region:</td>
                <td style="padding: 3px; border-bottom: 1px solid #eee;">{volcano.get('region', 'Unknown')}</td>
            </tr>
            <tr>
                <td style="font-weight: bold; padding: 3px;">Lava Build-Up Index:</td>
                <td style="padding: 3px;">
                    <span style="color: {lava_color}; font-weight: bold;">{lava_buildup}</span>
                    <span style="font-size: 10px; color: #666;">/10</span>
                </td>
            </tr>
        </table>
        {strain_info}
        <div style="font-size: 12px; color: #666; margin-top: 5px;">
            <strong>Data Sources:</strong> USGS, JMA, Volcano Monitoring Dashboard
        </div>
    </div>
    """
    
    return html

def add_monitoring_points(m: folium.Map, volcanoes_df: pd.DataFrame, 
                    show_earthquakes: bool = True, show_swarms: bool = True, 
                    show_deformation: bool = True):
    """
    Add simulated monitoring data points to the map.
    
    In a production environment, this would fetch real-time data from
    monitoring APIs and satellite sources.
    
    Args:
        m (folium.Map): Folium map to add points to
        volcanoes_df (pd.DataFrame): DataFrame of volcanoes for reference
        show_earthquakes (bool): Whether to display recent earthquake data (24h)
        show_swarms (bool): Whether to display earthquake swarm data
        show_deformation (bool): Whether to display ground deformation data
    """
    # Create feature groups for different data types
    so2_group = folium.FeatureGroup(name="SO2 Emissions", show=False)
    ash_group = folium.FeatureGroup(name="Volcanic Ash", show=False)
    radon_group = folium.FeatureGroup(name="Radon Gas Levels", show=False)
    earthquake_group = folium.FeatureGroup(name="Earthquakes (24h)", show=False)
    swarm_group = folium.FeatureGroup(name="Earthquake Swarms", show=False)
    deformation_group = folium.FeatureGroup(name="Ground Deformation", show=False)
    
    # Select up to 10 of the most active volcanoes to show monitoring data
    active_volcanoes = volcanoes_df[volcanoes_df['alert_level'].isin(['Warning', 'Watch', 'Advisory'])]
    if len(active_volcanoes) > 10:
        active_volcanoes = active_volcanoes.sample(10)
    elif len(active_volcanoes) == 0:
        # If no active volcanoes, use up to 5 random ones
        active_volcanoes = volcanoes_df.sample(min(5, len(volcanoes_df)))
    
    # Add SO2 emission points with volumetric data
    for _, volcano in active_volcanoes.iterrows():
        # Skip rows with missing coordinates
        if pd.isna(volcano['latitude']) or pd.isna(volcano['longitude']):
            continue
            
        # Create multiple emission points to show volume/concentration gradient
        num_points = random.randint(3, 8)  # Number of measurement points
        
        # Base SO2 level - higher for more active volcanoes
        base_so2_level = 0
        if volcano['alert_level'] == 'Warning':
            base_so2_level = random.randint(300, 1200)
        elif volcano['alert_level'] == 'Watch':
            base_so2_level = random.randint(100, 600)
        else:
            base_so2_level = random.randint(30, 200)
            
        # Wind direction affects SO2 dispersion
        wind_direction = random.uniform(0, 360)  # Random wind direction in degrees
        wind_speed = random.uniform(5, 30)       # Random wind speed in km/h
        
        # Create a plume of SO2 measurements downwind
        for i in range(num_points):
            # Calculate distance from volcano (further points have lower SO2)
            distance_factor = 1 - (i / num_points)
            
            # Calculate position based on wind direction
            import math
            rad = math.radians(wind_direction)
            distance = i * wind_speed * 0.05  # Spread points based on wind speed
            
            # Add some randomness to the position
            random_offset = random.uniform(-0.1, 0.1)
            
            lat_offset = math.cos(rad) * distance + random_offset
            lon_offset = math.sin(rad) * distance + random_offset
            
            # Calculate SO2 level with distance decay and randomness
            so2_level = int(base_so2_level * distance_factor * random.uniform(0.7, 1.3))
            
            # Volume calculation (tons/day) - simplified model based on SO2 level
            so2_volume = so2_level * random.uniform(1.5, 3.5)
            
            so2_popup = f"""
            <div style="font-family: Arial, sans-serif;">
                <h4>SO2 Emission Measurement</h4>
                <p><strong>Source:</strong> {volcano['name']}</p>
                <p><strong>Concentration:</strong> {so2_level} DU</p>
                <p><strong>Estimated volume:</strong> {so2_volume:.1f} tons/day</p>
                <p><strong>Distance from vent:</strong> {(distance * 20):.1f} km</p>
                <p><strong>Detected:</strong> Within last 24 hours</p>
            </div>
            """
            
            # Determine marker color based on SO2 level
            so2_color = 'green'
            if so2_level > 300:
                so2_color = 'red'
            elif so2_level > 100:
                so2_color = 'orange'
            elif so2_level > 50:
                so2_color = 'blue'
            
            folium.CircleMarker(
                location=[volcano['latitude'] + lat_offset, volcano['longitude'] + lon_offset],
                radius=so2_level / 50,  # Size based on level
                color=so2_color,
                fill=True,
                fill_color=so2_color,
                fill_opacity=0.4,
                popup=folium.Popup(so2_popup, max_width=250),
                tooltip=f"SO2: {so2_level} DU ({so2_volume:.1f} tons/day)"
            ).add_to(so2_group)
    
    # Add ash advisory areas for volcanoes with Warning or Watch alert levels
    warning_volcanoes = active_volcanoes[active_volcanoes['alert_level'].isin(['Warning', 'Watch'])]
    for _, volcano in warning_volcanoes.iterrows():
        # Skip rows with missing coordinates
        if pd.isna(volcano['latitude']) or pd.isna(volcano['longitude']):
            continue
            
        # Create ash cloud polygon (simplified for demo)
        wind_direction = random.uniform(0, 360)  # Random wind direction
        wind_speed = random.uniform(5, 30)       # Random wind speed in km/h
        
        # Calculate ash cloud polygon based on wind
        ash_distance = wind_speed * 20  # Simplified: speed * arbitrary factor
        ash_width = ash_distance / 3    # Width of plume
        
        # Convert direction to radians and calculate coordinates
        import math
        rad = math.radians(wind_direction)
        dx = math.sin(rad) * ash_distance
        dy = math.cos(rad) * ash_distance
        
        # Create polygon coordinates (simple elongated triangle)
        base_lat = volcano['latitude']
        base_lon = volcano['longitude']
        
        # Calculate points for triangle
        dx_perp = math.sin(rad + math.pi/2) * ash_width/2
        dy_perp = math.cos(rad + math.pi/2) * ash_width/2
        
        ash_coords = [
            [base_lat, base_lon],  # Volcano location (apex)
            [base_lat + dy_perp + dy, base_lon + dx_perp + dx],  # End point 1
            [base_lat - dy_perp + dy, base_lon - dx_perp + dx],  # End point 2
        ]
        
        # Add ash cloud polygon
        ash_popup = f"""
        <div style="font-family: Arial, sans-serif;">
            <h4>Volcanic Ash Advisory</h4>
            <p><strong>Source:</strong> {volcano['name']}</p>
            <p><strong>Wind Direction:</strong> {int(wind_direction)}°</p>
            <p><strong>Wind Speed:</strong> {int(wind_speed)} km/h</p>
            <p><strong>Status:</strong> Active ash emission</p>
            <p><strong>Issued:</strong> Within last 24 hours</p>
        </div>
        """
        
        folium.Polygon(
            locations=ash_coords,
            color='purple',
            fill=True,
            fill_color='purple',
            fill_opacity=0.2,
            popup=folium.Popup(ash_popup, max_width=200),
            tooltip=f"Ash from {volcano['name']}"
        ).add_to(ash_group)
    
    # Add radon gas monitoring stations
    for _, volcano in active_volcanoes.iterrows():
        # Skip rows with missing coordinates
        if pd.isna(volcano['latitude']) or pd.isna(volcano['longitude']):
            continue
            
        # Add 1-3 monitoring stations near the volcano
        num_stations = random.randint(1, 3)
        for i in range(num_stations):
            # Randomize location to simulate monitoring stations
            lat_offset = random.uniform(-0.2, 0.2)
            lon_offset = random.uniform(-0.2, 0.2)
            
            # Generate random radon level (in Bq/m³)
            radon_level = random.randint(20, 500)
            
            # Determine color based on radon level
            if radon_level > 300:
                radon_color = 'red'
                status = 'Elevated'
            elif radon_level > 100:
                radon_color = 'orange'
                status = 'Above normal'
            else:
                radon_color = 'green'
                status = 'Normal'
            
            # Create popup content
            radon_popup = f"""
            <div style="font-family: Arial, sans-serif;">
                <h4>Radon Monitoring Station #{i+1}</h4>
                <p><strong>Near:</strong> {volcano['name']}</p>
                <p><strong>Radon level:</strong> {radon_level} Bq/m³</p>
                <p><strong>Status:</strong> {status}</p>
                <p><small>Updated: Within last 24 hours</small></p>
            </div>
            """
            
            folium.Marker(
                location=[volcano['latitude'] + lat_offset, volcano['longitude'] + lon_offset],
                popup=folium.Popup(radon_popup, max_width=200),
                tooltip=f"Radon: {radon_level} Bq/m³",
                icon=folium.Icon(color=radon_color, icon="flask", prefix="fa")
            ).add_to(radon_group)
    
    # Add earthquake data from the last 24 hours (if enabled)
    if show_earthquakes:
        add_recent_earthquakes(earthquake_group, volcanoes_df)
        earthquake_group.add_to(m)
    
    # Add earthquake swarm locations (if enabled)
    if show_swarms:
        add_earthquake_swarms(swarm_group, volcanoes_df)
        swarm_group.add_to(m)
    
    # Add ground deformation data (if enabled)
    if show_deformation:
        add_ground_deformation(deformation_group, volcanoes_df)
        deformation_group.add_to(m)
    
    # Add the basic monitoring data feature groups to the map
    so2_group.add_to(m)
    ash_group.add_to(m)
    radon_group.add_to(m)
    
def fetch_usgs_earthquake_data():
    """
    Fetch real earthquake data from USGS API for the last 7 days.
    
    Returns:
        list: List of earthquake features
    """
    import requests
    from datetime import datetime, timedelta
    
    try:
        # Fetch all earthquakes from the past week (magnitude 2.5+)
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        return data.get('features', [])
    except Exception as e:
        print(f"Error fetching earthquake data: {str(e)}")
        return []

def add_recent_earthquakes(feature_group, volcanoes_df):
    """
    Add earthquake data from the USGS API to the provided feature group.
    
    Args:
        feature_group (folium.FeatureGroup): Feature group to add earthquakes to
        volcanoes_df (pd.DataFrame): DataFrame of volcanoes for reference
    """
    # Try to get real earthquake data from USGS
    earthquake_data = fetch_usgs_earthquake_data()
    
    if earthquake_data:
        # We have real earthquake data
        from datetime import datetime
        
        for eq in earthquake_data:
            try:
                # Extract earthquake properties
                coords = eq['geometry']['coordinates']
                props = eq['properties']
                
                # Extract coordinates (format is [longitude, latitude, depth])
                eq_lon = coords[0]
                eq_lat = coords[1]
                depth = coords[2]
                
                # Get magnitude and format time
                magnitude = props.get('mag', 0)
                
                # Skip very weak earthquakes
                if magnitude < 2.5:
                    continue
                    
                # Calculate time ago
                eq_time = datetime.fromtimestamp(props.get('time', 0) / 1000.0)
                now = datetime.now()
                time_diff = now - eq_time
                hours_ago = time_diff.total_seconds() / 3600
                
                # Determine circle size and color based on magnitude
                radius = magnitude * 3
                
                color = 'green'
                if magnitude >= 5.0:
                    color = 'red'
                elif magnitude >= 4.0:
                    color = 'orange'
                elif magnitude >= 3.0:
                    color = 'yellow'
                
                # Format place information
                place = props.get('place', 'Unknown location')
                
                # Create popup content
                popup_content = f"""
                <div style="font-family: Arial, sans-serif;">
                    <h4>Earthquake</h4>
                    <p><strong>Magnitude:</strong> {magnitude}</p>
                    <p><strong>Depth:</strong> {depth:.1f} km</p>
                    <p><strong>Time:</strong> {hours_ago:.1f} hours ago</p>
                    <p><strong>Location:</strong> {place}</p>
                    <p><a href="{props.get('url', '#')}" target="_blank">USGS Details</a></p>
                </div>
                """
                
                # Add circle marker for earthquake
                folium.CircleMarker(
                    location=[eq_lat, eq_lon],
                    radius=radius,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f"M{magnitude} - {hours_ago:.1f}h ago"
                ).add_to(feature_group)
            except Exception as e:
                print(f"Error processing earthquake: {str(e)}")
                continue
    else:
        # Fallback to simulated earthquakes if USGS data is unavailable
        print("Using simulated earthquake data (USGS API unavailable)")
        # Select random volcanoes to show earthquake activity
        earthquake_volcanoes = volcanoes_df.sample(min(15, len(volcanoes_df)))
        
        # For each selected volcano, create some simulated earthquake events
        for _, volcano in earthquake_volcanoes.iterrows():
            # Skip rows with missing coordinates
            if pd.isna(volcano['latitude']) or pd.isna(volcano['longitude']):
                continue
            
            # Determine number of earthquakes based on alert level
            num_earthquakes = 1  # Default for low activity
            if volcano.get('alert_level') == 'Warning':
                num_earthquakes = random.randint(5, 12)
            elif volcano.get('alert_level') == 'Watch':
                num_earthquakes = random.randint(3, 8)
            elif volcano.get('alert_level') == 'Advisory':
                num_earthquakes = random.randint(2, 5)
            
            # Create earthquake events around the volcano
            for _ in range(num_earthquakes):
                # Random location near volcano
                distance = random.uniform(0.05, 0.5)  # 5-50 km roughly
                angle = random.uniform(0, 2 * 3.14159)  # Random direction
                
                eq_lat = volcano['latitude'] + distance * np.cos(angle)
                eq_lon = volcano['longitude'] + distance * np.sin(angle)
                
                # Random earthquake attributes
                magnitude = round(random.uniform(1.5, 5.5), 1)
                depth = round(random.uniform(1.0, 15.0), 1)
                hours_ago = round(random.uniform(0, 24), 1)
                
                # Determine circle size and color based on magnitude
                radius = magnitude * 3
                
                color = 'green'
                if magnitude >= 4.0:
                    color = 'red'
                elif magnitude >= 3.0:
                    color = 'orange'
                elif magnitude >= 2.0:
                    color = 'yellow'
                
                # Create popup content
                popup_content = f"""
                <div style="font-family: Arial, sans-serif;">
                    <h4>Earthquake (Simulated)</h4>
                    <p><strong>Magnitude:</strong> {magnitude}</p>
                    <p><strong>Depth:</strong> {depth} km</p>
                    <p><strong>Time:</strong> {hours_ago:.1f} hours ago</p>
                    <p><strong>Near:</strong> {volcano['name']}</p>
                    <p><strong>Distance:</strong> ~{int(distance * 100)} km from volcano</p>
                </div>
                """
                
                # Add circle marker for earthquake
                folium.CircleMarker(
                    location=[eq_lat, eq_lon],
                    radius=radius,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_content, max_width=200),
                    tooltip=f"M{magnitude} - {hours_ago:.1f}h ago"
                ).add_to(feature_group)

def add_earthquake_swarms(feature_group, volcanoes_df):
    """
    Add earthquake swarm data to the provided feature group.
    
    Args:
        feature_group (folium.FeatureGroup): Feature group to add swarms to
        volcanoes_df (pd.DataFrame): DataFrame of volcanoes for reference
    """
    # Select volcanoes with higher alert levels for swarms
    swarm_candidates = volcanoes_df[volcanoes_df['alert_level'].isin(['Warning', 'Watch', 'Advisory'])]
    
    # If not enough candidates, add some random ones
    if len(swarm_candidates) < 5:
        additional = volcanoes_df[~volcanoes_df.index.isin(swarm_candidates.index)].sample(min(5, len(volcanoes_df)))
        swarm_candidates = pd.concat([swarm_candidates, additional])
    
    # Select a subset for actual swarms
    swarm_volcanoes = swarm_candidates.sample(min(7, len(swarm_candidates)))
    
    # Create swarms
    for _, volcano in swarm_volcanoes.iterrows():
        # Skip rows with missing coordinates
        if pd.isna(volcano['latitude']) or pd.isna(volcano['longitude']):
            continue
        
        # Determine swarm characteristics based on alert level
        if volcano.get('alert_level') == 'Warning':
            num_events = random.randint(50, 200)
            swarm_type = random.choice(['Magmatic', 'Distal', 'Proximal'])
            max_magnitude = round(random.uniform(3.2, 5.8), 1)
            depth_range = (1.5, 8.0) if swarm_type == 'Magmatic' else (3.0, 15.0)
            duration_days = random.randint(2, 7)
            activity_level = "High"
        elif volcano.get('alert_level') == 'Watch':
            num_events = random.randint(20, 80)
            swarm_type = random.choice(['Magmatic', 'Tectonic', 'Distal'])
            max_magnitude = round(random.uniform(2.5, 4.2), 1)
            depth_range = (2.0, 10.0)
            duration_days = random.randint(1, 5)
            activity_level = "Moderate"
        else:
            num_events = random.randint(5, 30)
            swarm_type = random.choice(['Tectonic', 'Hydrothermal', 'Uncertain'])
            max_magnitude = round(random.uniform(1.8, 3.5), 1)
            depth_range = (3.0, 12.0)
            duration_days = random.randint(1, 3)
            activity_level = "Low"
        
        # Create swarm location
        distance = random.uniform(0.05, 0.4)  # 5-40 km roughly
        angle = random.uniform(0, 2 * 3.14159)  # Random direction
        
        swarm_lat = volcano['latitude'] + distance * np.cos(angle)
        swarm_lon = volcano['longitude'] + distance * np.sin(angle)
        
        # Create detailed HTML for swarm popup
        swarm_details = f"""
        <div style="font-family: Arial, sans-serif; max-width: 350px;">
            <h3>Earthquake Swarm</h3>
            <p><strong>Near:</strong> {volcano['name']}</p>
            <p><strong>Type:</strong> {swarm_type}</p>
            <p><strong>Events:</strong> {num_events} in past {duration_days} days</p>
            <p><strong>Depth range:</strong> {depth_range[0]:.1f} - {depth_range[1]:.1f} km</p>
            <p><strong>Max magnitude:</strong> M{max_magnitude}</p>
            <p><strong>Activity level:</strong> {activity_level}</p>
            <p><strong>Distance from volcano:</strong> ~{int(distance * 100)} km</p>
            
            <div style="margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px;">
                <h4>Activity Timeline (Last 24 Hours)</h4>
                <div style="background-color: #f5f5f5; height: 30px; position: relative; border-radius: 3px;">
        """
        
        # Add timeline markers for recent earthquakes
        for _ in range(min(10, int(num_events / duration_days))):
            hours_ago = random.uniform(0, 24)
            magnitude = round(random.uniform(max(1.0, max_magnitude - 2), max_magnitude), 1)
            position = hours_ago / 24 * 100
            
            # Marker color based on magnitude
            marker_color = "#4CAF50"  # Green
            if magnitude >= max_magnitude - 0.5:
                marker_color = "#F44336"  # Red
            elif magnitude >= max_magnitude - 1.2:
                marker_color = "#FF9800"  # Orange
            
            # Add marker to timeline
            swarm_details += f"""
                    <div style="position: absolute; left: {position}%; top: 0; width: 2px; height: 30px; background-color: {marker_color};" 
                         title="M{magnitude} - {hours_ago:.1f}h ago"></div>
            """
        
        # Complete the timeline and popup HTML
        swarm_details += """
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 3px; font-size: 11px;">
                    <span>24h ago</span>
                    <span>12h ago</span>
                    <span>Now</span>
                </div>
            </div>
            
            <div style="margin-top: 10px; font-size: 12px; color: #666;">
                Data source: Volcano Observatory seismic networks
            </div>
        </div>
        """
        
        # Determine marker color based on activity level
        if activity_level == "High":
            marker_color = "red"
        elif activity_level == "Moderate":
            marker_color = "orange"
        else:
            marker_color = "blue"
        
        # Create icon for swarm
        swarm_icon = folium.Icon(
            color=marker_color,
            icon="bolt",
            prefix="fa"
        )
        
        # Add marker for earthquake swarm
        folium.Marker(
            location=[swarm_lat, swarm_lon],
            icon=swarm_icon,
            popup=folium.Popup(swarm_details, max_width=350),
            tooltip=f"Earthquake Swarm - {num_events} events"
        ).add_to(feature_group)

def add_ground_deformation(feature_group, volcanoes_df):
    """
    Add ground deformation (uplift/subsidence) data to the provided feature group.
    
    Args:
        feature_group (folium.FeatureGroup): Feature group to add deformation data to
        volcanoes_df (pd.DataFrame): DataFrame of volcanoes for reference
    """
    # Select volcanoes to show deformation data
    deformation_candidates = volcanoes_df[volcanoes_df['alert_level'].isin(['Warning', 'Watch'])]
    
    # If not enough candidates, add some with Advisory alert level
    if len(deformation_candidates) < 5:
        additional = volcanoes_df[volcanoes_df['alert_level'] == 'Advisory'].sample(
            min(5 - len(deformation_candidates), len(volcanoes_df[volcanoes_df['alert_level'] == 'Advisory']))
        )
        deformation_candidates = pd.concat([deformation_candidates, additional])
    
    # If still not enough, add random ones
    if len(deformation_candidates) < 5:
        additional = volcanoes_df[~volcanoes_df.index.isin(deformation_candidates.index)].sample(
            min(5 - len(deformation_candidates), len(volcanoes_df))
        )
        deformation_candidates = pd.concat([deformation_candidates, additional])
    
    # Create deformation data
    for _, volcano in deformation_candidates.iterrows():
        # Skip rows with missing coordinates
        if pd.isna(volcano['latitude']) or pd.isna(volcano['longitude']):
            continue
        
        # Determine deformation characteristics based on alert level
        if volcano.get('alert_level') == 'Warning':
            deformation_type = random.choice(['Inflation', 'Inflation', 'Inflation', 'Deflation'])
            rate = random.uniform(15.0, 60.0) # mm/month
            deformation_pattern = random.choice(['Concentric', 'Asymmetric', 'Complex'])
            area_radius = random.uniform(2.0, 8.0)  # km
        elif volcano.get('alert_level') == 'Watch':
            deformation_type = random.choice(['Inflation', 'Inflation', 'Deflation'])
            rate = random.uniform(5.0, 25.0) # mm/month
            deformation_pattern = random.choice(['Concentric', 'Asymmetric', 'Linear'])
            area_radius = random.uniform(1.5, 5.0)  # km
        else:
            deformation_type = random.choice(['Inflation', 'Deflation', 'Stable with localized changes'])
            rate = random.uniform(2.0, 12.0) # mm/month
            deformation_pattern = random.choice(['Concentric', 'Isolated', 'Linear'])
            area_radius = random.uniform(1.0, 3.0)  # km
        
        # Calculate deformation area
        import math
        
        # Create circle of points for deformation area
        center_lat = volcano['latitude']
        center_lon = volcano['longitude']
        
        # Convert radius from km to degrees (approximate)
        radius_deg = area_radius / 111.0  # 1 degree ~ 111 km
        
        # Create points for circle
        circle_points = []
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            lat = center_lat + radius_deg * math.cos(rad)
            lon = center_lon + radius_deg * math.sin(rad)
            circle_points.append([lat, lon])
        
        # Create color based on deformation type
        if deformation_type == 'Inflation':
            color = 'red'
            fill_color = 'red'
        elif deformation_type == 'Deflation':
            color = 'blue'
            fill_color = 'blue'
        else:
            color = 'green'
            fill_color = 'green'
        
        # Create popup content
        deformation_popup = f"""
        <div style="font-family: Arial, sans-serif; max-width: 300px;">
            <h3>Ground Deformation</h3>
            <p><strong>Volcano:</strong> {volcano['name']}</p>
            <p><strong>Type:</strong> {deformation_type}</p>
            <p><strong>Rate:</strong> {rate:.1f} mm/month</p>
            <p><strong>Pattern:</strong> {deformation_pattern}</p>
            <p><strong>Affected area:</strong> ~{area_radius:.1f} km radius</p>
            <p><strong>Data source:</strong> InSAR satellite measurements</p>
            <p><strong>Last measurement:</strong> Within last 24 hours</p>
        </div>
        """
        
        # Add circle for deformation area
        folium.Polygon(
            locations=circle_points,
            color=color,
            weight=2,
            fill=True,
            fill_color=fill_color,
            fill_opacity=0.2,
            popup=folium.Popup(deformation_popup, max_width=300),
            tooltip=f"{deformation_type}: {rate:.1f} mm/month"
        ).add_to(feature_group)