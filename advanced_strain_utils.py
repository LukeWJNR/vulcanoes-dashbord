"""
Advanced Strain Analysis Utilities

This module provides enhanced capabilities for calculating and visualizing crustal strain
data in the context of volcano monitoring. It incorporates algorithms from the Strain_2D toolkit
(https://github.com/kmaterna/Strain_2D) adapted for our specific application.

Original credit for strain calculation methods goes to the Strain_2D authors:
Kathryn Materna and others (https://github.com/kmaterna/Strain_2D)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium


def compute_strain_components(dudx, dvdx, dudy, dvdy):
    """
    Given a displacement tensor, compute the components of the strain tensor.
    
    Args:
        dudx (float): Displacement gradient (du/dx)
        dvdx (float): Displacement gradient (dv/dx)
        dudy (float): Displacement gradient (du/dy)
        dvdy (float): Displacement gradient (dv/dy)
        
    Returns:
        tuple: Strain components (exx, exy, eyy) and rotation
    """
    exx = dudx
    exy = (0.5 * (dvdx + dudy))
    eyy = dvdy
    rot = (0.5 * (dvdx - dudy)) * 1000  # Convert to radians per 1000 years for readability
    
    return exx, exy, eyy, rot


def compute_derived_quantities(exx, exy, eyy):
    """
    Compute derived quantities from strain rate tensor.
    
    Args:
        exx (float): Strain component
        exy (float): Strain component
        eyy (float): Strain component
        
    Returns:
        tuple: Derived quantities (I2nd, dilatation, max_shear)
    """
    # Compute 2nd invariant of strain rate tensor
    I2nd = np.sqrt(0.5 * (exx*exx + eyy*eyy + 2*exy*exy))
    
    # Compute dilatation (1st invariant, trace of the tensor)
    dilatation = exx + eyy
    
    # Max shear strain rate: Radius of Mohr's circle
    max_shear = np.sqrt((0.5 * (exx - eyy))**2 + exy*exy)
    
    return I2nd, dilatation, max_shear


def compute_eigenvectors(exx, exy, eyy):
    """
    Compute eigenvectors and eigenvalues of strain rate tensor.
    
    Args:
        exx (float): Strain component
        exy (float): Strain component
        eyy (float): Strain component
        
    Returns:
        tuple: Eigenvalues (e1, e2) and eigenvectors (v00, v01, v10, v11)
    """
    # Special case: If the tensor is purely diagonal
    if abs(exy) < 1e-6:
        if exx >= eyy:
            e1 = exx
            e2 = eyy
            v00 = 1.0
            v01 = 0.0
            v10 = 0.0
            v11 = 1.0
        else:
            e1 = eyy
            e2 = exx
            v00 = 0.0
            v01 = 1.0
            v10 = 1.0
            v11 = 0.0
    else:
        # General case: Solve the eigensystem
        w, v = np.linalg.eigh(np.array([[exx, exy], [exy, eyy]]))
        e1 = w[1]  # Eigenvalues in ascending order from np.linalg.eigh
        e2 = w[0]
        v00 = v[0, 1]  # Eigenvector corresponding to e1
        v01 = v[1, 1]
        v10 = v[0, 0]  # Eigenvector corresponding to e2
        v11 = v[1, 0]
    
    return e1, e2, v00, v01, v10, v11


def compute_max_shortening_azimuth(e1, e2, v00, v01, v10, v11):
    """
    Compute azimuth of maximum tension/compression.
    
    Args:
        e1 (float): First eigenvalue
        e2 (float): Second eigenvalue
        v00, v01, v10, v11 (float): Eigenvector components
        
    Returns:
        tuple: Azimuths in degrees
    """
    # For v1 (eigenvector corresponding to e1)
    if abs(v00) < 1e-6:  # Avoid division by zero
        if v01 > 0:
            azimuth_v1 = 90.0
        else:
            azimuth_v1 = -90.0
    else:
        azimuth_v1 = np.arctan2(v01, v00) * 180.0 / np.pi
    
    # For v2 (eigenvector corresponding to e2)
    if abs(v10) < 1e-6:
        if v11 > 0:
            azimuth_v2 = 90.0
        else:
            azimuth_v2 = -90.0
    else:
        azimuth_v2 = np.arctan2(v11, v10) * 180.0 / np.pi
    
    # Adjust to range [0, 180)
    azimuth_v1 = azimuth_v1 % 180
    azimuth_v2 = azimuth_v2 % 180
    
    return azimuth_v1, azimuth_v2


def calculate_lava_buildup_index(strain_data, earthquake_data=None, jma_strain_data=None):
    """
    Calculate the Lava Build-Up Index (LBI) for volcano risk assessment.
    
    This index combines crustal strain data with earthquake proximity and strain rate
    time series to estimate potential magma accumulation.
    
    Args:
        strain_data (pd.DataFrame): Strain data from WSM or other sources
        earthquake_data (pd.DataFrame, optional): Recent earthquake data
        jma_strain_data (pd.DataFrame, optional): Time series strain data
        
    Returns:
        dict: LBI values for different volcanic regions
    """
    # Baseline regions
    regions = {
        "Iceland": {"base_strain": 1.2, "base_risk": "High", "lat": 64.9, "lon": -19.0},
        "Hawaii": {"base_strain": 0.9, "base_risk": "Medium", "lat": 19.4, "lon": -155.3},
        "Andes": {"base_strain": 1.0, "base_risk": "Medium", "lat": -23.5, "lon": -67.8},
        "Japan": {"base_strain": 1.4, "base_risk": "High", "lat": 35.6, "lon": 138.2},
        "Indonesia": {"base_strain": 1.1, "base_risk": "High", "lat": -7.5, "lon": 110.0},
        "Mayotte": {"base_strain": 0.7, "base_risk": "Medium", "lat": -12.8, "lon": 45.2}
    }
    
    # Add additional strain analysis if we have data
    if strain_data is not None and not strain_data.empty:
        try:
            # Check if required columns exist
            required_columns = ["latitude", "longitude", "SHmax"]
            missing_columns = [col for col in required_columns if col not in strain_data.columns]
            
            if not missing_columns:
                # Calculate regional strain metrics
                for region_name, region_info in regions.items():
                    try:
                        lat, lon = region_info["lat"], region_info["lon"]
                        
                        # Find strain data points near this region
                        nearby_strain = strain_data[
                            (np.abs(strain_data["latitude"] - lat) < 5) & 
                            (np.abs(strain_data["longitude"] - lon) < 5)
                        ]
                        
                        if not nearby_strain.empty:
                            # Get average strain metrics for region
                            avg_strain = nearby_strain["SHmax"].mean() / 100  # Normalize
                            # Update the base strain with real data
                            regions[region_name]["strain_factor"] = avg_strain
                            regions[region_name]["base_strain"] = regions[region_name]["base_strain"] * (1 + avg_strain)
                    except Exception as e:
                        # If error processing this region, continue with others
                        print(f"Error processing strain data for {region_name}: {e}")
                        continue
        except Exception as e:
            # If error in overall strain processing, just continue with baseline values
            print(f"Error in strain data processing: {e}")
    
    # Add earthquake influence if available
    if earthquake_data is not None and not isinstance(earthquake_data, type(None)):
        for region_name, region_info in regions.items():
            lat, lon = region_info["lat"], region_info["lon"]
            
            # Find earthquakes near this region
            nearby_quakes = earthquake_data[
                (np.abs(earthquake_data["latitude"] - lat) < 2) & 
                (np.abs(earthquake_data["longitude"] - lon) < 2)
            ]
            
            if not nearby_quakes.empty:
                # Calculate earthquake influence
                eq_count = len(nearby_quakes)
                eq_factor = min(1.5, 0.2 + 0.1 * eq_count)  # Cap at 1.5
                regions[region_name]["eq_factor"] = eq_factor
                regions[region_name]["base_strain"] = regions[region_name]["base_strain"] * eq_factor
                
                # Update risk category based on LBI
                lbi = regions[region_name]["base_strain"]
                if lbi > 1.8:
                    regions[region_name]["risk"] = "Critical"
                elif lbi > 1.4:
                    regions[region_name]["risk"] = "High"
                elif lbi > 0.8:
                    regions[region_name]["risk"] = "Medium"
                else:
                    regions[region_name]["risk"] = "Low"
    
    # Add JMA strain time series influence if available
    if jma_strain_data is not None and not isinstance(jma_strain_data, type(None)):
        # Only applies to Japan region
        if "Japan" in regions:
            try:
                # Get recent trend in strain data
                recent_data = jma_strain_data.iloc[-30:]  # Last 30 days
                strain_cols = [col for col in recent_data.columns if col != 'timestamp']
                
                # Calculate average trend across all stations
                trend_factors = []
                for col in strain_cols:
                    if len(recent_data[col]) > 2:  # Need at least 3 points for trend
                        first_half = recent_data[col].iloc[:15].mean()
                        second_half = recent_data[col].iloc[15:].mean()
                        if abs(first_half) > 0:
                            trend = (second_half - first_half) / abs(first_half)
                            trend_factors.append(min(2.0, max(0.5, 1 + trend)))
                
                if trend_factors:
                    jma_factor = sum(trend_factors) / len(trend_factors)
                    regions["Japan"]["jma_factor"] = jma_factor
                    regions["Japan"]["base_strain"] = regions["Japan"]["base_strain"] * jma_factor
                    
                    # Update risk category for Japan
                    lbi = regions["Japan"]["base_strain"]
                    if lbi > 1.8:
                        regions["Japan"]["risk"] = "Critical"
                    elif lbi > 1.4:
                        regions["Japan"]["risk"] = "High"
                    elif lbi > 0.8:
                        regions["Japan"]["risk"] = "Medium"
                    else:
                        regions["Japan"]["risk"] = "Low"
            except Exception as e:
                st.warning(f"Error calculating JMA strain trends: {str(e)}")
    
    # Create final LBI dictionary
    lbi_values = {}
    for region, data in regions.items():
        lbi_values[region] = {
            "lbi": round(data["base_strain"], 2),
            "risk": data.get("risk", data["base_risk"])
        }
    
    return lbi_values


def create_strain_timeseries_plot(strain_data, station):
    """
    Create a time series plot of strain data for a specific station.
    
    Args:
        strain_data (pd.DataFrame): Strain time series data
        station (str): Station identifier
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if 'timestamp' not in strain_data.columns or station not in strain_data.columns:
        return None
    
    # Create the plot
    fig = go.Figure()
    
    # Add strain data line
    fig.add_trace(go.Scatter(
        x=strain_data['timestamp'],
        y=strain_data[station],
        mode='lines',
        name=f'Strain ({station})',
        line=dict(color='purple', width=2)
    ))
    
    # Add trendline if we have enough data
    if len(strain_data) > 10:
        # Get X values as days since start for the regression
        x_days = [(ts - strain_data['timestamp'].iloc[0]).total_seconds() / (24*3600) 
                 for ts in strain_data['timestamp']]
        
        # Simple linear regression
        coeffs = np.polyfit(x_days, strain_data[station], 1)
        trend = np.poly1d(coeffs)
        
        # Calculate trend values at each timestamp
        trend_vals = [trend(x) for x in x_days]
        
        # Add trend line
        fig.add_trace(go.Scatter(
            x=strain_data['timestamp'],
            y=trend_vals,
            mode='lines',
            name='Trend',
            line=dict(color='red', width=1, dash='dash')
        ))
    
    # Calculate 7-day moving average if we have enough data
    if len(strain_data) > 7:
        strain_data['ma7'] = strain_data[station].rolling(window=7).mean()
        
        # Add moving average line
        fig.add_trace(go.Scatter(
            x=strain_data['timestamp'],
            y=strain_data['ma7'],
            mode='lines',
            name='7-day Average',
            line=dict(color='blue', width=1.5)
        ))
    
    # Update layout
    fig.update_layout(
        title=f'Strain Time Series - Station {station}',
        xaxis_title='Date',
        yaxis_title='Strain (ppm)',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def visualize_strain_field(strain_data, lat_center=0, lon_center=0, zoom=2):
    """
    Create a visualization of strain field data using Folium.
    
    Args:
        strain_data (pd.DataFrame): Strain data with lat/lon
        lat_center (float): Center latitude for the map
        lon_center (float): Center longitude for the map
        zoom (int): Initial zoom level
        
    Returns:
        folium.Map: Folium map object with strain visualization
    """
    # Create base map
    m = folium.Map(location=[lat_center, lon_center], zoom_start=zoom, tiles="cartodbpositron")
    
    # Add strain markers
    for _, row in strain_data.iterrows():
        # Get strain components
        azimuth = row.get('SHmax', 0)  # Default to 0 if not present
        magnitude = row.get('SHmag', 1)  # Default to 1 if not present
        
        # Calculate vector endpoints for strain direction
        scale = 0.1 * magnitude  # Scale factor for visualization
        dx = scale * np.cos(np.radians(azimuth))
        dy = scale * np.sin(np.radians(azimuth))
        
        # Create marker with popup information
        html = f"""
        <h4>Strain Data Point</h4>
        <p><b>Lat/Lon:</b> {row['latitude']:.4f}, {row['longitude']:.4f}</p>
        <p><b>SHmax:</b> {row.get('SHmax', 'N/A')}°</p>
        <p><b>SHmag:</b> {row.get('SHmag', 'N/A')}</p>
        <p><b>Quality:</b> {row.get('quality', 'N/A')}</p>
        """
        popup = folium.Popup(html, max_width=300)
        
        # Add marker
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=3,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.7,
            popup=popup
        ).add_to(m)
        
        # Add strain direction vector if we have azimuth
        if 'SHmax' in row:
            folium.PolyLine(
                locations=[
                    [row['latitude'], row['longitude']],
                    [row['latitude'] + dy, row['longitude'] + dx]
                ],
                color='blue',
                weight=1.5,
                opacity=0.7
            ).add_to(m)
    
    return m


