"""
Crustal Strain Utilities for the Volcano Monitoring Dashboard.

This module provides functions for loading, processing, and visualizing crustal strain data
from JMA (Japan Meteorological Agency) borehole strainmeters and World Stress Map data.

The strain data is used for both visualization and as an input to the Lava Build-Up Index
calculation, providing a new dimension of crustal stress monitoring for volcanic risk assessment.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import folium
from folium.plugins import HeatMap
import warnings
from typing import Dict, List, Any, Tuple, Optional
import plotly.graph_objects as go

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_jma_strain_data(filepath: str = 'attached_assets/202303t4.zip') -> pd.DataFrame:
    """
    Load JMA hourly cumulative strain data from the text file format.
    This function is cached to improve performance. The file can be either a .txt
    file or a .zip file containing the text data.
    
    Args:
        filepath (str): Path to the JMA strain data (either text file or zip file)
        
    Returns:
        pd.DataFrame: Processed strain data with timestamps and station measurements
    """
    import zipfile
    
    # Check if the file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"JMA strain data file not found at {filepath}")
    
    # Handle zip files
    if filepath.endswith('.zip'):
        try:
            print(f"Loading strain data from zip file: {filepath}")
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                # Extract first file in the zip archive
                file_list = zip_ref.namelist()
                print(f"Files in zip archive: {file_list}")
                
                if not file_list:
                    raise ValueError(f"No files found in the zip archive at {filepath}")
                
                # Use the first file in the archive
                first_file = file_list[0]
                print(f"Using file {first_file} from zip archive")
                
                with zip_ref.open(first_file) as f:
                    content = f.read().decode('utf-8')
                    print(f"Successfully read {len(content)} bytes from {first_file}")
                    lines = content.splitlines()
        except Exception as e:
            print(f"Detailed error loading strain data from zip: {str(e)}")
            raise ValueError(f"Error extracting strain data from zip file: {str(e)}")
    else:
        # Regular text file handling
        try:
            print(f"Loading strain data from text file: {filepath}")
            with open(filepath, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Detailed error loading strain data from text file: {str(e)}")
            raise ValueError(f"Error reading strain data text file: {str(e)}")
    
    # Extract header information
    year = None
    month = None
    stations = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Extract year and month
        if "MARCH" in line or "APRIL" in line or "MAY" in line or "JUNE" in line:
            parts = line.split()
            year = int(parts[0])
            month_str = parts[1]
            months = {
                "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
                "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
                "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12
            }
            month = months.get(month_str, None)
        
        # Find the header row with station names
        if "DATE HOUR |" in line:
            # Next line has station names
            station_line = lines[i+1].strip()
            stations = station_line.split('|')[1].strip().split()
            # Skip 2 more lines (separator line)
            data_start_line = i + 3
            break
    
    if not year or not month or not stations:
        raise ValueError("Could not parse JMA strain data file header information")
    
    # Process data rows
    data = []
    
    for line_idx in range(data_start_line, len(lines)):
        line = lines[line_idx].strip()
        
        # Skip empty or separator lines
        if not line or line.startswith("----"):
            continue
        
        # Process data lines
        parts = line.split('|')
        if len(parts) >= 2:
            date_hour = parts[0].strip().split()
            
            # Check if this is a valid data line
            if len(date_hour) != 2:
                continue
                
            try:
                day = int(date_hour[0])
                hour = int(date_hour[1])
                
                # Create timestamp
                timestamp = pd.Timestamp(year=year, month=month, day=day, hour=hour)
                
                # Extract strain values
                strain_values = parts[1].strip().split()
                
                # Create row with timestamp and strain values
                row = {'timestamp': timestamp}
                
                for i, station in enumerate(stations):
                    if i < len(strain_values):
                        try:
                            row[station] = float(strain_values[i])
                        except ValueError:
                            row[station] = None
                    else:
                        row[station] = None
                        
                data.append(row)
                
            except (ValueError, IndexError):
                # Skip lines that can't be parsed properly
                continue
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    return df

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_wsm_data(filepath: str = 'attached_assets/wsm2016.xlsx') -> pd.DataFrame:
    """
    Load World Stress Map data from Excel file.
    This function is cached to improve performance.
    
    Args:
        filepath (str): Path to the WSM Excel file
        
    Returns:
        pd.DataFrame: Processed WSM data containing stress field information
    """
    # Check if the file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"World Stress Map data file not found at {filepath}")
    
    # Load the Excel file with specific columns of interest
    try:
        wsm_df = pd.read_excel(
            filepath, 
            sheet_name='WSM 2016',
            usecols=['LAT', 'LON', 'AZI', 'TYPE', 'DEPTH', 'QUALITY', 'REGIME']
        )
        
        # Filter for good quality data
        wsm_df = wsm_df[wsm_df['QUALITY'].isin(['A', 'B', 'C'])]
        
        # Convert types
        wsm_df['LAT'] = pd.to_numeric(wsm_df['LAT'], errors='coerce')
        wsm_df['LON'] = pd.to_numeric(wsm_df['LON'], errors='coerce')
        wsm_df['AZI'] = pd.to_numeric(wsm_df['AZI'], errors='coerce')
        wsm_df['DEPTH'] = pd.to_numeric(wsm_df['DEPTH'], errors='coerce')
        
        # Drop rows with missing coordinates
        wsm_df = wsm_df.dropna(subset=['LAT', 'LON'])
        
        return wsm_df
        
    except Exception as e:
        warnings.warn(f"Error loading World Stress Map data: {str(e)}")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=['LAT', 'LON', 'AZI', 'TYPE', 'DEPTH', 'QUALITY', 'REGIME'])

def add_strain_data_to_map(m: folium.Map, wsm_data: pd.DataFrame, num_points: int = 2000) -> folium.Map:
    """
    Add crustal strain data visualization to a Folium map.
    
    Args:
        m (folium.Map): The Folium map to add data to
        wsm_data (pd.DataFrame): World Stress Map data
        num_points (int): Maximum number of stress indicators to display
        
    Returns:
        folium.Map: Map with added strain data
    """
    if wsm_data.empty:
        return m
    
    # Create a feature group for stress indicators
    strain_group = folium.FeatureGroup(name="Crustal Strain (WSM)", show=False)
    
    # If we have too many points, sample a subset
    if len(wsm_data) > num_points:
        display_data = wsm_data.sample(num_points)
    else:
        display_data = wsm_data
    
    # Define color mapping for different stress regimes
    regime_colors = {
        'NF': 'blue',       # Normal faulting
        'NS': 'lightblue',  # Normal/strike-slip
        'SS': 'green',      # Strike-slip
        'TS': 'orange',     # Thrust/strike-slip
        'TF': 'red',        # Thrust faulting
        'U': 'gray'         # Unknown
    }
    
    # Add markers for each stress measurement
    for _, row in display_data.iterrows():
        lat, lon = row['LAT'], row['LON']
        azimuth = row['AZI']
        regime = row['REGIME'] if not pd.isna(row['REGIME']) else 'U'
        stress_type = row['TYPE']
        depth = row['DEPTH'] if not pd.isna(row['DEPTH']) else 'Unknown'
        quality = row['QUALITY']
        
        # Line length based on quality (better quality = longer line)
        quality_length = {
            'A': 0.5,
            'B': 0.4,
            'C': 0.3,
            'D': 0.2,
            'E': 0.1
        }
        
        length = quality_length.get(quality, 0.2)
        
        # Calculate endpoint coordinates based on azimuth
        # Note: Azimuth is measured clockwise from north
        import math
        rad = math.radians(azimuth)
        dx = math.sin(rad) * length
        dy = math.cos(rad) * length
        
        # Create a line representing the stress direction
        line_points = [
            [lat - dy/2, lon - dx/2],  # Start point
            [lat + dy/2, lon + dx/2]   # End point
        ]
        
        # Color based on regime
        color = regime_colors.get(regime, 'gray')
        
        # Create popup with information
        popup_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h4>Crustal Stress Data</h4>
            <p><strong>Type:</strong> {stress_type}</p>
            <p><strong>Azimuth:</strong> {azimuth}°</p>
            <p><strong>Depth:</strong> {depth} km</p>
            <p><strong>Regime:</strong> {regime}</p>
            <p><strong>Quality:</strong> {quality}</p>
        </div>
        """
        
        # Add a line showing the stress direction
        folium.PolyLine(
            locations=line_points,
            color=color,
            weight=3,
            opacity=0.7,
            popup=folium.Popup(popup_html, max_width=200)
        ).add_to(strain_group)
    
    # Add strain rate heatmap
    heatmap_data = [[row['LAT'], row['LON']] for _, row in display_data.iterrows()]
    
    # Create a separate feature group for the heatmap
    heatmap_group = folium.FeatureGroup(name="Strain Intensity (Heatmap)", show=False)
    
    # Add heatmap to the map
    HeatMap(
        heatmap_data,
        radius=15,
        gradient={'0.4': 'blue', '0.65': 'lime', '0.8': 'yellow', '1.0': 'red'},
        min_opacity=0.5,
        blur=10
    ).add_to(heatmap_group)
    
    # Add feature groups to map
    strain_group.add_to(m)
    heatmap_group.add_to(m)
    
    return m

