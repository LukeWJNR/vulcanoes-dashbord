"""
COMET (Centre for Observation and Modelling of Earthquakes, 
Volcanoes and Tectonics) utilities for the Volcano Monitoring Dashboard.

This module provides functions for accessing and processing volcano data
from the COMET Volcano Portal.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import time

def get_comet_url_for_volcano(volcano_name: str) -> str:
    """
    Get URL for a volcano in the COMET Volcano Portal.
    
    Args:
        volcano_name (str): Name of the volcano
        
    Returns:
        str: URL to the volcano page in COMET
    """
    # Format the name for URL
    formatted_name = volcano_name.lower().replace(" ", "-")
    return f"https://comet.nerc.ac.uk/volcanoes/{formatted_name}/"

def get_comet_volcano_data(volcano_name: str) -> Dict[str, Any]:
    """
    Get volcano data from COMET.
    
    Args:
        volcano_name (str): Name of the volcano
        
    Returns:
        Dict[str, Any]: Volcano data dictionary
    """
    # In production, this would fetch data from the COMET API
    # Return placeholder data for now
    return {
        'name': volcano_name,
        'source': 'COMET Portal',
        'status': 'Placeholder data - would fetch from COMET API in production'
    }

def get_matching_comet_volcano(volcano_name: str) -> Optional[str]:
    """
    Find a matching volcano name in the COMET database.
    
    Args:
        volcano_name (str): Name of the volcano to search for
        
    Returns:
        Optional[str]: Matching COMET volcano name, or None if no match
    """
    # Map of common volcano names to their COMET database equivalents
    comet_name_map = {
        'Mount Etna': 'Etna',
        'Stromboli': 'Stromboli',
        'Campi Flegrei': 'Campi Flegrei',
        'Kilauea': 'Kilauea',
        'Sierra Negra': 'Sierra Negra',
        'Soufrière Hills': 'Soufriere Hills',
        'Agung': 'Agung',
        'Eyjafjallajökull': 'Eyjafjallajokull',
        'Katla': 'Katla',
        'Mount St. Helens': 'St Helens',
        'Sakurajima': 'Sakurajima',
        'Tungurahua': 'Tungurahua',
        'Copahue': 'Copahue',
        'Tavurvur': 'Tavurvur',
        'Sinabung': 'Sinabung',
        'Popocatépetl': 'Popocatepetl',
        'Nevado del Ruiz': 'Nevado del Ruiz',
        'Reventador': 'Reventador',
        'Villarrica': 'Villarrica',
        'Cotopaxi': 'Cotopaxi',
        'Merapi': 'Merapi'
    }
    
    # Check for direct match or mapped match
    if volcano_name in comet_name_map:
        return comet_name_map[volcano_name]
        
    # Check for partial matches
    for comet_name in comet_name_map.values():
        if comet_name.lower() in volcano_name.lower() or volcano_name.lower() in comet_name.lower():
            return comet_name
            
    # Return original name if no matches found, COMET API would handle this in production
    return volcano_name

def get_comet_volcano_sar_data(volcano_name: str) -> List[Dict[str, Any]]:
    """
    Get SAR data for a volcano from COMET.
    
    Args:
        volcano_name (str): Name of the volcano
        
    Returns:
        List[Dict[str, Any]]: List of SAR data for the volcano
    """
    # In production, this would fetch data from the COMET API
    # Return scientific placeholder data with realistic dates and patterns
    comet_name = get_matching_comet_volcano(volcano_name)
    
    # Create a series of dates for the past 2 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # ~2 years
    
    # Generate dates at approximately 12-day intervals (Sentinel-1 revisit period)
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=12)
    
    # Create a list of SAR data entries
    sar_data = []
    
    # Different deformation patterns based on volcano type
    if 'etna' in comet_name.lower() or 'stromboli' in comet_name.lower():
        # Pattern for shield/stratovolcanoes with frequent activity
        cycle_length = 180  # ~6 months
        amplitude = 2.5     # cm
        for i, date in enumerate(dates):
            phase = (i % cycle_length) / cycle_length
            deformation = amplitude * np.sin(phase * 2 * np.pi)
            sar_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'displacement_cm': deformation,
                'processing_date': (date + timedelta(days=3)).strftime('%Y-%m-%d'),
                'source': 'Sentinel-1',
                'quality': 'High' if np.random.random() > 0.2 else 'Medium',
                'image_url': f"https://comet.nerc.ac.uk/volcanoes/{comet_name.lower()}/sar/{date.strftime('%Y%m%d')}.png"
            })
    elif 'katla' in comet_name.lower() or 'eyjafjallajokull' in comet_name.lower():
        # Pattern for subglacial volcanoes - gradual inflation with seasonal variation
        for i, date in enumerate(dates):
            # Gradual inflation trend with seasonal component
            yearly_phase = (date.timetuple().tm_yday / 366) * 2 * np.pi
            seasonal = 0.7 * np.sin(yearly_phase)  # Seasonal variation
            trend = 0.003 * i  # Gradual inflation
            deformation = trend + seasonal
            sar_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'displacement_cm': deformation,
                'processing_date': (date + timedelta(days=3)).strftime('%Y-%m-%d'),
                'source': 'Sentinel-1',
                'quality': 'Medium' if date.month in [11, 12, 1, 2] else 'High',  # Lower quality in winter
                'image_url': f"https://comet.nerc.ac.uk/volcanoes/{comet_name.lower()}/sar/{date.strftime('%Y%m%d')}.png"
            })
    else:
        # Generic pattern for other volcanoes - random fluctuations with occasional inflation events
        cumulative = 0
        for i, date in enumerate(dates):
            # Add occasional inflation events
            if i > 0 and np.random.random() < 0.03:  # ~3% chance of significant event
                event_size = np.random.uniform(0.5, 2.0)
                cumulative += event_size
            
            # Add small random fluctuations
            noise = np.random.normal(0, 0.15)
            deformation = cumulative + noise
            
            sar_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'displacement_cm': deformation,
                'processing_date': (date + timedelta(days=3)).strftime('%Y-%m-%d'),
                'source': 'Sentinel-1',
                'quality': 'High' if np.random.random() > 0.2 else 'Medium',
                'image_url': f"https://comet.nerc.ac.uk/volcanoes/{comet_name.lower()}/sar/{date.strftime('%Y%m%d')}.png"
            })
    
    return sar_data

def display_comet_sar_animation(volcano_name: str) -> None:
    """
    Display an animation of SAR data for a volcano.
    
    Args:
        volcano_name (str): Name of the volcano
    """
    # Get SAR data
    sar_data = get_comet_volcano_sar_data(volcano_name)
    
    if not sar_data:
        st.warning(f"No SAR data available for {volcano_name}")
        return
    
    # Convert to DataFrame for easier handling
    df = pd.DataFrame(sar_data)
    
    # Create a slider for date selection
    dates = df['date'].tolist()
    selected_index = st.slider("Select date:", 0, len(dates)-1, len(dates)-1)
    selected_date = dates[selected_index]
    
    # Display the selected data
    selected_row = df[df['date'] == selected_date].iloc[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("SAR Data Information")
        st.write(f"Date: {selected_row['date']}")
        st.write(f"Processing Date: {selected_row['processing_date']}")
        st.write(f"Source: {selected_row['source']}")
        st.write(f"Quality: {selected_row['quality']}")
        st.write(f"Displacement: {selected_row['displacement_cm']:.2f} cm")
        
        # Plot displacement time series
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['displacement_cm'],
            mode='lines+markers',
            name='Displacement',
            line=dict(color='blue', width=2),
            marker=dict(size=6, color='blue')
        ))
        
        # Add a marker for the selected date
        fig.add_trace(go.Scatter(
            x=[selected_date],
            y=[selected_row['displacement_cm']],
            mode='markers',
            marker=dict(size=12, color='red', symbol='circle'),
            name='Selected Date'
        ))
        
        fig.update_layout(
            title="Displacement Time Series",
            xaxis_title="Date",
            yaxis_title="Displacement (cm)",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("SAR Imagery")
        st.info("This is a placeholder for actual SAR imagery which would be fetched from the COMET Portal in a production environment.")
        
        # Display a placeholder for the SAR image
        # In production, this would display the actual SAR image from the COMET Portal
        fig = go.Figure()
        
        # Create a simulated interferogram pattern based on the displacement value
        # This is purely illustrative
        x = np.linspace(-5, 5, 100)
        y = np.linspace(-5, 5, 100)
        X, Y = np.meshgrid(x, y)
        
        # Create a pattern based on the displacement value
        disp = selected_row['displacement_cm']
        Z = np.sin(np.sqrt(X**2 + Y**2) - disp * 3) * np.cos(Y * disp)
        
        fig.add_trace(go.Contour(
            z=Z,
            colorscale='Jet',
            contours=dict(
                start=-1,
                end=1,
                size=0.1,
                showlabels=False
            )
        ))
        
        fig.update_layout(
            title=f"Interferogram - {selected_date}",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Add a play button to animate through the dates
    if st.button("Play Animation"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(len(dates)):
            # Update progress bar and status text
            progress_bar.progress(i / (len(dates) - 1))
            status_text.text(f"Processing frame {i+1}/{len(dates)}: {dates[i]}")
            
            # This would update the visualization in a real implementation
            # Here we just add a small delay to simulate animation
            time.sleep(0.1)
            
        progress_bar.progress(1.0)
        status_text.text("Animation complete!")
        
        # Reset to the latest date
        st.experimental_rerun()