def get_strain_legend():
    """
    Get HTML for strain data legend.
    
    Returns:
        str: HTML string with legend content
    """
    return """
    <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
        <h4>Strain Data Legend</h4>
        <p><span style="color: red;">●</span> Strain measurement location</p>
        <p><span style="color: blue;">—</span> Maximum horizontal stress direction</p>
        <p><b>SHmax:</b> Maximum horizontal stress orientation (degrees)</p>
        <p><b>SHmag:</b> Relative magnitude of stress</p>
    </div>
    """


def add_strain_data_to_map(m, strain_data, num_points=200):
    """
    Add strain data markers to a Folium map.
    
    Args:
        m (folium.Map): Folium map object
        strain_data (pd.DataFrame): Strain data
        num_points (int): Number of points to sample (for performance)
        
    Returns:
        folium.Map: Updated map with strain data
    """
    # Sample a subset of points if we have too many
    if len(strain_data) > num_points:
        strain_sample = strain_data.sample(num_points)
    else:
        strain_sample = strain_data
    
    # Create a feature group for strain data
    strain_group = folium.FeatureGroup(name="Crustal Strain", show=True)
    
    # Add strain markers
    for _, row in strain_sample.iterrows():
        # Get strain components if available
        azimuth = row.get('SHmax', 0)
        magnitude = row.get('SHmag', 1)
        
        # Calculate vector endpoints for strain direction
        scale = 0.1 * min(magnitude, 5)  # Scale and cap for visualization
        dx = scale * np.cos(np.radians(azimuth))
        dy = scale * np.sin(np.radians(azimuth))
        
        # Create popup content
        popup_html = f"""
        <h4>Strain Data Point</h4>
        <p><b>Lat/Lon:</b> {row['latitude']:.4f}, {row['longitude']:.4f}</p>
        <p><b>SHmax:</b> {row.get('SHmax', 'N/A')}°</p>
        <p><b>Type:</b> {row.get('type', 'N/A')}</p>
        <p><b>Quality:</b> {row.get('quality', 'N/A')}</p>
        """
        
        # Create popup and add to marker
        popup = folium.Popup(popup_html, max_width=300)
        
        # Add a small circle marker at the point
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=2,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.7,
            popup=popup
        ).add_to(strain_group)
        
        # Add strain direction vector if we have azimuth
        if 'SHmax' in row:
            folium.PolyLine(
                locations=[
                    [row['latitude'], row['longitude']],
                    [row['latitude'] + dy, row['longitude'] + dx]
                ],
                color='blue',
                weight=1.5,
                opacity=0.7
            ).add_to(strain_group)
    
    # Add the strain group to the map
    strain_group.add_to(m)
    
    return m


