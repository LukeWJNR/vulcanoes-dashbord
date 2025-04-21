def load_grib_volcanic_ash(filepath):
    """
    Load volcanic ash data from a GRIB file (Copernicus format)
    
    Args:
        filepath: Path to the GRIB file containing volcanic ash data
        
    Returns:
        xarray.Dataset containing the loaded data
    """
    try:
        st.info(f"Processing GRIB file: {filepath}")
        
        # First, try to check if the file is a valid GRIB file
        import os
        if not os.path.exists(filepath):
            st.error(f"File not found: {filepath}")
            return None
            
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # Convert to MB
        st.info(f"File size: {file_size:.2f} MB")
        
        # Open the GRIB file using cfgrib and xarray
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Try to extract just the first message (more reliable)
            try:
                ds = xr.open_dataset(filepath, engine='cfgrib', backend_kwargs={'filter_by_keys': {'edition': 2}})
            except Exception as e:
                st.warning(f"Couldn't open with filter_by_keys: {str(e)}")
                try:
                    # Try without filters
                    ds = xr.open_dataset(filepath, engine='cfgrib')
                except Exception as e2:
                    st.warning(f"Couldn't open normally: {str(e2)}")
                    # Try with more explicit options
                    import cfgrib
                    try:
                        ds = xr.open_dataset(filepath, engine='cfgrib', 
                                            backend_kwargs={'read_keys': ['stepType', 'typeOfLevel', 'units', 'name'],
                                                        'errors': 'ignore'})
                    except:
                        # Last resort - try to read with low-level API
                        st.warning("Attempting to use low-level API...")
                        messages = cfgrib.FileStream(filepath)
                        sample_msg = next(iter(messages), None)
                        st.write("GRIB file structure:")
                        if sample_msg:
                            keys = [k for k in sample_msg.keys()]
                            st.write(f"Available keys: {', '.join(keys[:20])}")
                            if 'values' in sample_msg:
                                st.write(f"Data shape: {sample_msg['values'].shape}")
                            else:
                                st.write("No values found in message")
                        else:
                            st.error("No valid messages found in GRIB file")
                        return None
                        
        # Provide some debug info
        if ds is not None:
            st.success("Successfully loaded GRIB file")
            st.write(f"Variables: {list(ds.data_vars)}")
            st.write(f"Dimensions: {list(ds.dims)}")
            
        return ds
        
    except Exception as e:
        st.error(f"Error loading GRIB file: {str(e)}")
        # Display more debug information
        import traceback
        st.code(traceback.format_exc(), language="python")
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