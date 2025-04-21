"""
CrusDe Integration Utilities for Volcano Dashboard

This module provides integration with the CrusDe simulation framework for modeling
crustal deformation due to surface load changes. CrusDe allows simulation of crustal 
response to various loading scenarios such as:
- Melting glaciers
- Sea level changes
- Seasonal snow loads
- Lava flows

The utilities in this module provide a Python interface to CrusDe's simulation
capabilities, allowing users to create, run, and visualize crustal deformation 
simulations directly within the Volcano Dashboard.
"""

import os
import numpy as np
import pandas as pd
import tempfile
import xml.etree.ElementTree as ET
import subprocess
import matplotlib.pyplot as plt
import streamlit as st
import folium
from folium.plugins import TimestampedGeoJson
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px

# Define constants
DEFAULT_ELASTIC_THICKNESS = 30  # km
DEFAULT_YOUNG_MODULUS = 100  # GPa
DEFAULT_POISSON_RATIO = 0.25
DEFAULT_DENSITY_MANTLE = 3300  # kg/m³
DEFAULT_DENSITY_CRUST = 2700  # kg/m³
DEFAULT_GRAVITY = 9.81  # m/s²

# Cache for simulation results
if 'crusde_simulations' not in st.session_state:
    st.session_state['crusde_simulations'] = {}

def create_xml_experiment(name, load_type, load_params, earth_model="elastic", 
                         time_steps=20, duration_years=100, 
                         lat_center=0, lon_center=0,
                         region_width_km=100, region_height_km=100, 
                         resolution_km=1):
    """
    Create an XML experiment definition for CrusDe simulation
    
    Args:
        name: Experiment name
        load_type: Type of load ('disk', 'irregular', 'glacier_melt', 'sea_level', 'lava_flow')
        load_params: Parameters specific to the load type
        earth_model: Earth model to use ('elastic', 'thick_plate', 'relaxed', 'exponential_decay')
        time_steps: Number of time steps in simulation
        duration_years: Total duration of simulation in years
        lat_center, lon_center: Center coordinates of simulation region
        region_width_km, region_height_km: Dimensions of simulation region
        resolution_km: Spatial resolution in kilometers
        
    Returns:
        XML string containing the experiment definition
    """
    # Create the root element
    root = ET.Element("CrusDe")
    root.set("version", "0.3.0")
    
    # Add experiment metadata
    experiment = ET.SubElement(root, "experiment")
    ET.SubElement(experiment, "name").text = name
    ET.SubElement(experiment, "description").text = f"CrusDe simulation of {load_type} effects on crustal deformation"
    
    # Add model configuration
    model = ET.SubElement(root, "model")
    
    # Add Green's function definition based on earth model
    green = ET.SubElement(model, "green")
    if earth_model == "elastic":
        ET.SubElement(green, "plugin").text = "pinel_hs_elastic"
    elif earth_model == "thick_plate":
        ET.SubElement(green, "plugin").text = "pinel_hs_thickplate"
    elif earth_model == "relaxed":
        ET.SubElement(green, "plugin").text = "pinel_hs_final_relaxed"
    elif earth_model == "exponential_decay":
        ET.SubElement(green, "plugin").text = "exponential_decay"
    
    # Add earth model parameters
    params = ET.SubElement(green, "parameters")
    ET.SubElement(params, "parameter", name="elastic_thickness").text = str(DEFAULT_ELASTIC_THICKNESS)
    ET.SubElement(params, "parameter", name="young_modulus").text = str(DEFAULT_YOUNG_MODULUS)
    ET.SubElement(params, "parameter", name="poisson_ratio").text = str(DEFAULT_POISSON_RATIO)
    ET.SubElement(params, "parameter", name="density_mantle").text = str(DEFAULT_DENSITY_MANTLE)
    ET.SubElement(params, "parameter", name="density_crust").text = str(DEFAULT_DENSITY_CRUST)
    ET.SubElement(params, "parameter", name="gravity").text = str(DEFAULT_GRAVITY)
    
    # Add load definition
    load = ET.SubElement(model, "load")
    
    # Configure load based on type
    if load_type == "disk":
        ET.SubElement(load, "plugin").text = "disk"
        load_params_elem = ET.SubElement(load, "parameters")
        ET.SubElement(load_params_elem, "parameter", name="radius_m").text = str(load_params.get("radius_km", 10) * 1000)
        ET.SubElement(load_params_elem, "parameter", name="height_m").text = str(load_params.get("height_m", 100))
        ET.SubElement(load_params_elem, "parameter", name="density_kg_m3").text = str(load_params.get("density_kg_m3", 1000))
        
    elif load_type == "irregular":
        ET.SubElement(load, "plugin").text = "irregular"
        load_params_elem = ET.SubElement(load, "parameters")
        ET.SubElement(load_params_elem, "parameter", name="file").text = load_params.get("file", "load.txt")
        
    elif load_type == "glacier_melt":
        # For glacier melt, we can use a specialized load_history plugin
        ET.SubElement(load, "plugin").text = "disk"  # Base load is a disk
        load_params_elem = ET.SubElement(load, "parameters")
        ET.SubElement(load_params_elem, "parameter", name="radius_m").text = str(load_params.get("radius_km", 10) * 1000)
        ET.SubElement(load_params_elem, "parameter", name="height_m").text = str(load_params.get("initial_height_m", 500))
        ET.SubElement(load_params_elem, "parameter", name="density_kg_m3").text = str(load_params.get("density_kg_m3", 900))  # Ice density
        
        # Add glacial melting load history
        load_history = ET.SubElement(model, "load_history")
        ET.SubElement(load_history, "plugin").text = "linear_decrease"  # Linear decrease for melting
        load_history_params = ET.SubElement(load_history, "parameters")
        ET.SubElement(load_history_params, "parameter", name="duration_years").text = str(duration_years)
        ET.SubElement(load_history_params, "parameter", name="final_fraction").text = str(load_params.get("final_fraction", 0.1))
        
    elif load_type == "sea_level":
        # For sea level, we can use a specialized load_history plugin
        ET.SubElement(load, "plugin").text = "irregular"  # Irregular load for coastline
        load_params_elem = ET.SubElement(load, "parameters")
        ET.SubElement(load_params_elem, "parameter", name="file").text = load_params.get("coastline_file", "coastline.txt")
        
        # Add sea level rise history
        load_history = ET.SubElement(model, "load_history")
        ET.SubElement(load_history, "plugin").text = "linear_increase"  # Linear increase for sea level rise
        load_history_params = ET.SubElement(load_history, "parameters")
        ET.SubElement(load_history_params, "parameter", name="duration_years").text = str(duration_years)
        ET.SubElement(load_history_params, "parameter", name="initial_height_m").text = str(load_params.get("initial_height_m", 0))
        ET.SubElement(load_history_params, "parameter", name="final_height_m").text = str(load_params.get("final_height_m", 1))
        
    elif load_type == "lava_flow":
        # For lava flow, we can use a specialized load_history plugin
        ET.SubElement(load, "plugin").text = "disk"  # Base load is a disk
        load_params_elem = ET.SubElement(load, "parameters")
        ET.SubElement(load_params_elem, "parameter", name="radius_m").text = str(load_params.get("radius_km", 5) * 1000)
        ET.SubElement(load_params_elem, "parameter", name="height_m").text = str(load_params.get("height_m", 50))
        ET.SubElement(load_params_elem, "parameter", name="density_kg_m3").text = str(load_params.get("density_kg_m3", 2700))  # Typical lava density
        
        # Add rapid loading history
        load_history = ET.SubElement(model, "load_history")
        ET.SubElement(load_history, "plugin").text = "step_function"  # Sudden application of load
        load_history_params = ET.SubElement(load_history, "parameters")
        ET.SubElement(load_history_params, "parameter", name="step_time_years").text = str(load_params.get("eruption_time_years", 1))
    
    # Add crustal decay model (if applicable)
    if earth_model == "exponential_decay":
        crustal_decay = ET.SubElement(model, "crustal_decay")
        ET.SubElement(crustal_decay, "plugin").text = "exponential"
        decay_params = ET.SubElement(crustal_decay, "parameters")
        ET.SubElement(decay_params, "parameter", name="tau_years").text = str(load_params.get("decay_time_years", 10))
    
    # Add simulation parameters
    simulation = ET.SubElement(root, "simulation")
    ET.SubElement(simulation, "parameter", name="timesteps").text = str(time_steps)
    ET.SubElement(simulation, "parameter", name="duration_years").text = str(duration_years)
    
    # Add region definition
    region = ET.SubElement(simulation, "region")
    ET.SubElement(region, "parameter", name="center_lat").text = str(lat_center)
    ET.SubElement(region, "parameter", name="center_lon").text = str(lon_center)
    ET.SubElement(region, "parameter", name="width_km").text = str(region_width_km)
    ET.SubElement(region, "parameter", name="height_km").text = str(region_height_km)
    ET.SubElement(region, "parameter", name="resolution_km").text = str(resolution_km)
    
    # Add output configuration
    output = ET.SubElement(root, "output")
    ET.SubElement(output, "plugin").text = "netcdf"
    output_params = ET.SubElement(output, "parameters")
    ET.SubElement(output_params, "parameter", name="filename").text = f"{name}_results.nc"
    
    # Convert to XML string
    return ET.tostring(root, encoding='utf8', method='xml').decode()

def simulate_crustal_response(simulation_params):
    """
    Simulate crustal response using simplified CrusDe approach
    
    This function implements a simplified version of the CrusDe simulation
    that doesn't require the actual CrusDe executable installation.
    
    Args:
        simulation_params: Dictionary containing simulation parameters
        
    Returns:
        Dictionary containing simulation results
    """
    # Extract key simulation parameters
    name = simulation_params["name"]
    timesteps = simulation_params["time_steps"]
    duration_years = simulation_params["duration_years"]
    
    center_lat = simulation_params["lat_center"]
    center_lon = simulation_params["lon_center"]
    width_km = simulation_params["region_width_km"]
    height_km = simulation_params["region_height_km"]
    resolution_km = simulation_params["resolution_km"]
    
    # Extract load parameters
    load_type = simulation_params["load_type"]
    load_params = simulation_params["load_params"]
    
    # Create simulation grid
    lat_min = center_lat - (height_km / 2) / 111  # Approximate degrees per km
    lat_max = center_lat + (height_km / 2) / 111
    lon_min = center_lon - (width_km / 2) / (111 * np.cos(np.radians(center_lat)))
    lon_max = center_lon + (width_km / 2) / (111 * np.cos(np.radians(center_lat)))
    
    lat_steps = int(height_km / resolution_km)
    lon_steps = int(width_km / resolution_km)
    
    lats = np.linspace(lat_min, lat_max, lat_steps)
    lons = np.linspace(lon_min, lon_max, lon_steps)
    
    # Create meshgrid for calculations
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # Initialize results arrays
    vertical_displacement = np.zeros((timesteps, lat_steps, lon_steps))
    horizontal_displacement_e = np.zeros((timesteps, lat_steps, lon_steps))
    horizontal_displacement_n = np.zeros((timesteps, lat_steps, lon_steps))
    strain_xx = np.zeros((timesteps, lat_steps, lon_steps))
    strain_yy = np.zeros((timesteps, lat_steps, lon_steps))
    strain_xy = np.zeros((timesteps, lat_steps, lon_steps))
    
    # Simulate vertical displacement results (synthetic data)
    # Handle different load types
    if load_type == "glacial_unloading" or load_type == "lava_flow_loading" or load_type == "disk":
        # Extract disk parameters
        radius_m = float(load_params.get("radius_m", 10000))
        height_m = float(load_params.get("height_m", 100))
        density = float(load_params.get("density_kg_m3", 1000))
        
        # Calculate effective pressure
        pressure = height_m * density * 9.81  # Pa
        
        # Create time steps
        times = np.linspace(0, duration_years, timesteps)
        
        # Time array
        times = np.linspace(0, duration_years, timesteps)
        
        # For each time step, calculate displacement patterns
        for t in range(timesteps):
            # Calculate time factor (e.g., for melting glacier)
            time_factor = 1.0 - (t / (timesteps - 1))
            
            # For each grid point, calculate distance from center
            for i in range(lat_steps):
                for j in range(lon_steps):
                    lat = lats[i]
                    lon = lons[j]
                    
                    # Calculate distance from center in meters
                    dist_lat = (lat - center_lat) * 111000  # m
                    dist_lon = (lon - center_lon) * 111000 * np.cos(np.radians(center_lat))  # m
                    dist = np.sqrt(dist_lat**2 + dist_lon**2)
                    
                    # Calculate vertical displacement using a basic elastic model
                    # This is a simplified approximation of actual CrusDe computations
                    if dist <= radius_m:
                        # Inside the disk
                        vertical_displacement[t, i, j] = -pressure * time_factor * 1e-7 * (1 - 0.5 * (dist/radius_m)**2)
                    else:
                        # Outside the disk
                        vertical_displacement[t, i, j] = -pressure * time_factor * 1e-7 * (radius_m/dist)**2
                    
                    # Calculate horizontal displacement (simplified model)
                    if dist > 0:
                        horizontal_displacement_e[t, i, j] = pressure * time_factor * 1e-8 * dist_lon/dist
                        horizontal_displacement_n[t, i, j] = pressure * time_factor * 1e-8 * dist_lat/dist
                    
                    # Calculate strain components (simplified derivatives)
                    if i > 0 and j > 0:
                        dx = (horizontal_displacement_e[t, i, j] - horizontal_displacement_e[t, i, j-1]) / (resolution_km * 1000)
                        dy = (horizontal_displacement_n[t, i, j] - horizontal_displacement_n[t, i-1, j]) / (resolution_km * 1000)
                        dxy = (horizontal_displacement_e[t, i, j] - horizontal_displacement_e[t, i-1, j]) / (resolution_km * 1000)
                        dyx = (horizontal_displacement_n[t, i, j] - horizontal_displacement_n[t, i, j-1]) / (resolution_km * 1000)
                        
                        strain_xx[t, i, j] = dx
                        strain_yy[t, i, j] = dy
                        strain_xy[t, i, j] = 0.5 * (dxy + dyx)
    
    # Package results
    results = {
        "name": name,
        "times": np.linspace(0, duration_years, timesteps),
        "lats": lats,
        "lons": lons,
        "vertical_displacement": vertical_displacement,
        "horizontal_displacement_e": horizontal_displacement_e,
        "horizontal_displacement_n": horizontal_displacement_n,
        "strain_xx": strain_xx,
        "strain_yy": strain_yy,
        "strain_xy": strain_xy,
        "parameters": {
            "center_lat": center_lat,
            "center_lon": center_lon,
            "width_km": width_km,
            "height_km": height_km,
            "resolution_km": resolution_km,
            "duration_years": duration_years,
            "timesteps": timesteps
        }
    }
    
    # Cache results
    if 'crusde_simulations' not in st.session_state:
        st.session_state['crusde_simulations'] = {}
    st.session_state['crusde_simulations'][name] = results
    
    return results

