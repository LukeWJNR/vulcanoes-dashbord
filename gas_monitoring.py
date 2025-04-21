"""
Volcanic Gas Monitoring Utilities for the Volcano Dashboard

This module provides functions to simulate and visualize gas emissions data,
including radioactive isotopes and other gas species used for monitoring volcanoes.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Isotope half-lives in days
HALF_LIVES = {
    'Rn-222': 3.8,
    'Pb-210': 8030,  # ~22 years
    'Bi-210': 5.0,
    'Po-210': 138.4
}

def calculate_decay_constant(half_life_days: float) -> float:
    """
    Calculate decay constant from half-life
    
    Args:
        half_life_days (float): Half-life in days
        
    Returns:
        float: Decay constant in days^-1
    """
    return np.log(2) / half_life_days

def simulate_radioactive_disequilibria(
    magma_residence_time: float,
    gas_transfer_time: float,
    volatility_factors: Dict[str, float]
) -> Dict[str, float]:
    """
    Simulate radioactive disequilibria in volcanic gas emissions
    
    Args:
        magma_residence_time (float): Residence time of magma in the degassing reservoir (days)
        gas_transfer_time (float): Transfer time of gas from reservoir to surface (days)
        volatility_factors (Dict[str, float]): Relative volatility of each isotope
        
    Returns:
        Dict[str, float]: Activity ratios for different isotope pairs
    """
    # Calculate decay constants
    decay_constants = {isotope: calculate_decay_constant(half_life) for isotope, half_life in HALF_LIVES.items()}
    
    # Initialize results
    activity_ratios = {}
    
    # Calculate Po-210/Pb-210 ratio
    if magma_residence_time > 0:
        # Dynamic degassing model with continuous regeneration of Po-210
        pb_volatility = volatility_factors.get('Pb-210', 0.1)
        po_volatility = volatility_factors.get('Po-210', 0.8)
        
        lambda_pb = decay_constants['Pb-210']
        lambda_po = decay_constants['Po-210']
        
        # Activity ratio calculation based on magma residence time
        ratio_po_pb = (po_volatility / pb_volatility) * (1 + (lambda_po / (lambda_po - lambda_pb)) * 
                                                      (np.exp(-lambda_pb * magma_residence_time) - 
                                                       np.exp(-lambda_po * magma_residence_time)))
        
        # Account for decay during gas transfer
        ratio_po_pb *= np.exp(-lambda_po * gas_transfer_time) / np.exp(-lambda_pb * gas_transfer_time)
        
    else:
        # Static degassing model (instantaneous degassing)
        ratio_po_pb = volatility_factors.get('Po-210', 0.8) / volatility_factors.get('Pb-210', 0.1)
        ratio_po_pb *= np.exp(-decay_constants['Po-210'] * gas_transfer_time)
    
    activity_ratios['Po-210/Pb-210'] = ratio_po_pb
    
    # Calculate Bi-210/Pb-210 ratio
    bi_volatility = volatility_factors.get('Bi-210', 0.4)
    pb_volatility = volatility_factors.get('Pb-210', 0.1)
    
    lambda_bi = decay_constants['Bi-210']
    lambda_pb = decay_constants['Pb-210']
    
    if magma_residence_time > 0:
        # Dynamic degassing with Bi-210 regeneration
        ratio_bi_pb = (bi_volatility / pb_volatility) * (1 + (lambda_bi / (lambda_bi - lambda_pb)) *
                                                      (np.exp(-lambda_pb * magma_residence_time) -
                                                       np.exp(-lambda_bi * magma_residence_time)))
    else:
        # Static degassing
        ratio_bi_pb = bi_volatility / pb_volatility
    
    # Account for decay during gas transfer
    ratio_bi_pb *= np.exp(-lambda_bi * gas_transfer_time) / np.exp(-lambda_pb * gas_transfer_time)
    
    activity_ratios['Bi-210/Pb-210'] = ratio_bi_pb
    
    # Include Rn-222 effects if residence time is significant
    if magma_residence_time > 0:
        rn_volatility = volatility_factors.get('Rn-222', 0.95)  # Radon is highly volatile
        lambda_rn = decay_constants['Rn-222']
        
        # Effect of Rn-222 decay producing Pb-210 in gas phase
        rn_decay_factor = (rn_volatility / pb_volatility) * (lambda_rn / (lambda_rn - lambda_pb)) * \
                        (np.exp(-lambda_pb * magma_residence_time) - np.exp(-lambda_rn * magma_residence_time))
        
        # Adjust activity ratios to account for Pb-210 produced from Rn-222 decay
        activity_ratios['Rn-222/Pb-210'] = rn_volatility / pb_volatility * np.exp(-lambda_rn * gas_transfer_time)
        
        # Modified Po-210/Pb-210 and Bi-210/Pb-210 ratios accounting for additional Pb-210 from Rn-222
        if rn_decay_factor > 0:
            pb_enrichment_factor = 1 + rn_decay_factor
            activity_ratios['Po-210/Pb-210-corrected'] = activity_ratios['Po-210/Pb-210'] / pb_enrichment_factor
            activity_ratios['Bi-210/Pb-210-corrected'] = activity_ratios['Bi-210/Pb-210'] / pb_enrichment_factor
    
    return activity_ratios

def simulate_gas_emissions(
    simulation_days: int, 
    eruption_probability: float,
    eruption_days: List[int] = None,
    scenario: str = "Gradual Buildup",
    volcano_type: str = "stratovolcano"
) -> Dict[str, np.ndarray]:
    """
    Simulate volcanic gas emissions time series based on volcano type
    
    Args:
        simulation_days (int): Number of days to simulate
        eruption_probability (float): Probability of eruption (0-100)
        eruption_days (List[int], optional): Days when eruptions occur
        scenario (str): Type of eruption scenario
        volcano_type (str): Type of volcano (affects gas composition)
        
    Returns:
        Dict[str, np.ndarray]: Dictionary of simulated gas emission time series
    """
    # Initialize result arrays
    timestamps = [datetime.now() + timedelta(days=i) for i in range(simulation_days)]
    so2_flux = np.zeros(simulation_days)
    co2_flux = np.zeros(simulation_days)
    h2s_flux = np.zeros(simulation_days)
    hcl_flux = np.zeros(simulation_days)
    hf_flux = np.zeros(simulation_days)
    radon_activity = np.zeros(simulation_days)
    
    # Determine if eruption occurs based on probability
    eruption_occurs = eruption_days is not None or np.random.random() < (eruption_probability / 100)
    
    # Set eruption day if eruption occurs and not specified
    if eruption_occurs and eruption_days is None:
        if scenario == "Sudden Explosion":
            eruption_days = [np.random.randint(1, int(simulation_days * 0.7))]
        elif scenario == "Multiple Events":
            first_day = np.random.randint(1, int(simulation_days * 0.4))
            second_day = np.random.randint(first_day + 2, simulation_days - 1)
            eruption_days = [first_day, second_day]
        else:  # Gradual Buildup or False Alarm
            eruption_days = [np.random.randint(int(simulation_days * 0.6), simulation_days - 1)]
    elif not eruption_occurs:
        eruption_days = []
    
    # Base values for gas emissions (in tonnes/day for SO2, CO2; kg/day for others)
    # These will be modified based on volcano type
    base_values = {
        'so2': 1000,   # SO2 flux in tonnes/day (typical for moderate degassing)
        'co2': 8000,   # CO2 flux in tonnes/day
        'h2s': 100,    # H2S flux in kg/day
        'hcl': 500,    # HCl flux in kg/day
        'hf': 50,      # HF flux in kg/day
        'radon': 1.0   # Radon activity (relative units)
    }
    
    # Base maximum values during eruption
    base_max_values = {
        'so2': 10000,   # SO2 flux in tonnes/day during eruption
        'co2': 50000,   # CO2 flux in tonnes/day
        'h2s': 1000,    # H2S flux in kg/day
        'hcl': 5000,    # HCl flux in kg/day
        'hf': 500,      # HF flux in kg/day
        'radon': 50.0   # Radon activity during eruption
    }
    
    # Apply volcano type-specific modifiers
    baseline = base_values.copy()
    max_values = base_max_values.copy()
    
    volcano_type = volcano_type.lower()
    
    # Modify gas signatures based on volcano type
    if 'shield' in volcano_type:
        # Shield volcanoes (e.g., Hawaiian) - high SO2, lower HCl/HF, high CO2/SO2 ratio
        baseline['so2'] *= 1.5
        baseline['co2'] *= 2.0
        baseline['hcl'] *= 0.7
        baseline['hf'] *= 0.6
        max_values['so2'] *= 1.2
        max_values['co2'] *= 1.5
        
    elif 'stratovolcano' in volcano_type:
        # Stratovolcanoes (e.g., Fuji, Vesuvius) - higher HCl, HF, moderate SO2
        baseline['hcl'] *= 1.4
        baseline['hf'] *= 1.3
        max_values['hcl'] *= 1.5
        max_values['hf'] *= 1.6
        
    elif 'caldera' in volcano_type:
        # Caldera systems (e.g., Yellowstone) - high CO2, high H2S/SO2 ratio
        baseline['co2'] *= 2.5
        baseline['h2s'] *= 1.8
        baseline['radon'] *= 1.3
        max_values['co2'] *= 1.8
        max_values['h2s'] *= 2.0
        
    elif 'fissure' in volcano_type or 'system' in volcano_type:
        # Fissure systems (common in Iceland) - high volume SO2, moderate HCl
        baseline['so2'] *= 1.8
        baseline['co2'] *= 1.2
        max_values['so2'] *= 2.0
        
    elif 'subglacial' in volcano_type or 'jökull' in volcano_type:
        # Subglacial volcanoes - reduced gas emissions due to ice, but sudden release
        baseline['so2'] *= 0.7
        baseline['co2'] *= 0.8
        baseline['hcl'] *= 0.6
        baseline['hf'] *= 0.6
        max_values['so2'] *= 2.2  # Sudden large release during eruption
        max_values['h2s'] *= 1.8
    
    # Iceland-specific modifications
    if 'iceland' in volcano_type or 'reykjanes' in volcano_type:
        # Icelandic volcanoes typically have higher fluorine content
        baseline['hf'] *= 1.4
        max_values['hf'] *= 1.5
        
        # And often higher radon precursors due to extensive fracture systems
        baseline['radon'] *= 1.2
        max_values['radon'] *= 1.3
    
    # Create gas emission time series based on scenario
    for i in range(simulation_days):
        if eruption_days and i in eruption_days:
            # Eruption day - peak values
            so2_flux[i] = max_values['so2'] * (0.8 + 0.4 * np.random.random())
            co2_flux[i] = max_values['co2'] * (0.7 + 0.6 * np.random.random())
            h2s_flux[i] = max_values['h2s'] * (0.6 + 0.8 * np.random.random())
            hcl_flux[i] = max_values['hcl'] * (0.9 + 0.2 * np.random.random())
            hf_flux[i] = max_values['hf'] * (0.8 + 0.4 * np.random.random())
            radon_activity[i] = max_values['radon'] * (0.7 + 0.6 * np.random.random())
            
        elif any(abs(i - eruption_day) == 1 for eruption_day in (eruption_days or [])):
            # Day before/after eruption - elevated values
            so2_flux[i] = baseline['so2'] * (2 + 3 * np.random.random())
            co2_flux[i] = baseline['co2'] * (3 + 2 * np.random.random())
            h2s_flux[i] = baseline['h2s'] * (2 + 3 * np.random.random())
            hcl_flux[i] = baseline['hcl'] * (2 + 2 * np.random.random())
            hf_flux[i] = baseline['hf'] * (2 + 2 * np.random.random())
            radon_activity[i] = baseline['radon'] * (5 + 10 * np.random.random())
            
        elif scenario == "Gradual Buildup" and eruption_days and min(eruption_days) > i:
            # Build-up period before eruption
            progress = i / min(eruption_days)
            so2_flux[i] = baseline['so2'] * (1 + 4 * progress**2) * (0.9 + 0.2 * np.random.random())
            co2_flux[i] = baseline['co2'] * (1 + 5 * progress**3) * (0.8 + 0.4 * np.random.random())
            h2s_flux[i] = baseline['h2s'] * (1 + 3 * progress**2) * (0.85 + 0.3 * np.random.random())
            hcl_flux[i] = baseline['hcl'] * (1 + 4 * progress**1.5) * (0.9 + 0.2 * np.random.random())
            hf_flux[i] = baseline['hf'] * (1 + 4 * progress**1.5) * (0.9 + 0.2 * np.random.random())
            radon_activity[i] = baseline['radon'] * (1 + 15 * progress**2) * (0.8 + 0.4 * np.random.random())
            
        else:
            # Normal background degassing with random variation
            # Add some sinusoidal patterns to simulate natural cycles
            cycle = 0.5 * np.sin(i * 0.4) + 0.3 * np.sin(i * 0.8 + 1) + 0.2 * np.sin(i * 0.2 + 2)
            variation = 0.2 * cycle + 0.8 * np.random.random()
            
            so2_flux[i] = baseline['so2'] * (0.7 + 0.6 * variation)
            co2_flux[i] = baseline['co2'] * (0.8 + 0.4 * variation)
            h2s_flux[i] = baseline['h2s'] * (0.7 + 0.6 * variation)
            hcl_flux[i] = baseline['hcl'] * (0.8 + 0.4 * variation)
            hf_flux[i] = baseline['hf'] * (0.8 + 0.4 * variation)
            radon_activity[i] = baseline['radon'] * (0.6 + 0.8 * variation)
    
    return {
        'timestamps': timestamps,
        'so2_flux': so2_flux,
        'co2_flux': co2_flux,
        'h2s_flux': h2s_flux,
        'hcl_flux': hcl_flux,
        'hf_flux': hf_flux,
        'radon_activity': radon_activity
    }

def plot_gas_emissions(gas_data: Dict[str, np.ndarray], eruption_days: List[int] = None) -> go.Figure:
    """
    Create a plotly figure visualizing gas emissions data
    
    Args:
        gas_data (Dict[str, np.ndarray]): Dictionary of gas emission time series
        eruption_days (List[int], optional): List of days when eruptions occurred
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Format dates for plotting
    dates = [ts.strftime("%Y-%m-%d") for ts in gas_data['timestamps']]
    days = [f"Day {i+1}" for i in range(len(dates))]
    
    # Create figure
    fig = go.Figure()
    
    # Add SO2 trace
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_data['so2_flux'],
        mode='lines+markers',
        name='SO₂ Flux (t/day)',
        line=dict(color='red', width=2)
    ))
    
    # Add CO2 trace (scaled down for comparison)
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_data['co2_flux'] / 10,  # Scale down to fit on same plot
        mode='lines+markers',
        name='CO₂ Flux (t/day ÷ 10)',
        line=dict(color='blue', width=2)
    ))
    
    # Add HCl trace
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_data['hcl_flux'] / 10,  # Scale to fit
        mode='lines+markers',
        name='HCl Flux (kg/day ÷ 10)',
        line=dict(color='green', width=2)
    ))
    
    # Add Radon activity
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_data['radon_activity'],
        mode='lines+markers',
        name='Radon Activity (rel. units)',
        line=dict(color='purple', width=2)
    ))
    
    # Add eruption markers if provided
    if eruption_days:
        for day in eruption_days:
            if day < len(days):
                fig.add_vline(
                    x=day,
                    line=dict(color='red', width=2, dash='dash'),
                    annotation_text="Eruption",
                    annotation_position="top right"
                )
    
    # Update layout
    fig.update_layout(
        title='Volcanic Gas Emissions Over Time',
        xaxis_title='Simulation Timeline',
        yaxis_title='Gas Flux / Activity',
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

def calculate_gas_ratios(gas_data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """
    Calculate gas ratios which are important for volcano monitoring
    
    Args:
        gas_data (Dict[str, np.ndarray]): Dictionary of gas emission time series
        
    Returns:
        Dict[str, np.ndarray]: Dictionary of calculated gas ratios
    """
    # Calculate common gas ratios used in volcano monitoring
    co2_so2_ratio = gas_data['co2_flux'] / gas_data['so2_flux']
    h2s_so2_ratio = gas_data['h2s_flux'] / (gas_data['so2_flux'] * 1000)  # Convert SO2 to kg
    hcl_so2_ratio = gas_data['hcl_flux'] / (gas_data['so2_flux'] * 1000)  # Convert SO2 to kg
    hf_hcl_ratio = gas_data['hf_flux'] / gas_data['hcl_flux']
    
    return {
        'co2_so2_ratio': co2_so2_ratio,
        'h2s_so2_ratio': h2s_so2_ratio,
        'hcl_so2_ratio': hcl_so2_ratio,
        'hf_hcl_ratio': hf_hcl_ratio
    }

def plot_gas_ratios(gas_data: Dict[str, np.ndarray], gas_ratios: Dict[str, np.ndarray], 
                   eruption_days: List[int] = None) -> go.Figure:
    """
    Create a plotly figure visualizing gas ratio data
    
    Args:
        gas_data (Dict[str, np.ndarray]): Dictionary of gas emission time series
        gas_ratios (Dict[str, np.ndarray]): Dictionary of calculated gas ratios
        eruption_days (List[int], optional): List of days when eruptions occurred
        
    Returns:
        go.Figure: Plotly figure object
    """
    # Format dates for plotting
    dates = [ts.strftime("%Y-%m-%d") for ts in gas_data['timestamps']]
    days = [f"Day {i+1}" for i in range(len(dates))]
    
    # Create figure
    fig = go.Figure()
    
    # Add CO2/SO2 trace
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_ratios['co2_so2_ratio'],
        mode='lines+markers',
        name='CO₂/SO₂ Ratio',
        line=dict(color='coral', width=2)
    ))
    
    # Add HCl/SO2 trace
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_ratios['hcl_so2_ratio'] * 1000,  # Scale up for visibility
        mode='lines+markers',
        name='HCl/SO₂ Ratio (×1000)',
        line=dict(color='green', width=2)
    ))
    
    # Add HF/HCl trace
    fig.add_trace(go.Scatter(
        x=days,
        y=gas_ratios['hf_hcl_ratio'],
        mode='lines+markers',
        name='HF/HCl Ratio',
        line=dict(color='purple', width=2)
    ))
    
    # Add eruption markers if provided
    if eruption_days:
        for day in eruption_days:
            if day < len(days):
                fig.add_vline(
                    x=day,
                    line=dict(color='red', width=2, dash='dash'),
                    annotation_text="Eruption",
                    annotation_position="top right"
                )
    
    # Update layout
    fig.update_layout(
        title='Volcanic Gas Ratios Over Time',
        xaxis_title='Simulation Timeline',
        yaxis_title='Gas Ratio',
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