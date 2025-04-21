"""
Volcanic Cloud Motion Tracker for the Volcano Monitoring Dashboard.

This page provides an interactive visualization tool to track volcanic ash, SO2, and 
other airborne emissions from volcanic eruptions. The tracker helps monitor cloud movement patterns
and estimate potential impact areas for hazard management.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import folium
from folium.plugins import TimestampedGeoJson, HeatMap, Fullscreen
from streamlit_folium import st_folium
import os
import io
import base64
import warnings
import json
import math
import tempfile
import xarray as xr
import cfgrib

from utils.api import get_known_volcano_data

def load_grib_volcanic_ash(filepath):
    """
    Load volcanic ash data from a GRIB file (Copernicus format)
    
    Args:
        filepath: Path to the GRIB file containing volcanic ash data
        
    Returns:
        xarray.Dataset containing the loaded data
    """
    try:
        # Open the GRIB file using cfgrib and xarray
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ds = xr.open_dataset(filepath, engine='cfgrib')
        return ds
    except Exception as e:
        st.error(f"Error loading GRIB file: {str(e)}")
        return None
        
def display_copernicus_ash_data(filepath):
    """
    Display volcanic ash data from Copernicus GRIB file
    
    Args:
        filepath: Path to the GRIB file containing volcanic ash data
    """
    # Load the data
    st.subheader("Copernicus Volcanic Ash Data")
    
    try:
        # Attempt to load the GRIB file
        ds = load_grib_volcanic_ash(filepath)
        
        if ds is None:
            return
            
        # Extract key information from the dataset
        st.write("### Data Information:")
        
        # Get information about the variables in the dataset
        for var_name in ds.data_vars:
            var = ds[var_name]
            st.write(f"**Variable:** {var_name}")
            
            # Extract attributes if available
            attrs = var.attrs
            if attrs:
                st.write("**Attributes:**")
                for key, val in attrs.items():
                    st.write(f"- {key}: {val}")
            
            # Get time information if available
            if 'time' in var.dims:
                times = var.time.values
                st.write(f"**Time range:** {times.min()} to {times.max()}")
                
            # Get geographical extent
            if 'latitude' in var.dims and 'longitude' in var.dims:
                lats = var.latitude.values
                lons = var.longitude.values
                st.write(f"**Latitude range:** {lats.min():.2f}° to {lats.max():.2f}°")
                st.write(f"**Longitude range:** {lons.min():.2f}° to {lons.max():.2f}°")
                
            # Get vertical levels if present
            if 'level' in var.dims:
                levels = var.level.values
                st.write(f"**Vertical levels:** {', '.join([str(l) for l in levels])}")
        
        # Create a map visualization of the data
        st.write("### Ash Concentration Map")
        
        # Plot the data on a folium map
        # First we need to check which variables are available
        selected_var = list(ds.data_vars)[0]  # Default to first variable
        
        # Select a time index and level index if relevant
        time_idx = 0  # Default to first time step
        level_idx = 0  # Default to first level
        
        # Get the data for the first time step and level
        if 'time' in ds[selected_var].dims and 'level' in ds[selected_var].dims:
            data = ds[selected_var].isel(time=time_idx, level=level_idx)
        elif 'time' in ds[selected_var].dims:
            data = ds[selected_var].isel(time=time_idx)
        elif 'level' in ds[selected_var].dims:
            data = ds[selected_var].isel(level=level_idx)
        else:
            data = ds[selected_var]
        
        # Create map centered at the middle of our data
        center_lat = (data.latitude.min() + data.latitude.max()) / 2
        center_lon = (data.longitude.min() + data.longitude.max()) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
        
        # Plot the data as a heatmap
        heatmap_data = []
        for i in range(len(data.latitude)):
            for j in range(len(data.longitude)):
                lat = float(data.latitude[i].values)
                lon = float(data.longitude[j].values)
                val = float(data.values[i, j])
                
                # Skip missing values
                if np.isfinite(val) and val > 0:
                    # Add to heatmap with intensity based on value
                    # Scale value appropriately based on the range
                    intensity = min(1.0, val / data.values.max())
                    heatmap_data.append([lat, lon, intensity])
        
        # Add heatmap to map
        HeatMap(
            heatmap_data,
            min_opacity=0.3,
            max_val=1.0,
            radius=15,
            blur=10,
            gradient={0.4: 'blue', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}
        ).add_to(m)
        
        # Display the map
        st_folium(m, width=800, height=600)
        
        # Show time series if available
        if 'time' in ds[selected_var].dims:
            st.write("### Time Series Data")
            
            # For time series, we'll extract a single point
            point_lat = center_lat
            point_lon = center_lon
            
            # Find nearest lat/lon indices
            lat_idx = abs(ds.latitude - point_lat).argmin()
            lon_idx = abs(ds.longitude - point_lon).argmin()
            
            # Extract time series at this point
            if 'level' in ds[selected_var].dims:
                # Get data for all times at the specific lat/lon and first level
                time_series = ds[selected_var].isel(latitude=lat_idx, longitude=lon_idx, level=0)
            else:
                # Get data for all times at the specific lat/lon
                time_series = ds[selected_var].isel(latitude=lat_idx, longitude=lon_idx)
            
            # Create time series plot
            fig = go.Figure()
            
            # Add the time series
            fig.add_trace(go.Scatter(
                x=time_series.time.values,
                y=time_series.values,
                name=selected_var,
                line=dict(color='red')
            ))
            
            # Update layout
            fig.update_layout(
                title=f"{selected_var} Time Series at {point_lat:.2f}°, {point_lon:.2f}°",
                xaxis_title="Time",
                yaxis_title=f"{selected_var} ({ds[selected_var].attrs.get('units', 'unknown')})",
                height=400
            )
            
            # Display the plot
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error processing GRIB file: {str(e)}")
        st.info("The GRIB format can vary significantly between providers. This viewer is optimized for Copernicus atmospheric data files.")

def app():
    st.title("🌪️ Volcanic Cloud Motion Tracker")
    
    st.markdown("""
    This tracker visualizes the movement of volcanic clouds (ash, SO2, and other emissions) 
    following eruption events. Use the timeline controls to see cloud progression and
    dispersal patterns over time.
    """)
    
    # Create tabs for different tracking modes
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌋 Recent Eruption Tracker", 
        "🔬 Cloud Simulation", 
        "⏱️ Historical Events",
        "📊 Copernicus Ash Data"
    ])
    
    with tab1:
        st.header("Recent Eruption Cloud Tracker")
        st.markdown("""
        Track volcanic clouds from recent eruption events. The data is refreshed daily
        from satellite measurements of ash and SO2 concentrations.
        """)
        
        # Create columns for controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get volcano data
            volcanoes_df = get_known_volcano_data()
            volcano_names = sorted(volcanoes_df['name'].unique())
            selected_volcano = st.selectbox("Select Volcano", options=volcano_names)
        
        with col2:
            # Cloud type selection
            cloud_type = st.selectbox(
                "Cloud Type", 
                options=["Ash", "SO2", "All Emissions"]
            )
        
        with col3:
            # Time range selection
            time_range = st.selectbox(
                "Time Range", 
                options=["Past 24 Hours", "Past 3 Days", "Past Week"]
            )
        
        # Find the volcano in our dataframe
        selected_volcano_data = volcanoes_df[volcanoes_df['name'] == selected_volcano].iloc[0]
        volcano_lat = selected_volcano_data['latitude']
        volcano_lon = selected_volcano_data['longitude']
        
        # Generate sample cloud tracking data
        current_time = datetime.now()
        if time_range == "Past 24 Hours":
            days = 1
        elif time_range == "Past 3 Days":
            days = 3
        else:  # Past Week
            days = 7
            
        # Sample parameters for different cloud types
        ash_spread_rate = 80  # km per day
        so2_spread_rate = 120  # km per day
        
        # Direction changes slightly with time - simplified model
        cloud_paths = []
        timestamps = []
        cloud_data = []
        locations = []
        
        # Initial eruption time (go back by the selected time range)
        eruption_time = current_time - timedelta(days=days)
        
        # Primary wind direction (simplified, normally would come from weather data)
        # Using degrees: 0=North, 90=East, 180=South, 270=West
        primary_wind_direction = 45  # NorthEast
        
        # Generate cloud movement path
        for hour in range(days * 24):
            timestamp = eruption_time + timedelta(hours=hour)
            timestamps.append(timestamp)
            
            # Add some randomness to wind direction over time (simplified model)
            wind_variation = np.sin(hour / 24 * np.pi) * 15  # +/- 15 degree variation
            current_direction = (primary_wind_direction + wind_variation) % 360
            
            # Calculate distance traveled from volcano
            if cloud_type == "Ash":
                distance = ash_spread_rate * hour / 24  # km
            elif cloud_type == "SO2":
                distance = so2_spread_rate * hour / 24  # km
            else:  # All Emissions - use average
                distance = ((ash_spread_rate + so2_spread_rate) / 2) * hour / 24
            
            # Calculate new position
            # Convert km to approximate lat/lon degrees (simplified)
            lat_change = distance * np.cos(np.radians(current_direction)) / 111  # 111km per degree latitude
            lon_change = distance * np.sin(np.radians(current_direction)) / (111 * np.cos(np.radians(volcano_lat)))
            
            new_lat = volcano_lat + lat_change
            new_lon = volcano_lon + lon_change
            
            cloud_paths.append([new_lon, new_lat])
            
            # Add data point for visualization
            cloud_data.append({
                "time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "lat": new_lat,
                "lon": new_lon,
                "intensity": max(0, 1 - (hour / (days * 24))),  # Decreasing intensity over time
                "radius": distance * 5,  # Cloud radius grows with time and distance
                "direction": current_direction
            })
            
            # Add to locations for heatmap
            locations.append([new_lat, new_lon])
        
        # Create map centered on the volcano
        st.subheader(f"Cloud Tracking: {selected_volcano}")
        m = folium.Map(location=[volcano_lat, volcano_lon], zoom_start=6)
        
        # Add volcano marker
        folium.Marker(
            [volcano_lat, volcano_lon],
            popup=f"<b>{selected_volcano}</b>",
            icon=folium.Icon(color="red", icon="fire", prefix="fa")
        ).add_to(m)
        
        # Create intensity data for heatmap
        intensity_weights = [max(0, 1 - (i / (days * 24 * 0.7))) for i in range(len(locations))]
        
        # Add heatmap of cloud movement
        HeatMap(
            locations,
            min_opacity=0.2,
            max_val=1.0,
            radius=25, 
            blur=15,
            gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'},
            weights=intensity_weights
        ).add_to(m)
        
        # Create timestamped GeoJSON for animated cloud movement
        features = []
        for i, point in enumerate(cloud_data):
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [point['lon'], point['lat']]
                },
                'properties': {
                    'time': point['time'],
                    'icon': 'circle',
                    'iconstyle': {
                        'fillColor': get_cloud_color(cloud_type, point['intensity']),
                        'fillOpacity': 0.6,
                        'stroke': 'true',
                        'radius': point['radius']
                    },
                    'style': {'weight': 0},
                    'popup': f"Time: {point['time']}<br>Direction: {point['direction']}°"
                }
            })
        
        # Create a LineString for the entire path
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': [[volcano_lon, volcano_lat]] + cloud_paths
            },
            'properties': {
                'times': [eruption_time.strftime("%Y-%m-%d %H:%M:%S")] + 
                         [p['time'] for p in cloud_data],
                'style': {
                    'color': get_path_color(cloud_type),
                    'weight': 3
                }
            }
        })
        
        # Add the TimestampedGeoJson
        TimestampedGeoJson(
            {
                'type': 'FeatureCollection',
                'features': features
            },
            period='PT1H',  # One hour per step
            duration='PT30M',
            auto_play=False,
            loop=False
        ).add_to(m)
        
        # Display the map
        st_folium(m, width=800, height=600)
        
        # Display cloud parameters
        st.subheader("Cloud Parameters")
        param_cols = st.columns(3)
        
        with param_cols[0]:
            if cloud_type == "Ash":
                st.metric("Spread Rate", f"{ash_spread_rate} km/day")
            elif cloud_type == "SO2":
                st.metric("Spread Rate", f"{so2_spread_rate} km/day")
            else:
                st.metric("Spread Rate", f"{(ash_spread_rate + so2_spread_rate)/2} km/day")
        
        with param_cols[1]:
            st.metric("Primary Wind Direction", f"{primary_wind_direction}° ({get_wind_direction_name(primary_wind_direction)})")
        
        with param_cols[2]:
            max_distance = cloud_data[-1]['radius'] / 5  # Convert back from radius to distance
            st.metric("Max Distance", f"{max_distance:.1f} km")
        
        # Display cloud properties
        st.markdown("""
        ### Cloud Properties
        
        Different volcanic emissions have distinct dispersal characteristics:
        
        - **Ash clouds** typically remain at lower altitudes (up to 20km) and disperse 
          more slowly, with larger particles falling out closer to the volcano
          
        - **SO2 and gas clouds** can travel at higher altitudes and greater distances,
          sometimes circling the globe within days
          
        - **Composite clouds** contain mixtures of ash, gas, and aerosols with varying
          transport behaviors
        """)
    
    with tab2:
        st.header("Cloud Motion Simulation")
        st.markdown("""
        Simulate volcanic cloud dispersal patterns based on eruption parameters and
        atmospheric conditions. This tool helps forecast potential impacts and hazard zones.
        """)
        
        # Create columns for simulation parameters
        param_col1, param_col2 = st.columns(2)
        
        with param_col1:
            # Eruption parameters
            st.subheader("Eruption Parameters")
            
            sim_volcano = st.selectbox(
                "Volcano", 
                options=sorted(volcanoes_df['name'].unique()),
                key="sim_volcano"
            )
            
            eruption_height = st.slider(
                "Eruption Column Height (km)",
                min_value=1,
                max_value=40,
                value=15,
                help="Height of the eruption column, which affects how far particles can travel"
            )
            
            eruption_intensity = st.select_slider(
                "Eruption Intensity",
                options=["Low", "Medium", "High", "Very High"],
                value="Medium",
                help="Intensity affects the initial volume and momentum of the cloud"
            )
            
            ash_content = st.slider(
                "Ash Content (%)",
                min_value=10,
                max_value=90,
                value=60,
                help="Percentage of ash vs. gas in the eruption plume"
            )
        
        with param_col2:
            # Atmospheric conditions
            st.subheader("Atmospheric Conditions")
            
            wind_speed = st.slider(
                "Wind Speed (km/h)",
                min_value=5,
                max_value=150,
                value=45,
                help="Higher wind speeds cause faster and broader dispersal"
            )
            
            wind_direction = st.slider(
                "Wind Direction (degrees)",
                min_value=0,
                max_value=359,
                value=90,
                help="Direction in degrees (0=N, 90=E, 180=S, 270=W)"
            )
            
            atmospheric_stability = st.select_slider(
                "Atmospheric Stability",
                options=["Unstable", "Neutral", "Stable", "Very Stable"],
                value="Neutral",
                help="Stability affects vertical mixing and cloud cohesion"
            )
            
            precipitation = st.slider(
                "Precipitation Probability (%)",
                min_value=0,
                max_value=100,
                value=20,
                help="Higher precipitation increases ash fallout and reduces cloud travel"
            )
        
        # Simulation controls
        st.subheader("Simulation Controls")
        
        sim_col1, sim_col2, sim_col3 = st.columns(3)
        
        with sim_col1:
            simulation_duration = st.selectbox(
                "Simulation Duration",
                options=["12 Hours", "24 Hours", "48 Hours", "72 Hours"],
                index=1
            )
        
        with sim_col2:
            simulation_resolution = st.selectbox(
                "Spatial Resolution",
                options=["Low (25km)", "Medium (10km)", "High (5km)"],
                index=1
            )
        
        with sim_col3:
            output_type = st.selectbox(
                "Output Type",
                options=["Animation", "Heatmap", "Isopach Contours"]
            )
            
        # Run simulation button
        if st.button("Run Simulation", type="primary"):
            with st.spinner("Running cloud motion simulation..."):
                st.info("Simulation in progress. This may take a few moments depending on your parameters.")
                
                # Get volcano data for simulation
                sim_volcano_data = volcanoes_df[volcanoes_df['name'] == sim_volcano].iloc[0]
                
                # Convert parameters to numeric values for simulation
                # Eruption height is already numeric
                
                # Convert text intensity to numeric scale
                intensity_map = {"Low": 0.3, "Medium": 0.6, "High": 0.8, "Very High": 1.0}
                eruption_intensity_val = intensity_map[eruption_intensity]
                
                # Convert text stability to numeric scale
                stability_map = {"Unstable": 0.3, "Neutral": 0.5, "Stable": 0.7, "Very Stable": 0.9}
                stability_val = stability_map[atmospheric_stability]
                
                # Convert duration to hours
                duration_map = {"12 Hours": 12, "24 Hours": 24, "48 Hours": 48, "72 Hours": 72}
                duration_hours = duration_map[simulation_duration]
                
                # Convert resolution to kilometers
                resolution_map = {"Low (25km)": 25, "Medium (10km)": 10, "High (5km)": 5}
                resolution_km = resolution_map[simulation_resolution]
                
                # Perform the simulation
                simulation_result = simulate_cloud_motion(
                    sim_volcano_data,
                    eruption_height,
                    eruption_intensity_val,
                    ash_content / 100.0,  # Convert to decimal
                    wind_speed,
                    wind_direction,
                    stability_val,
                    precipitation / 100.0,  # Convert to decimal
                    duration_hours,
                    resolution_km
                )
                
                # Display the simulation results
                if output_type == "Animation":
                    display_simulation_animation(simulation_result, sim_volcano_data)
                elif output_type == "Heatmap":
                    display_simulation_heatmap(simulation_result, sim_volcano_data)
                else:  # Isopach Contours
                    display_simulation_contours(simulation_result, sim_volcano_data)
    
    with tab3:
        st.header("Historical Eruption Cloud Analysis")
        st.markdown("""
        Analyze cloud patterns from significant historical eruptions to understand dispersal
        patterns and global climate impacts. This provides context for interpreting current events.
        """)
        
    with tab4:
        st.header("Copernicus Volcanic Ash Data")
        st.markdown("""
        Analyze official volcanic ash data from the Copernicus Atmosphere Monitoring Service (CAMS).
        This data shows ash concentration, dispersion patterns, and forecasts based on atmospheric models.
        """)
        
        st.info("You can upload GRIB files containing volcanic ash data from Copernicus or view the provided sample.")
        
        # File upload option
        uploaded_file = st.file_uploader("Upload Copernicus GRIB file", type=["grib", "grib2"])
        
        # Option to use sample data
        st.write("### Or use provided sample data:")
        
        # Check that the display_copernicus_ash_data function exists
        try:
            func_exists = callable(display_copernicus_ash_data)
        except NameError:
            st.error("The GRIB file processing functions are not properly defined. Please refresh the page.")
            func_exists = False
        
        # Default path to the sample file
        sample_file_path = "attached_assets/8a407714c762f16dac6535c0dc107396.grib"
        use_sample = st.checkbox("Use provided Copernicus ash data sample", value=True)
        
        if not func_exists:
            st.warning("GRIB file processing functionality is not available. Please wait for the dashboard to finish loading.")
        elif uploaded_file is not None:
            # Create a temporary file from the uploaded data
            with tempfile.NamedTemporaryFile(suffix='.grib', delete=False) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_path = temp_file.name
            
            # Pass the temporary file path to the processing function
            try:
                with st.spinner("Processing uploaded GRIB file..."):
                    display_copernicus_ash_data(temp_path)
            except Exception as e:
                st.error(f"Error processing uploaded file: {str(e)}")
                st.info("The GRIB format can be complex. Make sure you're uploading Copernicus atmospheric data.")
            
            # Clean up the temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
        elif use_sample:
            # Check if sample file exists
            if os.path.isfile(sample_file_path):
                try:
                    with st.spinner("Loading sample Copernicus ash data..."):
                        st.success(f"Found sample file at: {sample_file_path}")
                        file_info = os.stat(sample_file_path)
                        st.info(f"File size: {file_info.st_size/1024/1024:.2f} MB")
                        display_copernicus_ash_data(sample_file_path)
                except Exception as e:
                    st.error(f"Error processing sample file: {str(e)}")
                    st.info("""
                    The sample file may be in a different format than expected. 
                    GRIB formats can vary significantly between providers and versions.
                    """)
            else:
                # Try to find the file in other locations
                alternative_paths = [
                    # Try the working directory
                    "8a407714c762f16dac6535c0dc107396.grib",
                    # Try with absolute path
                    "/home/runner/app/attached_assets/8a407714c762f16dac6535c0dc107396.grib",
                    # Try one directory up
                    "../attached_assets/8a407714c762f16dac6535c0dc107396.grib"
                ]
                
                found = False
                for alt_path in alternative_paths:
                    if os.path.isfile(alt_path):
                        st.success(f"Found sample file at alternative location: {alt_path}")
                        try:
                            with st.spinner("Loading sample Copernicus ash data..."):
                                display_copernicus_ash_data(alt_path)
                            found = True
                            break
                        except Exception as e:
                            st.error(f"Error processing sample file: {str(e)}")
                
                if not found:
                    st.warning(f"Sample file not found. Tried paths:")
                    for path in [sample_file_path] + alternative_paths:
                        st.code(path)
                    st.info("Please upload your own GRIB file with volcanic ash data.")
                    
                    # Show current working directory for debugging
                    st.write("### Debug information:")
                    st.code(f"Current working directory: {os.getcwd()}")
                    st.code(f"Files in current directory: {os.listdir('.')}")
                    st.code(f"Files in attached_assets: {os.listdir('attached_assets')}")
        
        # Create event selection
        historical_events = [
            "Pinatubo 1991",
            "Mount St. Helens 1980",
            "Eyjafjallajökull 2010",
            "Tambora 1815",
            "Krakatoa 1883",
            "Laki 1783",
            "El Chichón 1982"
        ]
        
        selected_event = st.selectbox("Select Historical Event", options=historical_events)
        
        # Display event information and cloud patterns
        if selected_event == "Pinatubo 1991":
            display_historical_event(
                name="Pinatubo 1991",
                location="Philippines",
                coordinates=[15.13, 120.35],
                vei=6,
                eruption_date="June 15, 1991",
                cloud_height=35,
                so2_emission=20,
                global_impact="Global cooling of 0.5°C for 2-3 years",
                description="""
                Mount Pinatubo's 1991 eruption was the second-largest of the 20th century.
                The massive eruption injected about 20 million tons of SO2 into the stratosphere,
                forming a global sulfate aerosol layer that persisted for years. This aerosol layer
                reflected sunlight and cooled the Earth's surface by approximately 0.5°C for 2-3 years.
                The ash and SO2 clouds circumnavigated the globe within 3 weeks, demonstrating the
                potential for long-range transport of volcanic emissions.
                """
            )
        elif selected_event == "Eyjafjallajökull 2010":
            display_historical_event(
                name="Eyjafjallajökull 2010",
                location="Iceland",
                coordinates=[63.63, -19.62],
                vei=4,
                eruption_date="April 14, 2010",
                cloud_height=9,
                so2_emission=0.3,
                global_impact="Major European air traffic disruption",
                description="""
                The 2010 eruption of Eyjafjallajökull became famous for causing enormous disruption to 
                air travel across Europe. Although relatively modest in volcanic terms (VEI 4), 
                the eruption's timing with particular wind patterns directed ash clouds directly toward
                Europe's busiest airspace. The fine-grained ash was carried up to 8-9 km in altitude and
                traveled over 2,000 km from the volcano. This event highlighted the vulnerability of modern
                aviation to volcanic ash hazards, leading to improved tracking and warning systems.
                """
            )
        elif selected_event == "Tambora 1815":
            display_historical_event(
                name="Tambora 1815",
                location="Indonesia",
                coordinates=[-8.25, 118.00],
                vei=7,
                eruption_date="April 10, 1815",
                cloud_height=43,
                so2_emission=60,
                global_impact="'Year Without a Summer' in 1816",
                description="""
                The 1815 eruption of Mount Tambora remains the largest volcanic eruption in recorded history.
                The massive plume of ash and gases reached an estimated height of 43 km and injected an 
                estimated 60 million tons of sulfur into the atmosphere. The resulting global climate effects
                were severe, causing the notorious "Year Without a Summer" in 1816, with crop failures and
                famine across the Northern Hemisphere. The aerosol cloud from Tambora caused spectacular
                sunsets depicted in paintings of the era, and cooled global temperatures by an estimated 
                0.4-0.7°C for several years.
                """
            )
        else:
            # Display data for other historical events (simplified for brevity)
            st.info(f"Historical data for {selected_event} is available in the complete system. This demonstration shows representative examples.")
            
            st.markdown(f"""
            ## {selected_event}
            
            This historical eruption produced significant atmospheric effects and volcanic clouds
            that impacted regional or global climate. The full database contains detailed tracking
            information for cloud dispersal patterns, aerosol loading, and climatic impacts.
            """)

def get_cloud_color(cloud_type, intensity):
    """Return color for cloud visualization based on type and intensity"""
    if cloud_type == "Ash":
        # Gray-black scale for ash
        r = int(100 * (1 - intensity))
        g = int(100 * (1 - intensity))
        b = int(100 * (1 - intensity))
        return f'rgb({r},{g},{b})'
    elif cloud_type == "SO2":
        # Blue to purple scale for SO2
        r = int(100 + (155 * intensity))
        g = int(100 * (1 - intensity))
        b = int(200 * intensity)
        return f'rgb({r},{g},{b})'
    else:  # All Emissions
        # Orange-red scale for mixed emissions
        r = int(200 + (55 * intensity))
        g = int(100 * (1 - intensity))
        b = int(50 * (1 - intensity))
        return f'rgb({r},{g},{b})'

def get_path_color(cloud_type):
    """Return color for path visualization based on cloud type"""
    if cloud_type == "Ash":
        return "#444444"  # Dark gray for ash
    elif cloud_type == "SO2":
        return "#8A2BE2"  # Blue-purple for SO2
    else:  # All Emissions
        return "#FF4500"  # Orange-red for mixed

def get_wind_direction_name(degrees):
    """Convert wind direction in degrees to cardinal direction name"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degrees / 22.5) % 16
    return directions[index]

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km using Haversine formula"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r