def plot_displacement_map(simulation_results, time_index=-1, plot_type="vertical"):
    """
    Create a Folium map visualization of crustal displacement
    
    Args:
        simulation_results: Dictionary containing simulation results
        time_index: Index of time step to visualize (-1 for final state)
        plot_type: Type of plot ("vertical", "horizontal", "strain")
        
    Returns:
        Folium map object
    """
    # Extract parameters from results
    center_lat = simulation_results["parameters"]["center_lat"]
    center_lon = simulation_results["parameters"]["center_lon"]
    
    # Create a Folium map centered on simulation area
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles="OpenStreetMap")
    
    # Add a fullscreen control
    folium.plugins.Fullscreen().add_to(m)
    
    # Extract data for the selected time
    lats = simulation_results["lats"]
    lons = simulation_results["lons"]
    
    # Default values for title and cmap
    title = "Displacement"
    cmap = "viridis"
    
    if plot_type == "vertical":
        data = simulation_results["vertical_displacement"][time_index]
        title = "Vertical Displacement (m)"
        cmap = "RdBu_r"  # Blue for subsidence, red for uplift
    elif plot_type == "horizontal":
        # Calculate horizontal magnitude
        he = simulation_results["horizontal_displacement_e"][time_index]
        hn = simulation_results["horizontal_displacement_n"][time_index]
        data = np.sqrt(he**2 + hn**2)
        title = "Horizontal Displacement Magnitude (m)"
        cmap = "viridis"
    elif plot_type == "strain":
        # Calculate strain magnitude (2nd invariant)
        exx = simulation_results["strain_xx"][time_index]
        eyy = simulation_results["strain_yy"][time_index]
        exy = simulation_results["strain_xy"][time_index]
        data = np.sqrt(0.5 * (exx**2 + eyy**2 + 2 * exy**2))
        title = "Strain Magnitude (microstrain)"
        data = data * 1e6  # Convert to microstrain
        cmap = "magma"
    else:
        # Default to vertical displacement if type not recognized
        data = simulation_results["vertical_displacement"][time_index]
        title = f"Vertical Displacement (m) - Unknown type: {plot_type}"
        cmap = "RdBu_r"
    
    # Create a regular grid of points
    points = []
    values = []
    
    for i in range(len(lats)):
        for j in range(len(lons)):
            points.append([lats[i], lons[j]])
            values.append(data[i, j])
    
    # Add a heatmap layer
    from folium.plugins import HeatMap
    
    # Create pointlist with values as third element in each point
    weighted_points = []
    for i in range(len(points)):
        # Each point in format [lat, lon, value]
        weighted_points.append([points[i][0], points[i][1], values[i]])
    
    HeatMap(
        weighted_points,
        min_opacity=0.2,
        radius=15, 
        blur=10, 
        gradient={0.0: 'blue', 0.5: 'white', 1.0: 'red'} if plot_type == "vertical" else None,
        max_val=np.max(np.abs(data))
    ).add_to(m)
    
    # Add vectors for horizontal displacement if needed
    if plot_type == "horizontal":
        # Subsample for clearer visualization
        stride = max(1, len(lats) // 15)
        
        for i in range(0, len(lats), stride):
            for j in range(0, len(lons), stride):
                magnitude = np.sqrt(
                    simulation_results["horizontal_displacement_e"][time_index, i, j]**2 + 
                    simulation_results["horizontal_displacement_n"][time_index, i, j]**2
                )
                
                # Skip very small vectors
                if magnitude < 0.001:
                    continue
                
                # Calculate arrow endpoint (scaled for visibility)
                dx = simulation_results["horizontal_displacement_e"][time_index, i, j]
                dy = simulation_results["horizontal_displacement_n"][time_index, i, j]
                
                # Normalize and scale
                scale = 0.05 / (max(0.001, magnitude))
                
                end_lat = lats[i] + dy * scale
                end_lon = lons[j] + dx * scale
                
                # Add an arrow marker
                folium.PolyLine(
                    locations=[[lats[i], lons[j]], [end_lat, end_lon]],
                    color='black',
                    weight=2,
                    opacity=0.8
                ).add_to(m)
    
    # Add title
    time_years = simulation_results["times"][time_index]
    
    title_html = f'''
    <div style="position: fixed; 
                top: 10px; 
                left: 50px; 
                width: 300px; 
                height: 60px; 
                z-index:9999; 
                background-color: white; 
                border-radius: 5px; 
                padding: 10px; 
                font-size: 16px;
                box-shadow: 0 0 5px rgba(0,0,0,0.3);">
        <b>{title}</b><br>
        Time: {time_years:.1f} years
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(title_html))
    
    return m

def create_time_slider_map(simulation_results, plot_type="vertical"):
    """
    Create a time-slider map visualization of crustal deformation over time
    
    Args:
        simulation_results: Dictionary containing simulation results
        plot_type: Type of plot ("vertical", "horizontal", "strain")
        
    Returns:
        Folium map object with time slider
    """
    # Extract parameters
    center_lat = simulation_results["parameters"]["center_lat"]
    center_lon = simulation_results["parameters"]["center_lon"]
    
    # Create a basemap
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles="OpenStreetMap")
    
    # Add a fullscreen control
    folium.plugins.Fullscreen().add_to(m)
    
    # Create features for TimestampedGeoJson
    features = []
    
    # Extract data dimensions
    timesteps = len(simulation_results["times"])
    lats = simulation_results["lats"]
    lons = simulation_results["lons"]
    
    # Subsample for better performance
    stride = max(1, len(lats) // 10)
    
    # Generate a feature for each point at each timestamp
    for t in range(timesteps):
        # Extract the date for this time step
        time_years = simulation_results["times"][t]
        date_str = f"2020-01-01T00:00:00+00:00"  # Base date
        
        for i in range(0, len(lats), stride):
            for j in range(0, len(lons), stride):
                # Default values
                value = 0
                radius = 10
                color = "#888888"  # Default gray

                # Get the data value based on plot type
                if plot_type == "vertical":
                    value = simulation_results["vertical_displacement"][t, i, j]
                    radius = abs(value) * 10000  # Scale for visibility
                    if value > 0:
                        color = "#ff0000"  # Red for uplift
                    else:
                        color = "#0000ff"  # Blue for subsidence
                        
                elif plot_type == "horizontal":
                    dx = simulation_results["horizontal_displacement_e"][t, i, j]
                    dy = simulation_results["horizontal_displacement_n"][t, i, j]
                    value = np.sqrt(dx**2 + dy**2)
                    radius = value * 15000  # Scale for visibility
                    color = "#00ff00"  # Green for horizontal
                    
                elif plot_type == "strain":
                    exx = simulation_results["strain_xx"][t, i, j]
                    eyy = simulation_results["strain_yy"][t, i, j]
                    exy = simulation_results["strain_xy"][t, i, j]
                    value = np.sqrt(0.5 * (exx**2 + eyy**2 + 2 * exy**2))
                    radius = value * 1e8  # Scale for visibility
                    color = "#ff00ff"  # Magenta for strain
                else:
                    # Default to vertical displacement if type not recognized
                    value = simulation_results["vertical_displacement"][t, i, j]
                    radius = abs(value) * 10000  # Scale for visibility
                    if value > 0:
                        color = "#ff0000"  # Red for uplift
                    else:
                        color = "#0000ff"  # Blue for subsidence
                
                # Skip very small values
                if radius < 20:
                    continue
                
                # Cap the radius for very large values
                radius = min(5000, radius)
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lons[j], lats[i]]
                    },
                    "properties": {
                        "time": date_str,
                        "icon": "circle",
                        "iconstyle": {
                            "fillColor": color,
                            "fillOpacity": 0.6,
                            "stroke": True,
                            "radius": radius
                        },
                        "value": float(value),
                        "time_years": float(time_years)
                    }
                }
                
                features.append(feature)
    
    # Add the TimestampedGeoJson layer
    folium.plugins.TimestampedGeoJson(
        {
            "type": "FeatureCollection",
            "features": features
        },
        period="P1D",
        duration="P1D",
        auto_play=False,
        loop=False,
        max_speed=1,
        loop_button=True,
        time_slider_drag_update=True
    ).add_to(m)
    
    # Default values
    title = "Displacement"
    legend_html = """
    <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
        <p><strong>Displacement</strong></p>
        <p><span style="color: gray;">●</span> Displacement magnitude</p>
        <p>Circle size proportional to magnitude</p>
    </div>
    """
    
    # Add title and legend based on plot type
    if plot_type == "vertical":
        title = "Vertical Displacement (m)"
        legend_html = """
        <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
            <p><strong>Vertical Displacement</strong></p>
            <p><span style="color: red;">●</span> Uplift</p>
            <p><span style="color: blue;">●</span> Subsidence</p>
            <p>Circle size proportional to magnitude</p>
        </div>
        """
    elif plot_type == "horizontal":
        title = "Horizontal Displacement (m)"
        legend_html = """
        <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
            <p><strong>Horizontal Displacement</strong></p>
            <p><span style="color: green;">●</span> Displacement magnitude</p>
            <p>Circle size proportional to magnitude</p>
        </div>
        """
    elif plot_type == "strain":
        title = "Strain Magnitude (microstrain)"
        legend_html = """
        <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
            <p><strong>Strain Magnitude</strong></p>
            <p><span style="color: magenta;">●</span> Strain (2nd invariant)</p>
            <p>Circle size proportional to magnitude</p>
        </div>
        """
    
    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
        <h3>{title}</h3>
        <p>Use the time slider to animate deformation over time</p>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(title_html))
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def create_plotly_time_series(simulation_results, lat, lon, plot_type="vertical"):
    """
    Create a Plotly time series plot for a specific location
    
    Args:
        simulation_results: Dictionary containing simulation results
        lat, lon: Coordinates of the point to plot
        plot_type: Type of plot ("vertical", "horizontal", "strain")
        
    Returns:
        Plotly figure object
    """
    # Find nearest grid point
    lats = simulation_results["lats"]
    lons = simulation_results["lons"]
    
    lat_idx = np.argmin(np.abs(lats - lat))
    lon_idx = np.argmin(np.abs(lons - lon))
    
    # Extract time series
    times = simulation_results["times"]
    
    # Default values
    data = None
    title = f"Displacement at ({lat:.4f}, {lon:.4f})"
    y_label = "Value"
    
    if plot_type == "vertical":
        data = simulation_results["vertical_displacement"][:, lat_idx, lon_idx]
        title = f"Vertical Displacement at ({lat:.4f}, {lon:.4f})"
        y_label = "Displacement (m)"
    elif plot_type == "horizontal":
        he = simulation_results["horizontal_displacement_e"][:, lat_idx, lon_idx]
        hn = simulation_results["horizontal_displacement_n"][:, lat_idx, lon_idx]
        data = np.sqrt(he**2 + hn**2)
        title = f"Horizontal Displacement at ({lat:.4f}, {lon:.4f})"
        y_label = "Displacement (m)"
    elif plot_type == "strain":
        exx = simulation_results["strain_xx"][:, lat_idx, lon_idx]
        eyy = simulation_results["strain_yy"][:, lat_idx, lon_idx]
        exy = simulation_results["strain_xy"][:, lat_idx, lon_idx]
        data = np.sqrt(0.5 * (exx**2 + eyy**2 + 2 * exy**2)) * 1e6  # Convert to microstrain
        title = f"Strain Magnitude at ({lat:.4f}, {lon:.4f})"
        y_label = "Strain (μstrain)"
    else:
        # Default to vertical displacement if type not recognized
        data = simulation_results["vertical_displacement"][:, lat_idx, lon_idx]
        title = f"Vertical Displacement at ({lat:.4f}, {lon:.4f}) - Unknown type: {plot_type}"
        y_label = "Displacement (m)"
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=times,
        y=data,
        mode='lines+markers',
        name=plot_type.capitalize(),
        line=dict(width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time (years)",
        yaxis_title=y_label,
        template="plotly_white",
        height=500
    )
    
    return fig

def plot_cross_section(simulation_results, start_lat, start_lon, end_lat, end_lon, time_index=-1, plot_type="vertical"):
    """
    Create a cross-section plot along a line between two points
    
    Args:
        simulation_results: Dictionary containing simulation results
        start_lat, start_lon: Starting coordinates
        end_lat, end_lon: Ending coordinates
        time_index: Index of time step to visualize (-1 for final state)
        plot_type: Type of plot ("vertical", "horizontal", "strain")
        
    Returns:
        Plotly figure object
    """
    # Extract data grid
    lats = simulation_results["lats"]
    lons = simulation_results["lons"]
    
    # Create points along the cross-section line
    num_points = 100
    section_lats = np.linspace(start_lat, end_lat, num_points)
    section_lons = np.linspace(start_lon, end_lon, num_points)
    
    # Calculate distances along the cross-section
    distances = np.zeros(num_points)
    for i in range(1, num_points):
        dlat = section_lats[i] - section_lats[i-1]
        dlon = section_lons[i] - section_lons[i-1]
        # Approximate conversion to kilometers
        dist_km = np.sqrt((dlat * 111)**2 + (dlon * 111 * np.cos(np.radians(section_lats[i])))**2)
        distances[i] = distances[i-1] + dist_km
    
    # Interpolate data values along the cross-section
    values = np.zeros(num_points)
    
    # Default values
    data = None
    title = "Displacement Cross-Section"
    y_label = "Value"
    
    if plot_type == "vertical":
        data = simulation_results["vertical_displacement"][time_index]
        title = "Vertical Displacement Cross-Section"
        y_label = "Displacement (m)"
    elif plot_type == "horizontal":
        he = simulation_results["horizontal_displacement_e"][time_index]
        hn = simulation_results["horizontal_displacement_n"][time_index]
        data = np.sqrt(he**2 + hn**2)
        title = "Horizontal Displacement Cross-Section"
        y_label = "Displacement (m)"
    elif plot_type == "strain":
        exx = simulation_results["strain_xx"][time_index]
        eyy = simulation_results["strain_yy"][time_index]
        exy = simulation_results["strain_xy"][time_index]
        data = np.sqrt(0.5 * (exx**2 + eyy**2 + 2 * exy**2)) * 1e6  # Convert to microstrain
        title = "Strain Magnitude Cross-Section"
        y_label = "Strain (μstrain)"
    else:
        # Default to vertical displacement if type not recognized
        data = simulation_results["vertical_displacement"][time_index]
        title = f"Vertical Displacement Cross-Section - Unknown type: {plot_type}"
        y_label = "Displacement (m)"
    
    # Create a 2D interpolation of the data
    from scipy.interpolate import griddata
    
    points = np.vstack((lats.ravel(), lons.ravel())).T
    values_grid = data.ravel()
    
    # Interpolate at cross-section points
    for i in range(num_points):
        values[i] = griddata(points, values_grid, (section_lats[i], section_lons[i]), method='linear')
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=distances,
        y=values,
        mode='lines',
        name=plot_type.capitalize(),
        line=dict(width=3)
    ))
    
    fig.update_layout(
        title=f"{title} at Time = {simulation_results['times'][time_index]:.1f} years",
        xaxis_title="Distance (km)",
        yaxis_title=y_label,
        template="plotly_white",
        height=500
    )
    
    return fig

def plot_3d_surface(simulation_results, time_index=-1, plot_type="vertical", exaggeration=1000):
    """
    Create a 3D surface plot of crustal deformation
    
    Args:
        simulation_results: Dictionary containing simulation results
        time_index: Index of time step to visualize (-1 for final state)
        plot_type: Type of plot ("vertical", "horizontal", "strain")
        exaggeration: Vertical exaggeration factor
        
    Returns:
        Plotly figure object
    """
    # Extract data grid
    lats = simulation_results["lats"]
    lons = simulation_results["lons"]
    
    # Create meshgrid
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # Default values
    z_values = None
    title = "Displacement Surface"
    z_label = "Value"
    colorscale = "Viridis"
    
    # Extract z values based on plot type
    if plot_type == "vertical":
        z_values = simulation_results["vertical_displacement"][time_index]
        title = "Vertical Displacement Surface"
        z_label = "Displacement (m)"
        colorscale = "RdBu_r"
    elif plot_type == "horizontal":
        he = simulation_results["horizontal_displacement_e"][time_index]
        hn = simulation_results["horizontal_displacement_n"][time_index]
        z_values = np.sqrt(he**2 + hn**2)
        title = "Horizontal Displacement Surface"
        z_label = "Displacement (m)"
        colorscale = "Viridis"
    elif plot_type == "strain":
        exx = simulation_results["strain_xx"][time_index]
        eyy = simulation_results["strain_yy"][time_index]
        exy = simulation_results["strain_xy"][time_index]
        z_values = np.sqrt(0.5 * (exx**2 + eyy**2 + 2 * exy**2)) * 1e6  # Convert to microstrain
        title = "Strain Magnitude Surface"
        z_label = "Strain (μstrain)"
        colorscale = "Magma"
    else:
        # Default to vertical displacement if type not recognized
        z_values = simulation_results["vertical_displacement"][time_index]
        title = f"Vertical Displacement Surface - Unknown type: {plot_type}"
        z_label = "Displacement (m)"
        colorscale = "RdBu_r"
    
    # Apply vertical exaggeration
    z_values = z_values * exaggeration
    
    # Create figure
    fig = go.Figure(data=[go.Surface(
        x=lon_grid,
        y=lat_grid,
        z=z_values,
        colorscale=colorscale,
        contours={
            "z": {"show": True, "start": np.min(z_values), "end": np.max(z_values), "size": (np.max(z_values) - np.min(z_values)) / 10}
        }
    )])
    
    fig.update_layout(
        title=f"{title} at Time = {simulation_results['times'][time_index]:.1f} years<br>Vertical exaggeration: {exaggeration}x",
        scene={
            "xaxis": {"title": "Longitude"},
            "yaxis": {"title": "Latitude"},
            "zaxis": {"title": z_label},
            "aspectratio": {"x": 1, "y": 1, "z": 0.5},
            "camera": {"eye": {"x": 1.5, "y": 1.5, "z": 1.2}}
        },
        height=700,
        width=800
    )
    
    return fig

def calculate_volcanic_risk_impact(simulation_results, volcano_lat, volcano_lon, time_index=-1):
    """
    Calculate the impact of crustal deformation on volcanic risk
    
    Args:
        simulation_results: Dictionary containing simulation results
        volcano_lat, volcano_lon: Coordinates of the volcano
        time_index: Index of time step to evaluate (-1 for final state)
        
    Returns:
        Dictionary with risk impact factors
    """
    # Find nearest grid point to volcano
    lats = simulation_results["lats"]
    lons = simulation_results["lons"]
    
    lat_idx = np.argmin(np.abs(lats - volcano_lat))
    lon_idx = np.argmin(np.abs(lons - volcano_lon))
    
    # Extract deformation values at the volcano
    vertical_disp = simulation_results["vertical_displacement"][time_index, lat_idx, lon_idx]
    
    he = simulation_results["horizontal_displacement_e"][time_index, lat_idx, lon_idx]
    hn = simulation_results["horizontal_displacement_n"][time_index, lat_idx, lon_idx]
    horizontal_disp = np.sqrt(he**2 + hn**2)
    
    exx = simulation_results["strain_xx"][time_index, lat_idx, lon_idx]
    eyy = simulation_results["strain_yy"][time_index, lat_idx, lon_idx]
    exy = simulation_results["strain_xy"][time_index, lat_idx, lon_idx]
    strain_mag = np.sqrt(0.5 * (exx**2 + eyy**2 + 2 * exy**2))
    
    # Calculate first spatial derivative of vertical displacement (dilation/compaction)
    dilation_rate = 0
    if lat_idx > 0 and lat_idx < len(lats) - 1 and lon_idx > 0 and lon_idx < len(lons) - 1:
        dvdx = (simulation_results["vertical_displacement"][time_index, lat_idx, lon_idx+1] - 
                simulation_results["vertical_displacement"][time_index, lat_idx, lon_idx-1]) / 2
        dvdy = (simulation_results["vertical_displacement"][time_index, lat_idx+1, lon_idx] - 
                simulation_results["vertical_displacement"][time_index, lat_idx-1, lon_idx]) / 2
        dilation_rate = np.abs(dvdx) + np.abs(dvdy)
    
    # Calculate risk metrics
    
    # 1. Magma chamber pressure change (approximated by vertical displacement)
    # More negative values indicate increasing pressure under compression
    pressure_change = -vertical_disp * 1e6  # Scaled arbitrary units
    
    # 2. Edifice stability impact (related to strain magnitude)
    # Higher values indicate greater potential for structural weakening
    stability_impact = strain_mag * 1e9  # Scaled arbitrary units
    
    # 3. Magma pathway dilation (related to horizontal strain)
    # Higher values suggest greater potential for new or widened pathways
    pathway_dilation = dilation_rate * 1e6  # Scaled arbitrary units
    
    # 4. Combined risk index (weighted sum of factors)
    risk_index = (
        0.4 * np.abs(pressure_change) + 
        0.3 * stability_impact +
        0.3 * pathway_dilation
    )
    
    # Threshold risk level
    risk_level = "Low"
    if risk_index > 10:
        risk_level = "High"
    elif risk_index > 5:
        risk_level = "Medium"
    
    # Package and return results
    impact = {
        "pressure_change": pressure_change,
        "stability_impact": stability_impact,
        "pathway_dilation": pathway_dilation,
        "risk_index": risk_index,
        "risk_level": risk_level,
        "vertical_displacement": vertical_disp,
        "horizontal_displacement": horizontal_disp,
        "strain_magnitude": strain_mag * 1e6  # Convert to microstrain
    }
    
    return impact