def calculate_earthquake_risk_index(strain_data, region_name, earthquake_history=None):
    """
    Calculate an earthquake risk index based on crustal strain patterns.
    
    This function evaluates the risk of significant earthquakes in a region based on the
    pattern and magnitude of crustal strain, optionally incorporating earthquake history.
    
    Args:
        strain_data (pd.DataFrame): Dataframe containing strain measurements
        region_name (str): Name of the region to analyze
        earthquake_history (pd.DataFrame, optional): Historical earthquake data
        
    Returns:
        dict: Dictionary containing risk metrics and explanation
    """
    # Define region centers and baseline characteristics
    region_centers = {
        "Iceland": {"lat": 64.9, "lon": -19.0, "base_risk": 0.7, "tectonic_setting": "Divergent/Hotspot"},
        "Hawaii": {"lat": 19.4, "lon": -155.3, "base_risk": 0.5, "tectonic_setting": "Hotspot"},
        "Japan": {"lat": 35.6, "lon": 138.2, "base_risk": 0.9, "tectonic_setting": "Convergent"},
        "Andes": {"lat": -23.5, "lon": -67.8, "base_risk": 0.7, "tectonic_setting": "Convergent"},
        "Indonesia": {"lat": -7.5, "lon": 110.0, "base_risk": 0.85, "tectonic_setting": "Convergent"},
        "Mayotte": {"lat": -12.8, "lon": 45.2, "base_risk": 0.6, "tectonic_setting": "Hotspot"},
        "California": {"lat": 37.8, "lon": -122.4, "base_risk": 0.8, "tectonic_setting": "Transform"},
        "Greece": {"lat": 38.0, "lon": 23.7, "base_risk": 0.75, "tectonic_setting": "Convergent"},
        "Italy": {"lat": 41.9, "lon": 12.5, "base_risk": 0.7, "tectonic_setting": "Convergent"}
    }
    
    if region_name not in region_centers:
        return {
            "risk_score": 5.0,
            "risk_level": "Moderate",
            "explanation": "Unknown region. Using default moderate risk level."
        }
    
    # Get region information
    region_info = region_centers[region_name]
    base_risk = region_info["base_risk"]
    tectonic_setting = region_info["tectonic_setting"]
    
    # Initialize risk factors
    strain_complexity_factor = 1.0
    strain_magnitude_factor = 1.0
    tectonic_factor = 1.0
    climate_factor = 1.0
    
    # Calculate strain complexity if data is available
    if strain_data is not None and not strain_data.empty and 'SHmax' in strain_data.columns:
        try:
            # Filter for data in this region
            lat, lon = region_info["lat"], region_info["lon"]
            # Filter data for this region with proper numpy usage
            regional_strain = strain_data[
                (np.abs(strain_data["latitude"].astype(float) - lat) < 5) & 
                (np.abs(strain_data["longitude"].astype(float) - lon) < 5)
            ]
            
            if not regional_strain.empty:
                # Calculate strain complexity metrics
                azimuth_std = regional_strain['SHmax'].std()
                strain_directions = len(regional_strain['SHmax'].unique())
                
                # High std deviation suggests strain complexity
                # More complex strain field (higher std) = higher earthquake risk
                strain_complexity_factor = min(1.5, 0.8 + (azimuth_std / 90))
                
                # More strain measurement points = better data quality
                confidence_factor = min(1.2, 0.9 + (len(regional_strain) / 100))
                
                # Adjust strain magnitude based on the region's characteristics
                if 'SHmag' in regional_strain.columns:
                    avg_magnitude = regional_strain['SHmag'].mean()
                    strain_magnitude_factor = min(1.5, 0.7 + avg_magnitude / 2)
        except Exception as e:
            # Default to neutral factors if analysis fails
            print(f"Error in strain analysis for earthquake risk: {e}")
    
    # Apply tectonic setting factors
    if tectonic_setting == "Convergent":
        tectonic_factor = 1.3  # Higher risk at convergent boundaries
    elif tectonic_setting == "Divergent/Hotspot":
        tectonic_factor = 1.1  # Moderate risk at divergent boundaries
    elif tectonic_setting == "Transform":
        tectonic_factor = 1.4  # Highest risk at transform fault systems like San Andreas
    elif tectonic_setting == "Hotspot":
        tectonic_factor = 0.9  # Lower risk at pure hotspots
    
    # Apply climate change factors (simplified)
    # Regions with significant ice loss or sea level changes
    if region_name in ["Iceland", "Andes"]:
        climate_factor = 1.15  # Glacial retreat increases earthquake risk
    elif region_name in ["Japan", "Indonesia", "California"]:
        climate_factor = 1.05  # Sea level change affecting coastal areas
    elif region_name in ["Italy", "Greece"]:
        climate_factor = 1.08  # Mediterranean sea level change and drought patterns
    
    # Calculate final risk score (0-10 scale)
    risk_base = base_risk * strain_complexity_factor * strain_magnitude_factor * tectonic_factor * climate_factor
    risk_score = min(10.0, risk_base * 10)
    
    # Determine risk level
    if risk_score < 3:
        risk_level = "Low"
        color = "green"
    elif risk_score < 5:
        risk_level = "Moderate"
        color = "blue"
    elif risk_score < 7:
        risk_level = "High"
        color = "orange"
    else:
        risk_level = "Critical"
        color = "red"
    
    # Generate explanation text
    factors = []
    if strain_complexity_factor > 1.1:
        factors.append("complex strain patterns")
    if strain_magnitude_factor > 1.1:
        factors.append("high strain magnitude")
    if tectonic_factor > 1.1:
        factors.append(f"{tectonic_setting} tectonic setting")
    if climate_factor > 1.05:
        factors.append("climate change effects")
    
    if factors:
        factor_text = ", ".join(factors[:-1])
        if len(factors) > 1:
            factor_text += f" and {factors[-1]}"
        else:
            factor_text = factors[0]
        explanation = f"The {risk_level.lower()} earthquake risk in {region_name} is due to {factor_text}."
    else:
        explanation = f"The {risk_level.lower()} earthquake risk in {region_name} is based on baseline regional characteristics."
    
    # Return comprehensive risk assessment
    return {
        "risk_score": round(risk_score, 1),
        "risk_level": risk_level,
        "color": color,
        "factors": {
            "base_risk": base_risk,
            "strain_complexity": round(strain_complexity_factor, 2),
            "strain_magnitude": round(strain_magnitude_factor, 2),
            "tectonic_setting": round(tectonic_factor, 2),
            "climate_impact": round(climate_factor, 2)
        },
        "explanation": explanation
    }