def get_strain_data_legend() -> str:
    """
    Generate HTML for a legend explaining the crustal strain visualization.
    
    Returns:
        str: HTML for the legend
    """
    legend_html = """
    <div style="background-color: white; padding: 10px; border-radius: 5px; margin-top: 10px;">
        <h4 style="margin-top: 0;">Crustal Strain Legend</h4>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 3px; background-color: blue; margin-right: 10px;"></div>
            <span>Normal Faulting (NF)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 3px; background-color: lightblue; margin-right: 10px;"></div>
            <span>Normal/Strike-slip (NS)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 3px; background-color: green; margin-right: 10px;"></div>
            <span>Strike-slip (SS)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 3px; background-color: orange; margin-right: 10px;"></div>
            <span>Thrust/Strike-slip (TS)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 3px; background-color: red; margin-right: 10px;"></div>
            <span>Thrust Faulting (TF)</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 3px; background-color: gray; margin-right: 10px;"></div>
            <span>Unknown (U)</span>
        </div>
        <p style="margin-top: 10px; font-size: 12px;">
            <strong>Line Direction:</strong> Maximum horizontal stress orientation<br>
            <strong>Line Length:</strong> Data quality (longer = higher quality)<br>
            <strong>Heatmap:</strong> Areas of concentrated strain measurements
        </p>
        <p style="margin-top: 5px; font-size: 10px; font-style: italic;">
            Data Source: World Stress Map 2016 (WSM) and Japan Meteorological Agency (JMA)
        </p>
    </div>
    """
    return legend_html

