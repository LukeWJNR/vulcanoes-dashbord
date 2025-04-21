"""
Comprehensive eruption animation showing the full lifecycle from magma buildup to eruption.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

from utils.animation_utils import determine_volcano_type, VOLCANO_TYPES, ALERT_LEVELS
from utils.magma_chamber_viz import generate_3d_magma_chamber

def generate_complete_eruption_animation(volcano_data: Dict, time_steps: int = 100) -> Dict:
    """
    Generate a comprehensive eruption animation showing the full cycle from 
    magma buildup through seismic events to lava flow and ash emission.
    Includes detailed 3D visualization of magma plumbing structure with
    connected deep and shallow reservoirs and realistic lava flows and ash emissions.
    
    Args:
        volcano_data (Dict): Volcano data dictionary
        time_steps (int): Number of time steps in the animation
        
    Returns:
        Dict: Dictionary with animation figures (timeline and 3D visualization) and metadata
    """
    # Determine volcano type and alert level
    volcano_type = determine_volcano_type(volcano_data)
    alert_level = volcano_data.get('alert_level', 'Normal')
    v_params = VOLCANO_TYPES.get(volcano_type, VOLCANO_TYPES['stratovolcano'])
    
    # Create eruption phases with approximate durations
    phases = []
    if volcano_type == 'shield':
        phases = [
            {'name': 'Magma Buildup', 'duration': 0.25, 'color': 'rgba(255,165,0,0.3)'},
            {'name': 'Increased Seismicity', 'duration': 0.15, 'color': 'rgba(255,165,0,0.5)'},
            {'name': 'Initial Fissure Formation', 'duration': 0.05, 'color': 'rgba(255,69,0,0.5)'},
            {'name': 'Lava Fountaining', 'duration': 0.20, 'color': 'rgba(255,0,0,0.6)'},
            {'name': 'Lava Flow Progression', 'duration': 0.25, 'color': 'rgba(139,0,0,0.6)'},
            {'name': 'Waning Activity', 'duration': 0.10, 'color': 'rgba(139,0,0,0.3)'}
        ]
    elif volcano_type == 'stratovolcano':
        phases = [
            {'name': 'Magma Buildup', 'duration': 0.20, 'color': 'rgba(255,165,0,0.3)'},
            {'name': 'Increased Seismicity', 'duration': 0.15, 'color': 'rgba(255,165,0,0.5)'},
            {'name': 'Phreatic Explosions', 'duration': 0.10, 'color': 'rgba(169,169,169,0.6)'},
            {'name': 'Dome Growth', 'duration': 0.10, 'color': 'rgba(255,69,0,0.5)'},
            {'name': 'Explosive Phase', 'duration': 0.15, 'color': 'rgba(255,0,0,0.7)'},
            {'name': 'Pyroclastic Flows', 'duration': 0.15, 'color': 'rgba(139,0,0,0.6)'},
            {'name': 'Ash Fallout', 'duration': 0.15, 'color': 'rgba(105,105,105,0.5)'}
        ]
    elif volcano_type == 'caldera':
        phases = [
            {'name': 'Magma Buildup', 'duration': 0.15, 'color': 'rgba(255,165,0,0.3)'},
            {'name': 'Ground Deformation', 'duration': 0.15, 'color': 'rgba(255,165,0,0.4)'},
            {'name': 'Increased Seismicity', 'duration': 0.10, 'color': 'rgba(255,165,0,0.5)'},
            {'name': 'Initial Vent Formation', 'duration': 0.05, 'color': 'rgba(255,69,0,0.5)'},
            {'name': 'Major Explosive Phase', 'duration': 0.20, 'color': 'rgba(255,0,0,0.8)'},
            {'name': 'Caldera Collapse', 'duration': 0.15, 'color': 'rgba(139,0,0,0.7)'},
            {'name': 'Widespread Ash Fallout', 'duration': 0.20, 'color': 'rgba(105,105,105,0.5)'}
        ]
    elif volcano_type == 'cinder_cone':
        phases = [
            {'name': 'Magma Buildup', 'duration': 0.15, 'color': 'rgba(255,165,0,0.3)'},
            {'name': 'Increased Seismicity', 'duration': 0.15, 'color': 'rgba(255,165,0,0.5)'},
            {'name': 'Initial Vent Opening', 'duration': 0.05, 'color': 'rgba(255,69,0,0.5)'},
            {'name': 'Strombolian Explosions', 'duration': 0.25, 'color': 'rgba(255,0,0,0.6)'},
            {'name': 'Cone Growth', 'duration': 0.20, 'color': 'rgba(139,0,0,0.5)'},
            {'name': 'Lava Flow Emission', 'duration': 0.20, 'color': 'rgba(139,0,0,0.6)'}
        ]
    elif volcano_type == 'lava_dome':
        phases = [
            {'name': 'Magma Buildup', 'duration': 0.15, 'color': 'rgba(255,165,0,0.3)'},
            {'name': 'Increased Seismicity', 'duration': 0.15, 'color': 'rgba(255,165,0,0.5)'},
            {'name': 'Ground Deformation', 'duration': 0.15, 'color': 'rgba(255,165,0,0.4)'},
            {'name': 'Dome Extrusion', 'duration': 0.20, 'color': 'rgba(255,69,0,0.6)'},
            {'name': 'Dome Collapse Events', 'duration': 0.15, 'color': 'rgba(255,0,0,0.7)'},
            {'name': 'Pyroclastic Density Currents', 'duration': 0.10, 'color': 'rgba(139,0,0,0.6)'},
            {'name': 'Degassing and Stabilization', 'duration': 0.10, 'color': 'rgba(105,105,105,0.4)'}
        ]
    else:
        # Default phases for any other volcano type
        phases = [
            {'name': 'Magma Buildup', 'duration': 0.20, 'color': 'rgba(255,165,0,0.3)'},
            {'name': 'Increased Seismicity', 'duration': 0.15, 'color': 'rgba(255,165,0,0.5)'},
            {'name': 'Initial Activity', 'duration': 0.10, 'color': 'rgba(255,69,0,0.5)'},
            {'name': 'Eruptive Phase', 'duration': 0.30, 'color': 'rgba(255,0,0,0.7)'},
            {'name': 'Waning Activity', 'duration': 0.25, 'color': 'rgba(139,0,0,0.4)'}
        ]
    
    # Calculate phase boundaries for visualization
    phase_boundaries = [0]
    phase_mids = []
    for phase in phases:
        next_boundary = phase_boundaries[-1] + phase['duration']
        phase_boundaries.append(next_boundary)
        phase_mids.append((phase_boundaries[-2] + phase_boundaries[-1]) / 2)
    
    # Normalize phase boundaries to [0, 1]
    phase_boundaries = [x / phase_boundaries[-1] for x in phase_boundaries]
    phase_mids = [x / phase_boundaries[-1] for x in phase_mids]
    
    # Generate time steps for animation
    time_points = np.linspace(0, 1, time_steps)
    
    # Define parameters to track through eruption
    parameters = {
        'Magma Volume': {
            'start': 0.1,
            'patterns': {
                'shield': [0.2, 0.4, 0.7, 0.9, 0.8, 0.5],
                'stratovolcano': [0.3, 0.5, 0.6, 0.8, 0.4, 0.2, 0.1],
                'caldera': [0.3, 0.5, 0.7, 0.8, 0.2, 0.1, 0.1],
                'cinder_cone': [0.2, 0.4, 0.6, 0.9, 0.7, 0.4],
                'lava_dome': [0.3, 0.5, 0.7, 0.9, 0.5, 0.3, 0.2]
            },
            'color': 'rgba(255,69,0,1)'  # Orange-red
        },
        'Seismic Activity': {
            'start': 0.05,
            'patterns': {
                'shield': [0.1, 0.8, 0.4, 0.3, 0.2, 0.1],
                'stratovolcano': [0.1, 0.7, 0.5, 0.4, 0.9, 0.6, 0.2],
                'caldera': [0.1, 0.5, 0.8, 0.6, 0.9, 0.7, 0.3],
                'cinder_cone': [0.1, 0.7, 0.4, 0.8, 0.5, 0.2],
                'lava_dome': [0.1, 0.6, 0.5, 0.4, 0.9, 0.7, 0.3]
            },
            'color': 'rgba(30,144,255,1)'  # Dodger blue
        },
        'Ground Deformation': {
            'start': 0.05,
            'patterns': {
                'shield': [0.2, 0.5, 0.7, 0.6, 0.5, 0.4],
                'stratovolcano': [0.2, 0.6, 0.5, 0.7, 0.2, 0.0, -0.1],
                'caldera': [0.3, 0.6, 0.7, 0.5, 0.2, -0.3, -0.2],
                'cinder_cone': [0.1, 0.4, 0.5, 0.7, 0.6, 0.4],
                'lava_dome': [0.3, 0.6, 0.8, 0.9, 0.5, 0.3, 0.2]
            },
            'color': 'rgba(0,128,0,1)'  # Green
        },
        'Lava Emission': {
            'start': 0,
            'patterns': {
                'shield': [0, 0, 0.1, 0.9, 1.0, 0.6],
                'stratovolcano': [0, 0, 0, 0.3, 0.8, 0.6, 0.2],
                'caldera': [0, 0, 0, 0, 0.7, 0.4, 0.1],
                'cinder_cone': [0, 0, 0.1, 0.5, 0.7, 0.9],
                'lava_dome': [0, 0, 0, 0.7, 0.5, 0.2, 0.1]
            },
            'color': 'rgba(220,20,60,1)'  # Crimson
        },
        'Ash Emission': {
            'start': 0,
            'patterns': {
                'shield': [0, 0, 0, 0.2, 0.3, 0.1],
                'stratovolcano': [0, 0, 0.3, 0.5, 0.9, 0.8, 0.5],
                'caldera': [0, 0, 0, 0.2, 0.9, 0.8, 0.6],
                'cinder_cone': [0, 0, 0.1, 0.7, 0.5, 0.2],
                'lava_dome': [0, 0, 0, 0.2, 0.8, 0.7, 0.3]
            },
            'color': 'rgba(128,128,128,1)'  # Gray
        },
        'Gas Emission': {
            'start': 0.1,
            'patterns': {
                'shield': [0.2, 0.4, 0.6, 0.8, 0.7, 0.5],
                'stratovolcano': [0.2, 0.5, 0.7, 0.6, 0.9, 0.7, 0.4],
                'caldera': [0.3, 0.6, 0.8, 0.7, 0.9, 0.7, 0.5],
                'cinder_cone': [0.1, 0.3, 0.5, 0.8, 0.6, 0.4],
                'lava_dome': [0.2, 0.4, 0.6, 0.8, 0.9, 0.7, 0.5]
            },
            'color': 'rgba(255,215,0,1)'  # Gold
        }
    }
    
    # Generate data for each parameter
    data = {param: [] for param in parameters}
    current_values = {param: parameters[param]['start'] for param in parameters}
    
    # Helper function to get value at specific phase point
    def get_phase_value(phase_point, pattern):
        # Find which phase we're in
        for i in range(len(phase_boundaries) - 1):
            if phase_boundaries[i] <= phase_point < phase_boundaries[i+1]:
                # Calculate position within this phase
                phase_progress = (phase_point - phase_boundaries[i]) / (phase_boundaries[i+1] - phase_boundaries[i])
                
                # Get values at phase boundaries
                start_val = pattern[i] if i < len(pattern) else 0
                end_val = pattern[i+1] if i+1 < len(pattern) else 0
                
                # Linear interpolation
                return start_val + phase_progress * (end_val - start_val)
        return 0
    
    # Generate data points with smooth transitions
    for t in time_points:
        for param in parameters:
            pattern = parameters[param]['patterns'].get(volcano_type, parameters[param]['patterns']['stratovolcano'])
            target = get_phase_value(t, pattern)
            
            # Smooth transition - don't jump directly to target
            rate = 0.15  # How quickly to approach target (0.1 = slow, 0.9 = fast)
            current_values[param] = current_values[param] * (1 - rate) + target * rate
            
            # Add some noise for realism
            noise = np.random.normal(0, 0.02)
            value = max(0, min(1, current_values[param] + noise))
            data[param].append(value)
    
    # Create animation
    fig = make_subplots(
        rows=7, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.15, 0.14, 0.14, 0.14, 0.14, 0.14, 0.15]
    )
    
    # Add phase bars at the top
    for i, phase in enumerate(phases):
        fig.add_trace(
            go.Bar(
                x=[(phase_boundaries[i+1] - phase_boundaries[i]) * 100],
                y=[phase['name']],
                orientation='h',
                marker=dict(color=phase['color']),
                hoverinfo='text',
                hovertext=f"{phase['name']}: {phase['duration']*100:.0f}% of eruption duration",
                showlegend=False
            ),
            row=1, col=1
        )
    
    # Add parameter traces
    param_names = list(parameters.keys())
    for i, param in enumerate(param_names):
        row = i + 2  # Parameters start from row 2
        fig.add_trace(
            go.Scatter(
                x=time_points * 100,  # Convert to percentage for x-axis
                y=data[param],
                mode='lines',
                name=param,
                line=dict(width=2, color=parameters[param]['color'])
            ),
            row=row, col=1
        )
    
    # Add initial marker positions
    markers = []
    for i, param in enumerate(param_names):
        row = i + 2
        markers.append(
            go.Scatter(
                x=[time_points[0] * 100],
                y=[data[param][0]],
                mode='markers',
                marker=dict(size=10, color=parameters[param]['color']),
                showlegend=False
            )
        )
        fig.add_trace(markers[-1], row=row, col=1)
    
    # Create frames for animation
    frames = []
    for i in range(len(time_points)):
        frame_data = []
        
        # Keep phase bars the same
        for j in range(len(phases)):
            frame_data.append(go.Bar(
                x=[(phase_boundaries[j+1] - phase_boundaries[j]) * 100],
                y=[phases[j]['name']],
                marker=dict(color=phases[j]['color'])
            ))
        
        # Update parameter lines and markers
        for j, param in enumerate(param_names):
            # Add line trace with data up to current point
            frame_data.append(go.Scatter(
                x=time_points[:i+1] * 100,
                y=data[param][:i+1],
                line=dict(width=2, color=parameters[param]['color'])
            ))
            
            # Add marker at current position
            frame_data.append(go.Scatter(
                x=[time_points[i] * 100],
                y=[data[param][i]],
                mode='markers',
                marker=dict(size=10, color=parameters[param]['color'])
            ))
        
        # Highlight current phase
        current_t = time_points[i]
        current_phase_idx = 0
        for j in range(len(phase_boundaries) - 1):
            if phase_boundaries[j] <= current_t < phase_boundaries[j+1]:
                current_phase_idx = j
                break
        
        # Create vertical line showing current time
        for j in range(len(param_names)):
            frame_data.append(go.Scatter(
                x=[time_points[i] * 100, time_points[i] * 100],
                y=[0, 1],
                mode='lines',
                line=dict(color='rgba(0,0,0,0.5)', width=1, dash='dot'),
                showlegend=False
            ))
        
        # Create frame with all traces
        trace_indices = list(range(len(phases) + 2 * len(param_names) + len(param_names)))
        frames.append(go.Frame(data=frame_data, traces=trace_indices, name=f"frame{i}"))
    
    # Update layout
    fig.update_layout(
        title=f"Complete Eruption Sequence for {volcano_data.get('name', 'Volcano')} ({volcano_type.replace('_', ' ').title()})",
        height=800,
        barmode='stack',
        xaxis=dict(title="Eruption Timeline (%)", range=[0, 100]),
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': 'Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 100, 'redraw': True},
                        'fromcurrent': True,
                        'transition': {'duration': 50}
                    }]
                },
                {
                    'label': 'Pause',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'mode': 'immediate',
                        'transition': {'duration': 0}
                    }]
                }
            ],
            'x': 0.1,
            'y': 0
        }]
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Eruption Phases", row=1, col=1)
    for i, param in enumerate(param_names):
        fig.update_yaxes(
            title_text=param,
            range=[-0.05, 1.05],
            row=i+2, col=1
        )
    
    # Add frames to figure
    fig.frames = frames
    
    # Generate 3D magma chamber visualization based on the volcano type
    # Create different alert level visualizations based on eruption phase
    alert_levels = ['Normal', 'Advisory', 'Watch', 'Warning']
    magma_chamber_figs = {}
    
    # Generate 3D visualization for each alert level
    for alert in alert_levels:
        magma_fig, chamber_metrics = generate_3d_magma_chamber(volcano_type, alert)
        magma_chamber_figs[alert] = {
            'figure': magma_fig,
            'metrics': chamber_metrics
        }
    
    # Create lava flow patterns based on volcano type
    lava_flows = {}
    if volcano_type == 'shield':
        lava_color = 'rgb(255, 80, 0)'  # Bright orange for hot basaltic lava
        lava_flow_type = "pahoehoe_to_aa"  # Pahoehoe (smooth) to A'a (rough) transition
    elif volcano_type in ['stratovolcano', 'caldera']:
        lava_color = 'rgb(220, 20, 0)'  # Darker red for cooler, more viscous lava
        lava_flow_type = "blocky"  # Blocky or A'a flows
    elif volcano_type == 'lava_dome':
        lava_color = 'rgb(180, 10, 0)'  # Darker red for cooler, highly viscous lava
        lava_flow_type = "viscous_dome"  # Slow-moving, thick flows forming a dome
    else:  # cinder_cone or other
        lava_color = 'rgb(230, 25, 0)'  # Intermediate red color
        lava_flow_type = "aa"  # A'a flows (rough, blocky surface)
    
    # Prepare output dictionary
    animation_data = {
        'figure': fig,
        'volcano_type': volcano_type,
        'phases': phases,
        'parameters': parameters,
        'data': data,
        'volcano_name': volcano_data.get('name', 'Unknown'),
        'magma_chamber_visualizations': magma_chamber_figs,
        'lava_flow': {
            'color': lava_color,
            'type': lava_flow_type
        }
    }
    
    return animation_data