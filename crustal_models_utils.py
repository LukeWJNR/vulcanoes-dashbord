"""
Crustal Models Utilities for Volcano Dashboard

This module provides integration with real crustal and lithospheric datasets for more
accurate volcanic modeling. It incorporates data on:

1. Crustal thickness from global models
2. Lithospheric thickness variations
3. Compressional and shear wave velocity models
4. Regional variations in crustal properties

These data provide important constraints for simulating crustal deformation responses
to loads such as glacial melting, sea level changes, and volcanic eruptions.
"""

import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from PIL import Image
import io
import folium
from folium.plugins import FloatImage
from streamlit_folium import st_folium

# Dictionary mapping regions to their characteristic crustal properties
# Values derived from published literature and datasets
CRUSTAL_PROPERTIES = {
    "Iceland": {
        "crustal_thickness": 25.0,  # average thickness in km
        "elastic_thickness": 10.0,   # elastic thickness in km
        "young_modulus": 70.0,       # Young's modulus in GPa
        "poisson_ratio": 0.25,       # Poisson's ratio (dimensionless)
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2800.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0", "Iceland_crustal_model"]
    },
    "Hawaii": {
        "crustal_thickness": 18.0,   # km
        "elastic_thickness": 30.0,   # km
        "young_modulus": 80.0,       # GPa
        "poisson_ratio": 0.27,       # dimensionless
        "mantle_density": 3350.0,    # kg/m³
        "crustal_density": 2900.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0", "Hawaii_flexure_model"]
    },
    "Andes": {
        "crustal_thickness": 60.0,   # km
        "elastic_thickness": 40.0,   # km
        "young_modulus": 75.0,       # GPa
        "poisson_ratio": 0.26,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2800.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0", "Andes_crustal_model"]
    },
    "Alaska": {
        "crustal_thickness": 35.0,   # km
        "elastic_thickness": 20.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2750.0,   # kg/m³
        "characteristic_datasets": ["Berg_2020", "Alaska_velocity_model"]
    },
    "Kamchatka": {
        "crustal_thickness": 30.0,   # km
        "elastic_thickness": 15.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2800.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0"]
    },
    "Yellowstone": {
        "crustal_thickness": 40.0,   # km
        "elastic_thickness": 25.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3280.0,    # kg/m³
        "crustal_density": 2750.0,   # kg/m³
        "characteristic_datasets": ["US-Upper-Mantle-Vs", "Yellowstone_model"]
    },
    "Mediterranean": {
        "crustal_thickness": 30.0,   # km
        "elastic_thickness": 15.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2800.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0"]
    },
    "New Zealand": {
        "crustal_thickness": 25.0,   # km
        "elastic_thickness": 15.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2750.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0"]
    },
    "Japan": {
        "crustal_thickness": 35.0,   # km
        "elastic_thickness": 20.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2800.0,   # kg/m³
        "characteristic_datasets": ["Litho1.0"]
    },
    "Custom Location": {
        "crustal_thickness": 30.0,   # km
        "elastic_thickness": 20.0,   # km
        "young_modulus": 70.0,       # GPa
        "poisson_ratio": 0.25,       # dimensionless
        "mantle_density": 3300.0,    # kg/m³
        "crustal_density": 2800.0,   # kg/m³
        "characteristic_datasets": []
    }
}

# Dictionary mapping dataset names to filenames/resources
CRUSTAL_DATASETS = {
    "Litho1.0": "Litho1.0_1745178512125.png",
    "CVM-H": "CVM-H_comp_1745178565228.png",
    "US-Upper-Mantle-Vs": "US-Upper-Mantle-Vs.Xie.Chu.Yang.2018_1745178685361.png",
    "Berg_2020": "Berg_2020_1_1745178740814.png",
}

def get_crustal_properties(region_name):
    """
    Get crustal properties for a specific region
    
    Args:
        region_name: Name of the region
        
    Returns:
        Dictionary containing crustal properties for that region
    """
    if region_name in CRUSTAL_PROPERTIES:
        return CRUSTAL_PROPERTIES[region_name]
    else:
        return CRUSTAL_PROPERTIES["Custom Location"]

def display_crustal_model_info(region_name):
    """
    Display information about crustal models for a region
    
    Args:
        region_name: Name of the region
    """
    properties = get_crustal_properties(region_name)
    
    st.write("### Crustal Model Information")
    st.write(f"Region: {region_name}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("#### Physical Properties")
        st.write(f"- **Crustal Thickness**: {properties['crustal_thickness']} km")
        st.write(f"- **Elastic Thickness**: {properties['elastic_thickness']} km")
        st.write(f"- **Young's Modulus**: {properties['young_modulus']} GPa")
        st.write(f"- **Poisson's Ratio**: {properties['poisson_ratio']}")
        st.write(f"- **Mantle Density**: {properties['mantle_density']} kg/m³")
        st.write(f"- **Crustal Density**: {properties['crustal_density']} kg/m³")
    
    with col2:
        st.write("#### Regional Characteristics")
        if region_name == "Iceland":
            st.write("- Thin crust due to mid-ocean ridge")
            st.write("- Active volcanic zones")
            st.write("- High geothermal gradients")
        elif region_name == "Hawaii":
            st.write("- Oceanic hot spot")
            st.write("- Significant lithospheric flexure")
            st.write("- Shield volcanoes")
        elif region_name == "Andes":
            st.write("- Thick continental crust")
            st.write("- Subduction zone volcanism")
            st.write("- High elevation plateau")
        elif region_name == "Alaska":
            st.write("- Complex tectonic setting")
            st.write("- Subduction-related volcanism")
            st.write("- Glacial unloading effects")
        elif region_name == "Yellowstone":
            st.write("- Continental hot spot")
            st.write("- Major caldera systems")
            st.write("- High heat flow")

def load_crustal_dataset_image(dataset_name):
    """
    Load a crustal dataset image
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        PIL Image object
    """
    if dataset_name in CRUSTAL_DATASETS:
        filename = CRUSTAL_DATASETS[dataset_name]
        try:
            # Try multiple possible locations
            possible_paths = [
                f"data/crustal_models/{filename}",  # Preferred location
                f"attached_assets/{filename}",      # Original location
                f"{filename}"                       # Direct filename
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return Image.open(path)
            
            # If we get here, none of the paths worked
            st.warning(f"Dataset image {filename} not found in any of the expected locations")
            return None
        except Exception as e:
            st.error(f"Error loading dataset image: {e}")
            return None
    return None

def display_crustal_datasets(region_name):
    """
    Display crustal datasets for a region
    
    Args:
        region_name: Name of the region
    """
    properties = get_crustal_properties(region_name)
    datasets = properties.get("characteristic_datasets", [])
    
    if not datasets:
        st.write("No specific crustal datasets available for this region.")
        return
    
    st.write("### Available Crustal Datasets")
    
    for dataset in datasets:
        st.write(f"#### {dataset}")
        image = load_crustal_dataset_image(dataset)
        if image is not None:
            st.image(image, use_column_width=True)
        
        if dataset == "Litho1.0":
            st.write("""
            **LITHO1.0 Global Model**: This model provides global estimates of:
            - Crustal thickness
            - Compressional-wave velocity
            - Upper mantle structure
            - Lithospheric thickness
            
            These values constrain how the crust and upper mantle respond to surface loading changes.
            """)
        elif dataset == "US-Upper-Mantle-Vs":
            st.write("""
            **US Upper Mantle Shear-wave Velocity Model**: This dataset shows:
            - Variations in shear-wave velocity at different depths
            - Areas of potential weakness in the lithosphere
            - Regions susceptible to deformation under loading
            
            Lower velocity regions (red) generally indicate weaker, hotter material that responds 
            more readily to stress changes.
            """)
        elif dataset == "Berg_2020":
            st.write("""
            **Alaska Velocity Structure (Berg 2020)**: This dataset shows:
            - Shear velocity (Vsv) at different depths (1 km, 25 km, 45 km, 100 km)
            - Crustal structure beneath Alaska
            - Areas of potential weakness or strength in the lithosphere
            
            The variations in velocity correspond to different rock types, temperatures, and 
            degrees of partial melting, all of which affect crustal response to loading.
            """)

def apply_crustal_properties_to_simulation(simulation_params, region_name):
    """
    Apply crustal properties from a specific region to simulation parameters
    
    Args:
        simulation_params: Dictionary containing simulation parameters
        region_name: Name of the region
        
    Returns:
        Updated simulation parameters with region-specific crustal properties
    """
    properties = get_crustal_properties(region_name)
    
    # Update elastic parameters based on the region
    simulation_params["elastic_thickness"] = properties["elastic_thickness"]
    simulation_params["young_modulus"] = properties["young_modulus"] * 1e9  # Convert GPa to Pa
    simulation_params["poisson_ratio"] = properties["poisson_ratio"]
    simulation_params["mantle_density"] = properties["mantle_density"]
    simulation_params["crustal_density"] = properties["crustal_density"]
    
    return simulation_params

def display_crustal_model_on_map(region_name, center_lat, center_lon):
    """
    Display a map with crustal model information for a region
    
    Args:
        region_name: Name of the region
        center_lat: Center latitude
        center_lon: Center longitude
        
    Returns:
        Folium map object
    """
    properties = get_crustal_properties(region_name)
    
    # Create a map centered on the specified coordinates
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="OpenStreetMap")
    
    # Add a marker for the center location
    folium.Marker(
        [center_lat, center_lon],
        popup=f"<b>{region_name}</b><br>Crustal thickness: {properties['crustal_thickness']} km<br>Elastic thickness: {properties['elastic_thickness']} km",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    
    # Add a circle indicating the crustal thickness (scaled for visibility)
    folium.Circle(
        [center_lat, center_lon],
        radius=properties['crustal_thickness'] * 1000,  # Convert to meters
        color="blue",
        fill=True,
        fill_opacity=0.2,
        popup="Crustal thickness (scaled)",
    ).add_to(m)
    
    # Add a legend
    legend_html = f"""
    <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3);">
        <p><strong>{region_name} Crustal Model</strong></p>
        <p>Crustal thickness: {properties['crustal_thickness']} km</p>
        <p>Elastic thickness: {properties['elastic_thickness']} km</p>
        <p>Young's modulus: {properties['young_modulus']} GPa</p>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m