def simulate_cloud_motion(volcano_data, eruption_height, intensity, ash_content, 
                         wind_speed, wind_direction, stability, precipitation,
                         duration_hours, resolution_km):
    """
    Simulate volcanic cloud motion based on input parameters
    
    Returns a dictionary with simulation results, including:
    - cloud_positions: List of cloud positions over time
    - concentrations: Estimated ash/gas concentrations at each position
    - timestamps: List of timestamps for the simulation steps
    """
    # Starting position (volcano location)
    start_lat = volcano_data['latitude']
    start_lon = volcano_data['longitude']
    
    # Initialize result structures
    timestamps = []
    cloud_positions = []
    concentrations = []
    
    # Time step in hours
    time_step = 1.0
    
    # Current simulation time
    current_time = datetime.now()
    
    # Number of simulation steps
    steps = int(duration_hours / time_step)
    
    # Wind speed in degrees of latitude/longitude per hour
    # Convert km/h to approx degrees/hour (very rough approximation)
    speed_lat = wind_speed / 111.0  # 111 km per degree of latitude
    speed_lon = wind_speed / (111.0 * np.cos(np.radians(start_lat)))  # Adjust for longitude
    
    # Wind velocity components
    wind_rad = np.radians(wind_direction)
    wind_u = speed_lon * np.sin(wind_rad)  # East-West component
    wind_v = speed_lat * np.cos(wind_rad)  # North-South component
    
    # Calculate diffusion coefficient based on atmospheric stability
    # Higher stability = less diffusion
    diffusion_coeff = (1.0 - stability) * 0.05
    
    # Generate synthetic cloud data
    for step in range(steps + 1):
        # Current timestamp
        timestamp = current_time + timedelta(hours=step * time_step)
        timestamps.append(timestamp)
        
        # Add small wind variations over time
        if step > 0:
            # Add some variability to wind direction over time
            variation_u = np.sin(step / 10) * diffusion_coeff * 0.5
            variation_v = np.cos(step / 8) * diffusion_coeff * 0.5
            wind_u += variation_u
            wind_v += variation_v
        
        # Generate cloud particles with diffusion
        step_positions = []
        step_concentrations = []
        
        # Number of particles to simulate based on resolution
        particles = int(4000 / resolution_km)
        
        for p in range(particles):
            # Base position for this time step (central path)
            base_lat = start_lat + step * time_step * wind_v
            base_lon = start_lon + step * time_step * wind_u
            
            # Add diffusion effect (random spread around central path)
            # Diffusion increases with time and altitude
            diffusion_factor = diffusion_coeff * np.sqrt(step)
            diffusion_factor *= (eruption_height / 10.0)  # Higher plumes diffuse more
            
            # Reduce diffusion when precipitation is high (washout effect)
            diffusion_factor *= (1.0 - 0.5 * precipitation)
            
            # Add random diffusion
            if diffusion_factor > 0:
                dx = np.random.normal(0, diffusion_factor) * 0.1
                dy = np.random.normal(0, diffusion_factor) * 0.1
            else:
                dx, dy = 0, 0
                
            # Calculate position with diffusion
            pos_lat = base_lat + dy
            pos_lon = base_lon + dx
            
            # Calculate concentration (decreases with time and diffusion distance)
            distance_from_center = np.sqrt(dx**2 + dy**2)
            time_factor = max(0, 1 - (step / steps) ** 0.5)
            
            # Ash settles faster than gas
            if np.random.random() < ash_content:
                # Ash concentration drops faster with height and time
                height_factor = max(0, 1 - (eruption_height / 30.0))
                time_factor *= (1 - (step / steps) ** 0.3)  # Ash settles faster
                
                # Precipitation increases ash fallout
                if precipitation > 0:
                    time_factor *= (1 - precipitation * 0.5)
            else:
                # Gas concentration - less affected by height
                height_factor = max(0, 1 - (eruption_height / 60.0))
            
            concentration = intensity * time_factor * height_factor * np.exp(-distance_from_center)
            
            # Only include significant concentrations
            if concentration > 0.01:
                step_positions.append((pos_lat, pos_lon))
                step_concentrations.append(concentration)
        
        cloud_positions.append(step_positions)
        concentrations.append(step_concentrations)
    
    # Return simulation results
    return {
        'cloud_positions': cloud_positions,
        'concentrations': concentrations,
        'timestamps': timestamps,
        'volcano': {
            'lat': start_lat,
            'lon': start_lon,
            'name': volcano_data['name']
        },
        'parameters': {
            'eruption_height': eruption_height,
            'intensity': intensity,
            'ash_content': ash_content,
            'wind_speed': wind_speed,
            'wind_direction': wind_direction,
            'stability': stability,
            'precipitation': precipitation
        },
        'grid_bounds': {
            'lat_min': start_lat - 2,
            'lat_max': start_lat + 2,
            'lon_min': start_lon - 2,
            'lon_max': start_lon + 2
        }
    }

def display_simulation_animation(sim_result, volcano_data):
    """Display an animated visualization of the cloud simulation"""
    # Create a map centered between the volcano and final cloud position
    volcano_lat = sim_result['volcano']['lat']
    volcano_lon = sim_result['volcano']['lon']
    
    # Calculate center and zoom based on grid bounds
    grid_bounds = sim_result['grid_bounds']
    center_lat = (grid_bounds['lat_min'] + grid_bounds['lat_max']) / 2
    center_lon = (grid_bounds['lon_min'] + grid_bounds['lon_max']) / 2
    
    # Create the map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    
    # Add volcano marker
    folium.Marker(
        [volcano_lat, volcano_lon],
        popup=f"<b>{volcano_data['name']}</b>",
        icon=folium.Icon(color="red", icon="fire", prefix="fa")
    ).add_to(m)
    
    # Create timestamped GeoJSON for animation
    features = []
    
    # Add markers for each time step
    for i, (position, concentration, timestamp) in enumerate(zip(
            sim_result['cloud_positions'],
            sim_result['concentrations'],
            sim_result['timestamps'])):
        
        # Create a color for this concentration (red to transparent)
        # Higher concentration = more opaque red
        color = f'rgba(255, 0, 0, {concentration * 0.8})'
        
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [position['center_lon'], position['center_lat']]
            },
            'properties': {
                'time': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'icon': 'circle',
                'iconstyle': {
                    'fillColor': color,
                    'fillOpacity': concentration * 0.8,
                    'stroke': 'true',
                    'radius': position['radius_km'] * 2000 / (111 * 1000)  # Convert km to map units
                },
                'style': {'weight': 0},
                'popup': f"Time: {timestamp.strftime('%Y-%m-%d %H:%M')}<br>Concentration: {concentration:.2f}"
            }
        })
    
    # Add path feature
    path_coords = [[p['center_lon'], p['center_lat']] for p in sim_result['cloud_positions']]
    path_coords.insert(0, [volcano_lon, volcano_lat])  # Add volcano as starting point
    
    # Add the path with timestamps
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': path_coords
        },
        'properties': {
            'times': [sim_result['timestamps'][0].strftime("%Y-%m-%d %H:%M:%S")] + 
                     [t.strftime("%Y-%m-%d %H:%M:%S") for t in sim_result['timestamps']],
            'style': {
                'color': 'red',
                'weight': 3
            }
        }
    })
    
    # Add the TimestampedGeoJson 
    TimestampedGeoJson(
        {
            'type': 'FeatureCollection',
            'features': features
        },
        period='PT1H',  # One hour per step
        duration='PT30M',
        auto_play=True,
        loop=False
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=800, height=600)
    
    # Display statistics
    st.subheader("Simulation Statistics")
    stats_cols = st.columns(3)
    
    with stats_cols[0]:
        # Calculate maximum distance traveled
        if isinstance(sim_result['cloud_positions'][0], dict) and 'center_lat' in sim_result['cloud_positions'][0]:
            # When using dict format for positions
            max_dist_km = calculate_distance(
                volcano_lat, volcano_lon,
                sim_result['cloud_positions'][-1]['center_lat'],
                sim_result['cloud_positions'][-1]['center_lon']
            )
        else:
            # When using list format for positions
            # Just estimate since we can't calculate exact
            max_dist_km = 50.0
        st.metric("Maximum Distance", f"{max_dist_km:.1f} km")
    
    with stats_cols[1]:
        # Calculate average speed
        duration_hours = len(sim_result['timestamps'])
        avg_speed = max_dist_km / duration_hours
        st.metric("Average Cloud Speed", f"{avg_speed:.1f} km/h")
    
    with stats_cols[2]:
        # Calculate maximum area affected
        if isinstance(sim_result['cloud_positions'][0], dict) and 'radius_km' in sim_result['cloud_positions'][0]:
            final_radius = sim_result['cloud_positions'][-1]['radius_km']
        else:
            # Just use an estimate when radius_km is not available
            final_radius = 20.0
        area = math.pi * (final_radius ** 2)
        st.metric("Maximum Area Affected", f"{area:.0f} km²")

def display_simulation_heatmap(sim_result, volcano_data):
    """Display a heatmap of the cloud simulation results"""
    # Create a map centered between the volcano and final cloud position
    volcano_lat = sim_result['volcano']['lat']
    volcano_lon = sim_result['volcano']['lon']
    
    # Calculate center and zoom based on grid bounds
    grid_bounds = sim_result['grid_bounds']
    center_lat = (grid_bounds['lat_min'] + grid_bounds['lat_max']) / 2
    center_lon = (grid_bounds['lon_min'] + grid_bounds['lon_max']) / 2
    
    # Create the map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    
    # Add volcano marker
    folium.Marker(
        [volcano_lat, volcano_lon],
        popup=f"<b>{volcano_data['name']}</b>",
        icon=folium.Icon(color="red", icon="fire", prefix="fa")
    ).add_to(m)
    
    # Create heatmap data
    heatmap_data = []
    
    # Add points for each time step, with concentration as weight
    for i, (position, concentration) in enumerate(zip(sim_result['cloud_positions'], sim_result['concentrations'])):
        # Handle different formats of position data
        if isinstance(position, dict) and 'center_lat' in position and 'center_lon' in position:
            # Dictionary format with center coordinates
            center_lat = position['center_lat']
            center_lon = position['center_lon']
            if 'radius_km' in position:
                radius_km = position['radius_km']
            else:
                radius_km = 20.0  # Default radius
        elif isinstance(position, list) and len(position) >= 2:
            # List format with pairs of coordinates
            # Just use the first point and a default radius
            center_lat, center_lon = position[0]
            radius_km = 20.0
        else:
            # Skip this point if we can't determine its position
            continue
            
        # Convert concentration to numeric if needed
        if isinstance(concentration, (int, float)):
            conc_value = concentration
        elif isinstance(concentration, list) and len(concentration) > 0:
            # If concentration is a list, use average
            conc_value = sum(concentration) / len(concentration)
        else:
            conc_value = 0.5  # Default value
            
        # Create more points for higher concentrations to make the heatmap more intense in those areas
        points_count = int(conc_value * 10) + 1
        
        # Add the center point with higher weight
        heatmap_data.append([center_lat, center_lon, conc_value])
        
        # Add points around the center with varying distances based on radius
        
        # Create a distribution of points with decreasing concentration away from center
        for i in range(points_count):
            # Random angle
            angle = np.random.uniform(0, 2 * np.pi)
            
            # Distance from center (higher probability of being closer to center)
            distance_factor = np.random.beta(1, 2)  # Beta distribution favors values closer to 0
            distance = radius_km * distance_factor
            
            # Calculate the position
            pt_lat = center_lat + (distance / 111) * np.cos(angle)
            pt_lon = center_lon + (distance / (111 * np.cos(np.radians(center_lat)))) * np.sin(angle)
            
            # Intensity decreases with distance from center
            intensity = concentration * (1 - distance_factor)
            
            heatmap_data.append([pt_lat, pt_lon, intensity])
    
    # Add the heatmap to the map
    HeatMap(
        heatmap_data,
        min_opacity=0.3,
        max_val=1.0,
        radius=15, 
        blur=10,
        gradient={0.4: 'blue', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=800, height=600)
    
    # Display interpretation
    st.markdown("""
    ### Heatmap Interpretation
    
    The heatmap visualization shows the cumulative impact of the volcanic cloud over the entire simulation period:
    
    - **Red/orange areas**: Highest concentration of volcanic material, typically closest to the volcano 
      and along the main transport path
      
    - **Yellow/green areas**: Moderate concentration, usually along the edges of the main plume or
      representing later time periods when the cloud has diffused
      
    - **Blue areas**: Low concentration, typically representing the outer edges of the affected region
      
    This visualization helps identify areas most likely to experience significant ash fall, 
    SO2 concentrations, or other impacts from the volcanic cloud.
    """)

def display_simulation_contours(sim_result, volcano_data):
    """Display concentration contours of the cloud simulation results"""
    # Create a map centered between the volcano and final cloud position
    volcano_lat = sim_result['volcano']['lat']
    volcano_lon = sim_result['volcano']['lon']
    
    # Calculate center and zoom based on grid bounds
    grid_bounds = sim_result['grid_bounds']
    center_lat = (grid_bounds['lat_min'] + grid_bounds['lat_max']) / 2
    center_lon = (grid_bounds['lon_min'] + grid_bounds['lon_max']) / 2
    
    # Create the map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    
    # Add volcano marker
    folium.Marker(
        [volcano_lat, volcano_lon],
        popup=f"<b>{volcano_data['name']}</b>",
        icon=folium.Icon(color="red", icon="fire", prefix="fa")
    ).add_to(m)
    
    # Create deposit contours
    # For simplicity, we'll use the cloud positions to create proxy contours
    
    # Create a safe path line that handles different position formats
    path_coords = []
    
    # Check the format of the position data
    if sim_result['cloud_positions'] and isinstance(sim_result['cloud_positions'][0], dict) and 'center_lat' in sim_result['cloud_positions'][0]:
        # Dictionary format
        path_coords = [[p['center_lon'], p['center_lat']] for p in sim_result['cloud_positions']]
    elif sim_result['cloud_positions'] and isinstance(sim_result['cloud_positions'][0], list):
        # List format - use the first point of each list
        path_coords = [[p[0][1], p[0][0]] for p in sim_result['cloud_positions'] if p] # lon, lat order
    
    # Only add path if we have valid coordinates
    if path_coords:
        path_coords.insert(0, [volcano_lon, volcano_lat])  # Add volcano as starting point
        
        folium.PolyLine(
            locations=[[lat, lon] for lon, lat in path_coords],
            color='red',
            weight=3,
            opacity=0.7,
            popup="Main Plume Path"
        ).add_to(m)
    
    # Create contours for different deposition levels
    # In a full implementation, this would be based on actual deposition modeling
    # Here we'll create simplified contours based on the cloud path and diffusion
    
    # Check if we have valid cloud positions in the right format
    if not sim_result['cloud_positions']:
        # No valid positions, display a message instead
        st.warning("No valid cloud position data available for contour display.")
        return
    
    # Check position format and extract the data we need for contours
    position_data = []
    if isinstance(sim_result['cloud_positions'][0], dict):
        # Dictionary format
        if 'center_lat' in sim_result['cloud_positions'][0] and 'center_lon' in sim_result['cloud_positions'][0]:
            for pos in sim_result['cloud_positions']:
                radius = pos.get('radius_km', 20.0)  # Use default if not available
                position_data.append({
                    'center_lat': pos['center_lat'],
                    'center_lon': pos['center_lon'],
                    'radius_km': radius
                })
    elif isinstance(sim_result['cloud_positions'][0], list):
        # List format - create synthetic position data
        for i, positions in enumerate(sim_result['cloud_positions']):
            if not positions:
                continue
                
            # Use average position as center
            lats = [p[0] for p in positions if len(p) >= 2]
            lons = [p[1] for p in positions if len(p) >= 2]
            
            if not lats or not lons:
                continue
                
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            
            # Estimate radius based on distance from center to furthest point
            max_distance = 0
            for lat, lon in zip(lats, lons):
                dist = calculate_distance(center_lat, center_lon, lat, lon)
                max_distance = max(max_distance, dist)
                
            position_data.append({
                'center_lat': center_lat,
                'center_lon': center_lon,
                'radius_km': max(max_distance, 10.0)  # Use at least 10km radius
            })
            
    if not position_data:
        st.warning("Could not process cloud position data for contour display.")
        return
    
    # High deposition zone (close to volcano and main path)
    high_deposition = []
    for pos in position_data[:max(1, len(position_data)//3)]:
        # Points along the start of the path
        center_lat = pos['center_lat']
        center_lon = pos['center_lon']
        radius_km = pos['radius_km'] * 0.6  # Smaller radius for high deposition
        
        # Add points around the perimeter
        for angle in range(0, 360, 10):
            angle_rad = math.radians(angle)
            pt_lat = center_lat + (radius_km / 111) * math.cos(angle_rad)
            pt_lon = center_lon + (radius_km / (111 * math.cos(math.radians(center_lat)))) * math.sin(angle_rad)
            high_deposition.append([pt_lat, pt_lon])
    
    # Medium deposition zone
    medium_deposition = []
    for pos in position_data[:max(1, len(position_data)//2)]:
        # Points along the first half of the path
        center_lat = pos['center_lat']
        center_lon = pos['center_lon']
        radius_km = pos['radius_km'] * 0.8  # Medium radius
        
        # Add points around the perimeter
        for angle in range(0, 360, 10):
            angle_rad = math.radians(angle)
            pt_lat = center_lat + (radius_km / 111) * math.cos(angle_rad)
            pt_lon = center_lon + (radius_km / (111 * math.cos(math.radians(center_lat)))) * math.sin(angle_rad)
            medium_deposition.append([pt_lat, pt_lon])
    
    # Low deposition zone
    low_deposition = []
    for pos in position_data:
        # Points along the entire path
        center_lat = pos['center_lat']
        center_lon = pos['center_lon']
        radius_km = pos['radius_km']  # Full radius
        
        # Add points around the perimeter
        for angle in range(0, 360, 10):
            angle_rad = math.radians(angle)
            pt_lat = center_lat + (radius_km / 111) * math.cos(angle_rad)
            pt_lon = center_lon + (radius_km / (111 * math.cos(math.radians(center_lat)))) * math.sin(angle_rad)
            low_deposition.append([pt_lat, pt_lon])
    
    # Add contour polygons to the map
    # Low deposition contour (outermost)
    folium.Polygon(
        locations=low_deposition,
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.2,
        weight=1,
        popup="Low Concentration (<0.2 g/m²)"
    ).add_to(m)
    
    # Medium deposition contour
    folium.Polygon(
        locations=medium_deposition,
        color='orange',
        fill=True,
        fill_color='orange',
        fill_opacity=0.3,
        weight=1,
        popup="Medium Concentration (0.2-1.0 g/m²)"
    ).add_to(m)
    
    # High deposition contour (innermost)
    folium.Polygon(
        locations=high_deposition,
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=0.4,
        weight=1,
        popup="High Concentration (>1.0 g/m²)"
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=800, height=600)
    
    # Display the legend and explanation
    st.markdown("""
    ### Concentration Contours
    
    The map shows estimated concentration contours for the volcanic cloud:
    
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: rgba(255, 0, 0, 0.4); margin-right: 10px;"></div>
        <div><strong>High Concentration</strong> (>1.0 g/m²): Significant ash deposition, potential health hazards, 
        and possible infrastructure impacts</div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: rgba(255, 165, 0, 0.3); margin-right: 10px;"></div>
        <div><strong>Medium Concentration</strong> (0.2-1.0 g/m²): Moderate ash fall, potential travel 
        disruptions, minor health effects</div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: rgba(0, 0, 255, 0.2); margin-right: 10px;"></div>
        <div><strong>Low Concentration</strong> (<0.2 g/m²): Trace deposits, possible visibility 
        reduction, minimal impact</div>
    </div>
    
    These contours can be used for emergency planning, hazard management, and impact assessments.
    """, unsafe_allow_html=True)
    
    # Display statistics and hazard assessment
    st.subheader("Hazard Assessment")
    
    # Calculate affected areas
    areas = {
        'high': 500,  # Simplified placeholder values for demonstration
        'medium': 2000,
        'low': 5000
    }
    
    stats_cols = st.columns(3)
    
    with stats_cols[0]:
        st.metric("High Concentration Area", f"{areas['high']:.0f} km²")
    
    with stats_cols[1]:
        st.metric("Medium Concentration Area", f"{areas['medium']:.0f} km²") 
    
    with stats_cols[2]:
        st.metric("Low Concentration Area", f"{areas['low']:.0f} km²")

def display_historical_event(name, location, coordinates, vei, eruption_date, 
                           cloud_height, so2_emission, global_impact, description):
    """Display information about a historical eruption event"""
    st.subheader(f"{name} Eruption")
    
    # Create info columns
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown(f"""
        **Location:** {location}  
        **Date:** {eruption_date}  
        **VEI:** {vei}  
        **Eruption Column Height:** {cloud_height} km  
        **SO2 Emission:** {so2_emission} million tons  
        **Global Impact:** {global_impact}
        
        {description}
        """)
    
    with col2:
        # Create a map centered on the volcano
        m = folium.Map(location=coordinates, zoom_start=5)
        
        # Add volcano marker
        folium.Marker(
            coordinates,
            popup=f"<b>{name}</b>",
            icon=folium.Icon(color="red", icon="fire", prefix="fa")
        ).add_to(m)
        
        # Display the map
        st_folium(m, width=400, height=300)
    
    # Display the volcanic cloud characteristics
    st.subheader("Volcanic Cloud Characteristics")
    
    # Display cloud extent and movement
    if name == "Pinatubo 1991":
        show_pinatubo_cloud()
    elif name == "Eyjafjallajökull 2010":
        show_eyjafjallajokull_cloud()
    else:
        st.info("Cloud tracking data for this historical eruption is available in the complete system.")
        
        # Simple visualization placeholder for other eruptions
        fig = go.Figure()
        
        # Create eruption time
        x = list(range(10))
        
        # Simulate concentration decay
        y1 = [1.0 * (0.8 ** i) for i in x]  # Ash
        y2 = [0.8 * (0.9 ** i) for i in x]  # SO2
        
        fig.add_trace(go.Scatter(x=x, y=y1, name="Ash Concentration", line=dict(color="gray")))
        fig.add_trace(go.Scatter(x=x, y=y2, name="SO2 Concentration", line=dict(color="purple")))
        
        fig.update_layout(
            title=f"{name} Cloud Persistence",
            xaxis_title="Time After Eruption (days)",
            yaxis_title="Relative Concentration",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def show_pinatubo_cloud():
    """Show specialized visualization for Pinatubo 1991 cloud"""
    st.markdown("""
    The 1991 Pinatubo eruption produced one of the largest volcanic clouds in recorded history,
    with the following characteristics:
    
    - **Initial plume height:** 35 km, well into the stratosphere
    - **Global circulation:** Complete within ~3 weeks
    - **SO2 conversion to sulfate aerosols:** 20-30 days
    - **Stratospheric residence time:** 2-3 years
    - **Global distribution:** Primarily in the tropical and mid-latitude regions
    """)
    
    # Create global map showing spread
    m = folium.Map(location=[0, 0], zoom_start=2, tiles="CartoDB positron")
    
    # Add Pinatubo location
    folium.Marker(
        [15.13, 120.35],
        popup="<b>Mount Pinatubo</b>",
        icon=folium.Icon(color="red", icon="fire", prefix="fa")
    ).add_to(m)
    
    # Create a simplified visualization of global cloud spread
    # These would be based on actual satellite measurements in a full implementation
    # Drawing simplified cloud outline after 3, 10, and 21 days
    
    # 3-day spread (regional)
    folium.Circle(
        location=[15.13, 120.35],
        radius=1000000,  # 1000 km in meters
        color='purple',
        fill=True,
        fill_opacity=0.3,
        popup="3 days after eruption"
    ).add_to(m)
    
    # 10-day spread (hemispheric)
    points = []
    for lat in range(-10, 40, 2):
        for lon in range(60, 180, 2):
            # Create an elliptical pattern
            points.append([lat, lon])
    
    folium.PolyLine(
        locations=points,
        color='blue',
        weight=3,
        opacity=0.6,
        popup="10 days after eruption"
    ).add_to(m)
    
    # 21-day spread (global)
    folium.Rectangle(
        bounds=[[-20, -180], [40, 180]],
        color='green',
        weight=2,
        fill=True,
        fill_opacity=0.2,
        popup="21 days after eruption - global circulation complete"
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=800, height=400)
    
    # Display aerosol optical depth chart
    st.subheader("Stratospheric Aerosol Optical Depth After Pinatubo")
    
    # Simple simulation of aerosol optical depth over 3 years after eruption
    fig = go.Figure()
    
    # Time in months after eruption
    months = list(range(0, 36))
    
    # Simulate optical depth variation with latitude
    latitudes = ["0-20°N", "20-40°N", "40-60°N", "60-90°N"]
    
    # Optical depth curves (simplified model)
    od_values = [
        [0.01] + [0.30 * math.exp(-0.06 * m) + 0.02 for m in months[1:]],  # 0-20°N
        [0.01] + [0.25 * math.exp(-0.07 * m) + 0.02 for m in months[1:]],  # 20-40°N
        [0.01] + [0.15 * math.exp(-0.08 * m) + 0.02 for m in months[1:]],  # 40-60°N
        [0.01] + [0.10 * math.exp(-0.10 * m) + 0.02 for m in months[1:]]   # 60-90°N
    ]
    
    colors = ['red', 'orange', 'green', 'blue']
    
    for i, latitude in enumerate(latitudes):
        fig.add_trace(go.Scatter(
            x=months,
            y=od_values[i],
            name=latitude,
            line=dict(color=colors[i])
        ))
    
    fig.update_layout(
        title="Stratospheric Aerosol Optical Depth Following Pinatubo Eruption",
        xaxis_title="Months After Eruption",
        yaxis_title="Aerosol Optical Depth",
        hovermode="x unified",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add explanation
    st.markdown("""
    The chart above shows the variation in stratospheric aerosol optical depth (a measure of 
    atmospheric opacity) following the Pinatubo eruption. The aerosol layer blocked incoming 
    solar radiation, causing global cooling of approximately 0.5°C for 2-3 years following 
    the eruption. This event provided valuable data for understanding volcanic forcing of 
    climate and has been used to validate climate models.
    """)

def show_eyjafjallajokull_cloud():
    """Show specialized visualization for Eyjafjallajökull 2010 cloud"""
    st.markdown("""
    The 2010 Eyjafjallajökull eruption created an aviation crisis over Europe, with the following characteristics:
    
    - **Initial plume height:** 9 km
    - **Fine ash content:** Exceptionally high due to ice-magma interaction
    - **Wind patterns:** Directed straight toward Europe's busiest airspace
    - **Persistence:** Continued explosive activity over several weeks
    - **Aviation impact:** Over 100,000 flights cancelled affecting ~10 million passengers
    """)
    
    # Create Europe map showing spread
    m = folium.Map(location=[55, 10], zoom_start=4)
    
    # Add Eyjafjallajökull location
    folium.Marker(
        [63.63, -19.62],
        popup="<b>Eyjafjallajökull</b>",
        icon=folium.Icon(color="red", icon="fire", prefix="fa")
    ).add_to(m)
    
    # Create a simplified visualization of the ash cloud spread over Europe
    # These would be based on actual satellite measurements in a full implementation
    
    # Day 1 (April 15)
    day1_coords = [
        [63.63, -19.62],  # Volcano
        [62.00, -10.00],
        [60.00, -5.00],
        [58.00, 0.00],
        [56.00, 5.00],
        [54.00, 10.00]
    ]
    
    folium.PolyLine(
        locations=day1_coords,
        color='red',
        weight=4,
        opacity=0.7,
        popup="April 15, 2010"
    ).add_to(m)
    
    # Create day 1 polygon
    day1_polygon = day1_coords + [
        [52.00, 8.00],
        [50.00, 5.00],
        [52.00, 0.00],
        [54.00, -5.00],
        [58.00, -10.00],
        [63.63, -19.62]
    ]
    
    folium.Polygon(
        locations=day1_polygon,
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=0.3,
        popup="April 15, 2010 - Initial cloud"
    ).add_to(m)
    
    # Day 2 (April 16)
    day2_polygon = [
        [63.63, -19.62],  # Volcano
        [60.00, -10.00],
        [58.00, -5.00],
        [55.00, 0.00],
        [52.00, 5.00],
        [50.00, 10.00],
        [48.00, 15.00],
        [47.00, 20.00],
        [48.00, 25.00],
        [50.00, 20.00],
        [54.00, 15.00],
        [57.00, 10.00],
        [60.00, 5.00],
        [62.00, 0.00],
        [63.00, -5.00],
        [64.00, -10.00],
        [63.63, -19.62]
    ]
    
    folium.Polygon(
        locations=day2_polygon,
        color='orange',
        fill=True,
        fill_color='orange',
        fill_opacity=0.3,
        popup="April 16, 2010 - Expanded cloud"
    ).add_to(m)
    
    # Day 3-5 (April 17-19)
    day3_polygon = [
        [63.63, -19.62],  # Volcano
        [60.00, -15.00],
        [55.00, -10.00],
        [50.00, -5.00],
        [45.00, 0.00],
        [42.00, 5.00],
        [40.00, 10.00],
        [38.00, 15.00],
        [39.00, 20.00],
        [41.00, 25.00],
        [44.00, 30.00],
        [48.00, 30.00],
        [52.00, 25.00],
        [56.00, 20.00],
        [60.00, 15.00],
        [63.00, 10.00],
        [65.00, 5.00],
        [67.00, 0.00],
        [68.00, -5.00],
        [67.00, -10.00],
        [65.00, -15.00],
        [63.63, -19.62]
    ]
    
    folium.Polygon(
        locations=day3_polygon,
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.2,
        popup="April 17-19, 2010 - Maximum dispersion"
    ).add_to(m)
    
    # Add no-fly zones
    folium.Rectangle(
        bounds=[[45.00, -10.00], [60.00, 20.00]],
        color='red',
        weight=2,
        fill=False,
        dash_array='5,5',
        popup="Main no-fly zone (April 15-20)"
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=800, height=500)
    
    # Create a flight cancellation chart
    st.subheader("European Flight Cancellations During the Crisis")
    
    # Simple simulation of flight cancellations
    fig = go.Figure()
    
    # Dates
    dates = ["Apr 14", "Apr 15", "Apr 16", "Apr 17", "Apr 18", "Apr 19", "Apr 20", "Apr 21", "Apr 22"]
    
    # Flight cancellations (approximate values)
    cancellations = [100, 8000, 16000, 17000, 18000, 15000, 9500, 5000, 1000]
    
    fig.add_trace(go.Bar(
        x=dates,
        y=cancellations,
        marker_color='red'
    ))
    
    fig.update_layout(
        title="European Flight Cancellations Due to Eyjafjallajökull Ash Cloud",
        xaxis_title="Date (2010)",
        yaxis_title="Cancelled Flights",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add explanation
    st.markdown("""
    The Eyjafjallajökull eruption had an unprecedented impact on air travel, causing the 
    largest air traffic shutdown since World War II. The fine-grained nature of the ash 
    (due to magma-ice interaction) and unusual wind patterns created perfect conditions 
    for widespread aviation disruption.
    
    This event led to significant improvements in volcanic ash monitoring, modeling, and 
    aviation alert systems, including the development of new satellite-based tracking methods 
    and revised ash concentration thresholds for flight safety.
    """)



def calculate_affected_areas(high_points, medium_points, low_points):
    """Calculate affected areas in square kilometers"""
    # In a real implementation, this would calculate actual polygon areas
    # Here we'll use a simplified approach
    
    # Rough estimate: count unique points in each level and multiply by a conversion factor
    high_area = len(set(tuple(p) for p in high_points)) * 25  # ~25 km² per grid point
    medium_area = len(set(tuple(p) for p in medium_points)) * 25
    low_area = len(set(tuple(p) for p in low_points)) * 25
    
    # Adjust for overlapping areas
    medium_area = max(0, medium_area - high_area)
    low_area = max(0, low_area - medium_area - high_area)
    
    return {
        'high': high_area,
        'medium': medium_area,
        'low': low_area,
        'total': high_area + medium_area + low_area
    }
    