def create_strain_timeseries_plot(jma_data: pd.DataFrame, station: str = None) -> Optional[Dict[str, Any]]:
    """
    Create a time series plot of strain data for a specific station.
    
    Args:
        jma_data (pd.DataFrame): JMA strain data
        station (str, optional): Station to plot data for. If None, use first available.
        
    Returns:
        Optional[Dict[str, Any]]: Plotly figure data or None if no data available
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    if jma_data.empty:
        return None
    
    # If no station specified, use the first one
    if station is None:
        station_cols = [col for col in jma_data.columns if col != 'timestamp']
        if not station_cols:
            return None
        station = station_cols[0]
    
    # Ensure the station exists in the data
    if station not in jma_data.columns:
        return None
    
    # Create figure
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    
    # Add strain data trace
    fig.add_trace(
        go.Scatter(
            x=jma_data['timestamp'],
            y=jma_data[station],
            mode='lines',
            name=f"{station} Strain",
            line=dict(color='firebrick', width=2)
        )
    )
    
    # Calculate rate of change (derivative) to show rapid changes
    # First convert None values to NaN so diff() can work properly
    strain_data = jma_data[station].copy()
    strain_data = pd.to_numeric(strain_data, errors='coerce')  # Convert to numeric, non-numeric to NaN
    
    # Now we can calculate the diff safely
    strain_change = strain_data.diff()
    
    # Add rate of change trace
    fig.add_trace(
        go.Scatter(
            x=jma_data['timestamp'],
            y=strain_change,
            mode='lines',
            name=f"{station} Strain Rate of Change",
            line=dict(color='royalblue', width=1.5, dash='dash'),
            visible='legendonly'  # Hide by default, can be toggled
        )
    )
    
    # Customize layout
    fig.update_layout(
        title=f"Crustal Strain Time Series - {station}",
        xaxis_title="Date/Time",
        yaxis_title="Strain (1.0E-06)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def get_jma_station_locations() -> Dict[str, Tuple[float, float]]:
    """
    Get the geographic locations of JMA strainmeter stations.
    
    Returns:
        Dict[str, Tuple[float, float]]: Dictionary of station names and their (lat, lon) coordinates
    """
    # These are approximate locations based on public information
    # For a real implementation, accurate coordinates should be obtained
    return {
        "IRAKO": (34.3179, 136.8558),
        "GAMAGO": (34.8547, 139.0375),
        "MIKKAB": (34.7635, 136.3979),
        "TENRYU": (34.8735, 137.8156),
        "KAWANE": (35.1265, 138.0219)
    }

def process_jma_strain_data_for_risk_assessment(jma_data: pd.DataFrame) -> Dict[str, List[float]]:
    """
    Process JMA strain data into a format suitable for the Lava Build-Up Index calculation.
    
    Args:
        jma_data (pd.DataFrame): JMA strain data from load_jma_strain_data()
        
    Returns:
        Dict[str, List[float]]: Dictionary with station names as keys and lists of strain values as values
    """
    # If data is empty, return empty dictionary
    if jma_data.empty:
        return {}
    
    # Get station columns (all non-timestamp columns)
    station_columns = [col for col in jma_data.columns if col != 'timestamp']
    
    # Extract strain data for each station
    strain_data = {}
    for station in station_columns:
        # Convert to numeric and remove NaN values
        values = pd.to_numeric(jma_data[station], errors='coerce')
        # Drop NaN values and convert to list
        values_list = values.dropna().tolist()
        # Only include stations with sufficient data
        if len(values_list) >= 2:  # Need at least 2 points to calculate change
            strain_data[station] = values_list
    
    return strain_data

def create_strain_graph_component(jma_data: pd.DataFrame, station: str = None, height: int = 300) -> Optional[Dict]:
    """
    Create a strain graph component for use in the dashboard.
    This is similar to the TypeScript StrainGraph component.
    
    Args:
        jma_data (pd.DataFrame): JMA strain data
        station (str, optional): Station to display. If None, use first available.
        height (int): Height of the graph in pixels
        
    Returns:
        Optional[Dict]: Plotly figure object or None if no data
    """
    # If no data, return None
    if jma_data.empty:
        return None
    
    # If no station specified, use the first available
    if not station:
        station_cols = [col for col in jma_data.columns if col != 'timestamp']
        if not station_cols:
            return None
        station = station_cols[0]
    
    # Ensure station exists in data
    if station not in jma_data.columns:
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Add strain data
    strain_values = jma_data[station]
    dates = jma_data['timestamp']
    
    # Main strain line
    fig.add_trace(go.Scatter(
        x=dates,
        y=strain_values,
        mode='lines',
        name=f"{station} Strain",
        line=dict(color='firebrick', width=2)
    ))
    
    # Calculate and add the rate of change (derivative)
    strain_data = pd.to_numeric(strain_values, errors='coerce')
    strain_change = strain_data.diff() * 100  # Scale for visibility
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=strain_change,
        mode='lines',
        name='Rate of Change',
        line=dict(color='royalblue', width=1.5, dash='dash'),
        visible='legendonly'  # Hidden by default
    ))
    
    # Update layout
    fig.update_layout(
        title=f"Crustal Strain - {station}",
        xaxis_title="Date",
        yaxis_title="Strain (1.0E-06)",
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig