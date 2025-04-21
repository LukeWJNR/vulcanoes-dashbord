"""
Specialized visualization functions for magma chamber dynamics and eruption processes.

This module provides 3D visualizations of magma chambers for different volcano types.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Tuple, List, Optional, Any, Union
import math
from datetime import datetime, timedelta
import random

from utils.animation_utils import VOLCANO_TYPES, ALERT_LEVELS, determine_volcano_type
from utils.cinematic_animation import ensure_valid_color

def generate_3d_magma_chamber(volcano_type: str, alert_level: str) -> go.Figure:
    """
    Generate a 3D model of a volcano's magma chamber and plumbing system
    with metrics for chamber size and magma volume
    
    Args:
        volcano_type (str): Type of volcano
        alert_level (str): Current alert level
        
    Returns:
        go.Figure: Interactive 3D visualization with metrics
    """
    # Get type-specific parameters
    v_params = VOLCANO_TYPES.get(volcano_type, VOLCANO_TYPES['stratovolcano'])
    a_params = ALERT_LEVELS.get(alert_level, ALERT_LEVELS['Normal'])
    
    # Alert level parameters
    alert_colors = {
        'Normal': ['rgba(0,200,0,0.7)', 'rgba(0,200,0,0.2)'],
        'Advisory': ['rgba(255,200,0,0.7)', 'rgba(255,200,0,0.2)'],
        'Watch': ['rgba(255,120,0,0.7)', 'rgba(255,120,0,0.2)'],
        'Warning': ['rgba(255,0,0,0.7)', 'rgba(255,0,0,0.2)']
    }
    magma_color = alert_colors.get(alert_level, ['rgba(255,0,0,0.7)', 'rgba(255,0,0,0.2)'])
    
    # Deformation multipliers based on alert level
    deformation_rate = {
        'Normal': 0.2,
        'Advisory': 0.5,
        'Watch': 0.8,
        'Warning': 1.0
    }.get(alert_level, 0.2)
    
    # Create 3D figure
    fig = go.Figure()
    
    # Generate surface points - will differ by volcano type
    if volcano_type == 'shield':
        # Shield volcano: broad, low slope with shallow magma chamber
        # Surface
        x = np.linspace(-10, 10, 40)
        y = np.linspace(-10, 10, 40)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        # Gentle sloping surface with broad base
        Z_surface = 5 * np.exp(-0.05 * R**2)
        
        # Add surface deformation based on alert level
        # Shield volcanoes often show bulging with minimal summit deformation
        deform = deformation_rate * np.exp(-0.1 * (R - 5)**2) * 0.3
        Z_surface = Z_surface + deform
        
        # Add the surface
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z_surface,
            colorscale='Earth',
            showscale=False,
            opacity=0.9
        ))
        
        # Shield volcanoes have both shallow and deep magma reservoirs based on research
        
        # Shallow magma chamber - relatively close to surface, broad
        shallow_chamber_depth = -1.5
        shallow_chamber_x = np.linspace(-4, 4, 30)
        shallow_chamber_y = np.linspace(-4, 4, 30)
        shallow_chamber_X, shallow_chamber_Y = np.meshgrid(shallow_chamber_x, shallow_chamber_y)
        shallow_chamber_R = np.sqrt(shallow_chamber_X**2 + shallow_chamber_Y**2)
        shallow_chamber_Z = shallow_chamber_depth - 1.0 * np.exp(-0.1 * shallow_chamber_R**2)
        
        # Shallow magma chamber
        fig.add_trace(go.Surface(
            x=shallow_chamber_X, y=shallow_chamber_Y, z=shallow_chamber_Z,
            colorscale=[[0, magma_color[0]], [1, magma_color[1]]],
            showscale=False,
            opacity=0.8,
            name="Shallow Magma Chamber"
        ))
        
        # Deep crustal reservoir - larger and deeper
        deep_reservoir_depth = -5.0
        deep_reservoir_x = np.linspace(-6, 6, 30)
        deep_reservoir_y = np.linspace(-6, 6, 30)
        deep_reservoir_X, deep_reservoir_Y = np.meshgrid(deep_reservoir_x, deep_reservoir_y)
        deep_reservoir_R = np.sqrt(deep_reservoir_X**2 + deep_reservoir_Y**2)
        deep_reservoir_Z = deep_reservoir_depth - 1.5 * np.exp(-0.05 * deep_reservoir_R**2)
        
        # Deep crustal reservoir
        fig.add_trace(go.Surface(
            x=deep_reservoir_X, y=deep_reservoir_Y, z=deep_reservoir_Z,
            colorscale=[[0, 'rgba(255,30,30,0.6)'], [1, 'rgba(255,30,30,0.2)']],
            showscale=False,
            opacity=0.7,
            name="Deep Crustal Reservoir"
        ))
        
        # Add central conduit from shallow chamber to surface
        r = np.linspace(0, 1, 20)
        theta = np.linspace(0, 2*np.pi, 20)
        R, Theta = np.meshgrid(r, theta)
        X_conduit = 0.5 * R * np.cos(Theta)
        Y_conduit = 0.5 * R * np.sin(Theta)
        Z_top = Z_surface[20, 20]  # Summit
        Z_conduit = shallow_chamber_depth + (Z_top - shallow_chamber_depth) * (1 - R)
        
        fig.add_trace(go.Surface(
            x=X_conduit, y=Y_conduit, z=Z_conduit,
            colorscale=[[0, magma_color[0]], [1, magma_color[0]]],
            showscale=False,
            opacity=0.85,
            name="Central Conduit"
        ))
        
        # Add connection between deep reservoir and shallow chamber
        # Create a slightly curved connecting conduit
        connecting_points = []
        for t in np.linspace(0, 1, 15):
            # Create a slight curve in the connection
            x_offset = 0.3 * np.sin(t * np.pi)
            y_offset = 0.2 * np.sin(t * np.pi)
            z_pos = deep_reservoir_depth + t * (shallow_chamber_depth - deep_reservoir_depth)
            
            # Add multiple points at each level for thickness
            for angle in np.linspace(0, 2*np.pi, 8):
                radius = 0.5
                x = x_offset + radius * 0.3 * np.cos(angle)
                y = y_offset + radius * 0.3 * np.sin(angle)
                connecting_points.append((x, y, z_pos))
        
        # Add connecting conduit points
        connect_x = [p[0] for p in connecting_points]
        connect_y = [p[1] for p in connecting_points]
        connect_z = [p[2] for p in connecting_points]
        
        fig.add_trace(go.Scatter3d(
            x=connect_x,
            y=connect_y,
            z=connect_z,
            mode='markers',
            marker=dict(
                size=8,
                color=magma_color[0],
                opacity=0.8
            ),
            showlegend=False,
            name="Deep Connection"
        ))
        
        # Add lateral dikes for more active states
        if alert_level in ['Watch', 'Warning']:
            # Create radial dikes
            for angle in [0, 2*np.pi/3, 4*np.pi/3]:
                dike_x = np.linspace(0, 6 * np.cos(angle), 20)
                dike_y = np.linspace(0, 6 * np.sin(angle), 20)
                dike_z = np.linspace(shallow_chamber_depth, -0.5, 20)
                for i in range(len(dike_x)):
                    fig.add_trace(go.Scatter3d(
                        x=[dike_x[i]],
                        y=[dike_y[i]],
                        z=[dike_z[i]],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color=magma_color[0],
                            opacity=0.7
                        ),
                        showlegend=False
                    ))
    
    elif volcano_type == 'stratovolcano':
        # Stratovolcano: steep sides, deep magma chamber
        x = np.linspace(-10, 10, 40)
        y = np.linspace(-10, 10, 40)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        # Steep surface with pointed summit
        Z_surface = 10 * np.exp(-0.15 * R**2)
        
        # Add surface deformation based on alert level
        # Stratovolcanoes often show localized summit deformation
        deform = deformation_rate * np.exp(-0.5 * R**2) * 0.5
        Z_surface = Z_surface + deform
        
        # Add the surface
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z_surface,
            colorscale='Earth',
            showscale=False,
            opacity=0.9
        ))
        
        # Stratovolcanoes have vertically-oriented magmatic plumbing systems
        # with deep and shallow chambers based on research
        
        # Deep magma reservoir - larger and deeper
        deep_reservoir_depth = -10.0
        deep_reservoir_x = np.linspace(-3.5, 3.5, 30)
        deep_reservoir_y = np.linspace(-3.5, 3.5, 30)
        deep_reservoir_X, deep_reservoir_Y = np.meshgrid(deep_reservoir_x, deep_reservoir_y)
        deep_reservoir_R = np.sqrt(deep_reservoir_X**2 + deep_reservoir_Y**2)
        deep_reservoir_Z = deep_reservoir_depth - 2.0 * np.exp(-0.1 * deep_reservoir_R**2)
        
        # Deep crustal reservoir
        fig.add_trace(go.Surface(
            x=deep_reservoir_X, y=deep_reservoir_Y, z=deep_reservoir_Z,
            colorscale=[[0, 'rgba(255,20,20,0.6)'], [1, 'rgba(255,20,20,0.2)']],
            showscale=False,
            opacity=0.7,
            name="Deep Magma Reservoir"
        ))
        
        # Shallow magma chamber - closer to surface
        chamber_depth = -5.0
        chamber_x = np.linspace(-3, 3, 30)
        chamber_y = np.linspace(-3, 3, 30)
        chamber_X, chamber_Y = np.meshgrid(chamber_x, chamber_y)
        chamber_R = np.sqrt(chamber_X**2 + chamber_Y**2)
        chamber_Z = chamber_depth - 1.5 * np.exp(-0.15 * chamber_R**2)
        
        # Shallow magma chamber
        fig.add_trace(go.Surface(
            x=chamber_X, y=chamber_Y, z=chamber_Z,
            colorscale=[[0, magma_color[0]], [1, magma_color[1]]],
            showscale=False,
            opacity=0.8,
            name="Shallow Magma Chamber"
        ))
        
        # Add central conduit from shallow chamber to surface
        r = np.linspace(0, 1, 20)
        theta = np.linspace(0, 2*np.pi, 20)
        R, Theta = np.meshgrid(r, theta)
        X_conduit = 0.4 * R * np.cos(Theta)
        Y_conduit = 0.4 * R * np.sin(Theta)
        Z_top = Z_surface[20, 20]  # Summit
        Z_conduit = chamber_depth + (Z_top - chamber_depth) * (1 - R)
        
        fig.add_trace(go.Surface(
            x=X_conduit, y=Y_conduit, z=Z_conduit,
            colorscale=[[0, magma_color[0]], [1, magma_color[0]]],
            showscale=False,
            opacity=0.85,
            name="Central Conduit"
        ))
        
        # Add connection between deep reservoir and shallow chamber
        # Create a vertical connecting conduit
        connecting_points = []
        for t in np.linspace(0, 1, 15):
            z_pos = deep_reservoir_depth + t * (chamber_depth - deep_reservoir_depth)
            
            # Add multiple points at each level for thickness
            for angle in np.linspace(0, 2*np.pi, 8):
                radius = 0.3
                x = radius * 0.2 * np.cos(angle)
                y = radius * 0.2 * np.sin(angle)
                connecting_points.append((x, y, z_pos))
        
        # Add connecting conduit points
        connect_x = [p[0] for p in connecting_points]
        connect_y = [p[1] for p in connecting_points]
        connect_z = [p[2] for p in connecting_points]
        
        fig.add_trace(go.Scatter3d(
            x=connect_x,
            y=connect_y,
            z=connect_z,
            mode='markers',
            marker=dict(
                size=8,
                color=magma_color[0],
                opacity=0.8
            ),
            showlegend=False,
            name="Vertical Connection"
        ))
        
        # Add secondary magma chamber for more complex systems
        if alert_level in ['Watch', 'Warning']:
            # Secondary chamber offset from main
            sec_chamber_x = np.linspace(-2, 2, 20)
            sec_chamber_y = np.linspace(-1, 3, 20)
            sec_chamber_X, sec_chamber_Y = np.meshgrid(sec_chamber_x, sec_chamber_y)
            sec_chamber_X = sec_chamber_X + 2  # Offset
            sec_chamber_R = np.sqrt((sec_chamber_X - 2)**2 + (sec_chamber_Y - 1)**2)
            sec_chamber_Z = -3.0 - 1.0 * np.exp(-0.2 * sec_chamber_R**2)
            
            fig.add_trace(go.Surface(
                x=sec_chamber_X, y=sec_chamber_Y, z=sec_chamber_Z,
                colorscale=[[0, magma_color[0]], [1, magma_color[1]]],
                showscale=False,
                opacity=0.7
            ))
            
            # Connection between chambers
            for t in np.linspace(0, 1, 10):
                cx = 1 + t
                cy = t
                cz = chamber_depth + t * (sec_chamber_Z[10, 10] - chamber_depth)
                
                fig.add_trace(go.Scatter3d(
                    x=[cx], y=[cy], z=[cz],
                    mode='markers',
                    marker=dict(
                        size=6,
                        color=magma_color[0],
                        opacity=0.8
                    ),
                    showlegend=False
                ))
    
    elif volcano_type == 'caldera':
        # Caldera: circular depression with complex magma system
        x = np.linspace(-10, 10, 50)
        y = np.linspace(-10, 10, 50)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        # Caldera surface with central depression
        # Create a ring-like structure
        Z_surface = 4 * np.exp(-0.05 * R**2) - 2 * np.exp(-0.5 * R**2)
        
        # Add deformation - calderas can show complex inflation/deflation patterns
        deform = deformation_rate * np.cos(R) * np.exp(-0.2 * (R - 3)**2) * 0.5
        Z_surface = Z_surface + deform
        
        # Add the surface
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z_surface,
            colorscale='Earth',
            showscale=False,
            opacity=0.9
        ))
        
        # Calderas have large-volume, complex magmatic systems with ring-shaped fracture systems
        
        # Large shallow magma reservoir 
        shallow_chamber_depth = -3.0
        chamber_x = np.linspace(-6, 6, 40)
        chamber_y = np.linspace(-6, 6, 40)
        chamber_X, chamber_Y = np.meshgrid(chamber_x, chamber_y)
        chamber_R = np.sqrt(chamber_X**2 + chamber_Y**2)
        chamber_Z = shallow_chamber_depth - 2.0 * np.exp(-0.05 * chamber_R**2)
        
        # Main shallow magma reservoir
        fig.add_trace(go.Surface(
            x=chamber_X, y=chamber_Y, z=chamber_Z,
            colorscale=[[0, magma_color[0]], [1, magma_color[1]]],
            showscale=False,
            opacity=0.7,
            name="Shallow Magma Reservoir"
        ))
        
        # Add deeper magma reservoir for complex caldera systems
        deep_reservoir_depth = -8.0
        deep_reservoir_x = np.linspace(-8, 8, 40) 
        deep_reservoir_y = np.linspace(-8, 8, 40)
        deep_reservoir_X, deep_reservoir_Y = np.meshgrid(deep_reservoir_x, deep_reservoir_y)
        deep_reservoir_R = np.sqrt(deep_reservoir_X**2 + deep_reservoir_Y**2)
        deep_reservoir_Z = deep_reservoir_depth - 2.5 * np.exp(-0.03 * deep_reservoir_R**2)
        
        # Deep reservoir
        fig.add_trace(go.Surface(
            x=deep_reservoir_X, y=deep_reservoir_Y, z=deep_reservoir_Z,
            colorscale=[[0, 'rgba(255,20,20,0.5)'], [1, 'rgba(255,20,20,0.2)']],
            showscale=False,
            opacity=0.6,
            name="Deep Magma Reservoir"
        ))
        
        # Add connecting structure between deep and shallow reservoirs
        for angle in np.linspace(0, 2*np.pi, 16):
            if alert_level in ['Normal', 'Advisory'] and angle % (np.pi/4) != 0:
                continue  # Show fewer connections for lower alert levels
                
            radius = 4.0
            # Create sloped conduit from deep to shallow
            cond_x = radius * 0.7 * np.cos(angle)
            cond_y = radius * 0.7 * np.sin(angle)
            
            # Get z positions
            for t in np.linspace(0, 1, 10):
                z_pos = deep_reservoir_depth + 1 + t * (shallow_chamber_depth - deep_reservoir_depth - 1)
                
                # Add point
                fig.add_trace(go.Scatter3d(
                    x=[cond_x * (1 + 0.3 * t)],
                    y=[cond_y * (1 + 0.3 * t)],
                    z=[z_pos],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=magma_color[0],
                        opacity=0.8
                    ),
                    showlegend=False
                ))
        
        
        # Add multiple conduits - calderas often have ring fractures
        for angle in np.linspace(0, 2*np.pi, 8):
            radius = 3.0
            x_pos = radius * np.cos(angle)
            y_pos = radius * np.sin(angle)
            
            # Create conduit
            r = np.linspace(0, 1, 10)
            theta = np.linspace(0, 2*np.pi, 10)
            R, Theta = np.meshgrid(r, theta)
            X_conduit = 0.3 * R * np.cos(Theta) + x_pos
            Y_conduit = 0.3 * R * np.sin(Theta) + y_pos
            
            # Get z height at this position
            # Find closest point on surface grid
            idx_x = np.abs(x - x_pos).argmin()
            idx_y = np.abs(y - y_pos).argmin()
            Z_top = Z_surface[idx_y, idx_x]
            
            Z_conduit = shallow_chamber_depth + (Z_top - shallow_chamber_depth) * (1 - R)
            
            # Only show some conduits based on alert level
            if alert_level == 'Normal' and angle % (np.pi/2) != 0:
                continue
            if alert_level == 'Advisory' and angle % (np.pi/4) != 0:
                continue
                
            fig.add_trace(go.Surface(
                x=X_conduit, y=Y_conduit, z=Z_conduit,
                colorscale=[[0, magma_color[0]], [1, magma_color[0]]],
                showscale=False,
                opacity=0.6 + 0.3 * deformation_rate  # More visible at higher alert levels
            ))
    
    elif volcano_type == 'cinder_cone':
        # Cinder cone: steep-sided, relatively small
        x = np.linspace(-5, 5, 30)
        y = np.linspace(-5, 5, 30)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        # Steep conical surface with crater
        Z_surface = 6 * np.exp(-0.3 * R**2) - 2 * np.exp(-2.0 * R**2)
        
        # Add deformation - cinder cones often show localized deformation
        deform = deformation_rate * np.exp(-1.0 * R**2) * 0.5
        Z_surface = Z_surface + deform
        
        # Add the surface
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z_surface,
            colorscale='Earth',
            showscale=False,
            opacity=0.9
        ))
        
        # Small, shallow magma reservoir
        chamber_depth = -1.0
        chamber_x = np.linspace(-1.5, 1.5, 20)
        chamber_y = np.linspace(-1.5, 1.5, 20)
        chamber_X, chamber_Y = np.meshgrid(chamber_x, chamber_y)
        chamber_R = np.sqrt(chamber_X**2 + chamber_Y**2)
        chamber_Z = chamber_depth - 0.8 * np.exp(-0.5 * chamber_R**2)
        
        # Magma reservoir
        fig.add_trace(go.Surface(
            x=chamber_X, y=chamber_Y, z=chamber_Z,
            colorscale=[[0, magma_color[0]], [1, magma_color[1]]],
            showscale=False,
            opacity=0.8
        ))
        
        # Add conduit - cinder cones have a simple central conduit
        r = np.linspace(0, 1, 15)
        theta = np.linspace(0, 2*np.pi, 15)
        R, Theta = np.meshgrid(r, theta)
        X_conduit = 0.3 * R * np.cos(Theta)
        Y_conduit = 0.3 * R * np.sin(Theta)
        Z_top = Z_surface[15, 15]  # Summit
        Z_conduit = chamber_depth + (Z_top - chamber_depth) * (1 - R)
        
        fig.add_trace(go.Surface(
            x=X_conduit, y=Y_conduit, z=Z_conduit,
            colorscale=[[0, magma_color[0]], [1, magma_color[0]]],
            showscale=False,
            opacity=0.9
        ))
    
    elif volcano_type == 'lava_dome':
        # Lava dome: steep-sided, viscous lava
        x = np.linspace(-5, 5, 30)
        y = np.linspace(-5, 5, 30)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        
        # Bulbous dome surface
        Z_surface = 4 * np.exp(-0.25 * R**2)
        
        # Add fracturing patterns to surface
        theta = np.arctan2(Y, X)
        fractures = 0.3 * np.sin(theta * 6)**2 * np.exp(-0.5 * R**2)
        Z_surface = Z_surface - fractures * deformation_rate
        
        # Add the surface
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z_surface,
            colorscale='Earth',
            showscale=False,
            opacity=0.9
        ))
        
        # Lava domes have complex magmatic plumbing featuring multiple interacting reservoirs
        
        # Main magma chamber - small shallow reservoir with high viscosity
        main_chamber_depth = -2.0
        chamber_x = np.linspace(-2, 2, 20)
        chamber_y = np.linspace(-2, 2, 20)
        chamber_X, chamber_Y = np.meshgrid(chamber_x, chamber_y)
        chamber_R = np.sqrt(chamber_X**2 + chamber_Y**2)
        chamber_Z = main_chamber_depth - 1.0 * np.exp(-0.3 * chamber_R**2)
        
        # Main shallow magma chamber
        fig.add_trace(go.Surface(
            x=chamber_X, y=chamber_Y, z=chamber_Z,
            colorscale=[[0, magma_color[0]], [1, magma_color[1]]],
            showscale=False,
            opacity=0.8,
            name="Main Magma Chamber"
        ))
        
        # Secondary magma pockets - lava domes often have multiple storage zones
        # Create several smaller chambers at different depths and positions
        for i, position in enumerate([(-1.5, 1.0, -2.8), (1.5, -1.0, -3.5), (0.5, 2.0, -4.2)]):
            # Only show deeper chambers for higher alert levels
            if alert_level in ['Normal', 'Advisory'] and i > 0:
                continue
                
            sec_x, sec_y, sec_z = position
            sec_chamber_x = np.linspace(-0.8, 0.8, 15)
            sec_chamber_y = np.linspace(-0.8, 0.8, 15)
            sec_chamber_X, sec_chamber_Y = np.meshgrid(sec_chamber_x, sec_chamber_y)
            sec_chamber_X = sec_chamber_X + sec_x
            sec_chamber_Y = sec_chamber_Y + sec_y
            sec_chamber_R = np.sqrt((sec_chamber_X - sec_x)**2 + (sec_chamber_Y - sec_y)**2)
            sec_chamber_Z = sec_z - 0.6 * np.exp(-0.5 * sec_chamber_R**2)
            
            # Add secondary chamber
            fig.add_trace(go.Surface(
                x=sec_chamber_X, y=sec_chamber_Y, z=sec_chamber_Z,
                colorscale=[[0, 'rgba(255,30,30,0.6)'], [1, 'rgba(255,30,30,0.2)']],
                showscale=False,
                opacity=0.7,
                name=f"Secondary Magma Pocket {i+1}"
            ))
            
            # Add connection to main chamber
            connect_points = []
            for t in np.linspace(0, 1, 8):
                # Calculate connection path
                cx = sec_x * (1-t)
                cy = sec_y * (1-t)
                cz = sec_z + t * (main_chamber_depth - sec_z)
                
                connect_points.append((cx, cy, cz))
            
            # Plot connection
            connect_x = [p[0] for p in connect_points]
            connect_y = [p[1] for p in connect_points]
            connect_z = [p[2] for p in connect_points]
            
            fig.add_trace(go.Scatter3d(
                x=connect_x, y=connect_y, z=connect_z,
                mode='markers',
                marker=dict(
                    size=6,
                    color=magma_color[0],
                    opacity=0.7
                ),
                showlegend=False
            ))
        
        # Add thick conduit - lava domes have a fat conduit with viscous magma
        r = np.linspace(0, 1, 15)
        theta = np.linspace(0, 2*np.pi, 15)
        R, Theta = np.meshgrid(r, theta)
        X_conduit = 0.7 * R * np.cos(Theta)
        Y_conduit = 0.7 * R * np.sin(Theta)
        Z_top = Z_surface[15, 15]  # Summit
        Z_conduit = main_chamber_depth + (Z_top - main_chamber_depth) * (1 - R)
        
        fig.add_trace(go.Surface(
            x=X_conduit, y=Y_conduit, z=Z_conduit,
            colorscale=[[0, magma_color[0]], [1, magma_color[0]]],
            showscale=False,
            opacity=0.9
        ))
        
        # Add extrusion pulse for higher alert levels
        if alert_level in ['Watch', 'Warning']:
            # Create extrusion pulse in conduit
            pulse_z = Z_top * 0.6
            for r_val in np.linspace(0.1, 0.6, 5):
                pulse_theta = np.linspace(0, 2*np.pi, 20)
                pulse_x = r_val * np.cos(pulse_theta)
                pulse_y = r_val * np.sin(pulse_theta)
                
                fig.add_trace(go.Scatter3d(
                    x=pulse_x, y=pulse_y, z=[pulse_z] * len(pulse_x),
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=magma_color[0],
                        opacity=0.9
                    ),
                    showlegend=False
                ))
    
    # Update layout
    name_title = volcano_type.replace('_', ' ').title()
    
    fig.update_layout(
        title=f"3D Magma Chamber Visualization - {name_title} Volcano, {alert_level} Alert Level",
        scene=dict(
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8),
            xaxis_title="East-West Distance (km)",
            yaxis_title="North-South Distance (km)",
            zaxis_title="Elevation (km)",
            camera=dict(
                eye=dict(x=1.5, y=-1.5, z=0.7),
                up=dict(x=0, y=0, z=1)
            )
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        width=1200,
        height=900,
    )
    
    # Calculate magma chamber metrics
    chamber_metrics = {}
    
    # Calculate chamber size and magma volume based on volcano type
    if volcano_type == 'shield':
        # Shield volcano: broader, shallower chamber
        chamber_metrics['chamber_depth'] = 1.5  # km
        chamber_metrics['chamber_width'] = 8.0  # km
        chamber_metrics['chamber_height'] = 1.0  # km
        
        # Base magma volume calculation
        base_volume = 25.0  # km³
        # Adjust based on alert level
        volume_multipliers = {
            'Normal': 0.3,
            'Advisory': 0.6,
            'Watch': 0.8,
            'Warning': 1.0
        }
        volume_multiplier = volume_multipliers.get(alert_level, 0.3)
        chamber_metrics['magma_volume'] = base_volume * volume_multiplier
        
        # Lava accumulation rate varies by alert level
        accumulation_rates = {
            'Normal': 0.05,
            'Advisory': 0.2,
            'Watch': 0.5,
            'Warning': 1.2
        }
        chamber_metrics['accumulation_rate'] = accumulation_rates.get(alert_level, 0.05)  # km³/month
        
    elif volcano_type == 'stratovolcano':
        # Stratovolcano: deeper, more compact chamber
        chamber_metrics['chamber_depth'] = 5.0  # km
        chamber_metrics['chamber_width'] = 6.0  # km
        chamber_metrics['chamber_height'] = 1.5  # km
        
        # Base magma volume calculation
        base_volume = 15.0  # km³
        # Adjust based on alert level
        volume_multipliers = {
            'Normal': 0.25,
            'Advisory': 0.5,
            'Watch': 0.8,
            'Warning': 1.0
        }
        volume_multiplier = volume_multipliers.get(alert_level, 0.25)
        chamber_metrics['magma_volume'] = base_volume * volume_multiplier
        
        # Lava accumulation rate varies by alert level
        accumulation_rates = {
            'Normal': 0.03,
            'Advisory': 0.15,
            'Watch': 0.4,
            'Warning': 0.9
        }
        chamber_metrics['accumulation_rate'] = accumulation_rates.get(alert_level, 0.03)  # km³/month
        
        # Add secondary chamber volume for higher alert levels
        if alert_level in ['Watch', 'Warning']:
            sec_chamber_volume = 5.0 * volume_multiplier
            chamber_metrics['magma_volume'] += sec_chamber_volume
            chamber_metrics['secondary_chamber'] = True
        else:
            chamber_metrics['secondary_chamber'] = False
            
    elif volcano_type == 'caldera':
        # Caldera: very large, complex magma system
        chamber_metrics['chamber_depth'] = 3.0  # km
        chamber_metrics['chamber_width'] = 12.0  # km
        chamber_metrics['chamber_height'] = 2.0  # km
        
        # Base magma volume calculation
        base_volume = 75.0  # km³
        # Adjust based on alert level
        volume_multipliers = {
            'Normal': 0.4,
            'Advisory': 0.6,
            'Watch': 0.8,
            'Warning': 1.0
        }
        volume_multiplier = volume_multipliers.get(alert_level, 0.4)
        chamber_metrics['magma_volume'] = base_volume * volume_multiplier
        
        # Lava accumulation rate varies by alert level
        accumulation_rates = {
            'Normal': 0.1,
            'Advisory': 0.3,
            'Watch': 0.7,
            'Warning': 1.5
        }
        chamber_metrics['accumulation_rate'] = accumulation_rates.get(alert_level, 0.1)  # km³/month
        
        # Calculate number of active conduits
        if alert_level == 'Normal':
            chamber_metrics['active_conduits'] = 2
        elif alert_level == 'Advisory':
            chamber_metrics['active_conduits'] = 4
        else:
            chamber_metrics['active_conduits'] = 8
            
    elif volcano_type == 'cinder_cone':
        # Cinder cone: small, simple magma system
        chamber_metrics['chamber_depth'] = 1.0  # km
        chamber_metrics['chamber_width'] = 3.0  # km
        chamber_metrics['chamber_height'] = 0.8  # km
        
        # Base magma volume calculation
        base_volume = 3.0  # km³
        # Adjust based on alert level
        volume_multipliers = {
            'Normal': 0.2,
            'Advisory': 0.5,
            'Watch': 0.8,
            'Warning': 1.0
        }
        volume_multiplier = volume_multipliers.get(alert_level, 0.2)
        chamber_metrics['magma_volume'] = base_volume * volume_multiplier
        
        # Lava accumulation rate varies by alert level
        accumulation_rates = {
            'Normal': 0.01,
            'Advisory': 0.08,
            'Watch': 0.2,
            'Warning': 0.5
        }
        chamber_metrics['accumulation_rate'] = accumulation_rates.get(alert_level, 0.01)  # km³/month
        
    elif volcano_type == 'lava_dome':
        # Lava dome: small chamber but high viscosity
        chamber_metrics['chamber_depth'] = 2.0  # km
        chamber_metrics['chamber_width'] = 4.0  # km
        chamber_metrics['chamber_height'] = 1.0  # km
        
        # Base magma volume calculation
        base_volume = 5.0  # km³
        # Adjust based on alert level
        volume_multipliers = {
            'Normal': 0.3,
            'Advisory': 0.6,
            'Watch': 0.8,
            'Warning': 1.0
        }
        volume_multiplier = volume_multipliers.get(alert_level, 0.3)
        chamber_metrics['magma_volume'] = base_volume * volume_multiplier
        
        # Lava accumulation rate varies by alert level
        accumulation_rates = {
            'Normal': 0.02,
            'Advisory': 0.1,
            'Watch': 0.25,
            'Warning': 0.6
        }
        chamber_metrics['accumulation_rate'] = accumulation_rates.get(alert_level, 0.02)  # km³/month
        
        # Extrusion amount for higher alert levels
        if alert_level in ['Watch', 'Warning']:
            chamber_metrics['extrusion_volume'] = 0.5 * volume_multiplier  # km³
        else:
            chamber_metrics['extrusion_volume'] = 0.0  # km³
    
    # Default values for any other type
    else:
        chamber_metrics['chamber_depth'] = 3.0  # km
        chamber_metrics['chamber_width'] = 5.0  # km
        chamber_metrics['chamber_height'] = 1.0  # km
        chamber_metrics['magma_volume'] = 10.0 * deformation_rate  # km³
        chamber_metrics['accumulation_rate'] = 0.1 * deformation_rate  # km³/month
    
    # Add potential eruption metrics based on alert level
    if alert_level == 'Normal':
        chamber_metrics['eruption_probability'] = '< 5%'
        chamber_metrics['est_vei_range'] = 'N/A'
    elif alert_level == 'Advisory':
        chamber_metrics['eruption_probability'] = '5-25%'
        chamber_metrics['est_vei_range'] = '1-2'
    elif alert_level == 'Watch':
        chamber_metrics['eruption_probability'] = '25-50%'
        chamber_metrics['est_vei_range'] = '2-3'
    elif alert_level == 'Warning':
        chamber_metrics['eruption_probability'] = '> 50%'
        chamber_metrics['est_vei_range'] = '3-4+'
    
    # Update scene for better 3D visualization
    fig.update_layout(
        scene=dict(
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8),
            xaxis_title="East-West Distance (km)",
            yaxis_title="North-South Distance (km)",
            zaxis_title="Elevation (km)",
            camera=dict(
                eye=dict(x=1.5, y=-1.5, z=0.7),
                up=dict(x=0, y=0, z=1)
            )
        )
    )
    
    # Return both the figure and the calculated metrics
    return fig, chamber_metrics

def generate_animated_magma_flow(volcano_type: str, alert_level: str, frames: int = 60) -> Tuple[go.Figure, Dict[str, Any]]:
    """
    Generate an animated visualization of magma flow within the volcano's plumbing system
    and return metrics about the chamber size and magma volume
    
    Args:
        volcano_type (str): Type of volcano
        alert_level (str): Current alert level
        frames (int): Number of animation frames
        
    Returns:
        Tuple[go.Figure, Dict[str, Any]]: 
            - Animated figure of magma flow
            - Dictionary with chamber metrics (size, volume, accumulation rate)
    """
    # Get base 3D model and chamber metrics
    fig, chamber_metrics = generate_3d_magma_chamber(volcano_type, alert_level)
    
    # Animation frames will vary by volcano type
    animation_frames = []
    
    # Get type-specific parameters
    v_params = VOLCANO_TYPES.get(volcano_type, VOLCANO_TYPES['stratovolcano'])
    a_params = ALERT_LEVELS.get(alert_level, ALERT_LEVELS['Normal'])
    
    # Alert level parameters
    alert_colors = {
        'Normal': ['rgba(0,200,0,0.7)', 'rgba(0,200,0,0.2)'],
        'Advisory': ['rgba(255,200,0,0.7)', 'rgba(255,200,0,0.2)'],
        'Watch': ['rgba(255,120,0,0.7)', 'rgba(255,120,0,0.2)'],
        'Warning': ['rgba(255,0,0,0.7)', 'rgba(255,0,0,0.2)']
    }
    magma_color = alert_colors.get(alert_level, ['rgba(255,0,0,0.7)', 'rgba(255,0,0,0.2)'])
    
    # Animation parameters based on alert level
    flow_rates = {
        'Normal': 0.3,
        'Advisory': 0.5,
        'Watch': 0.8,
        'Warning': 1.0
    }
    flow_rate = flow_rates.get(alert_level, 0.3)
    
    # Different particle positions for each volcano type
    if volcano_type == 'shield':
        # Points for main chamber to surface
        chamber_depth = -1.5
        surface_height = 5
        conduit_points = []
        
        # Main vertical conduit
        for z in np.linspace(chamber_depth, surface_height, 10):
            r = 0.3 * (1 - (z - chamber_depth) / (surface_height - chamber_depth))
            theta = np.linspace(0, 2*np.pi, 8)
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                conduit_points.append((x, y, z))
        
        # Add lateral dikes for higher alert levels
        if alert_level in ['Watch', 'Warning']:
            # Create radial dikes
            for angle in [0, 2*np.pi/3, 4*np.pi/3]:
                for t in np.linspace(0, 1, 5):
                    dike_x = t * 6 * np.cos(angle)
                    dike_y = t * 6 * np.sin(angle)
                    dike_z = chamber_depth + t * 1.0  # Some rise
                    conduit_points.append((dike_x, dike_y, dike_z))
        
    elif volcano_type == 'stratovolcano':
        # Points for deeper chamber to surface
        chamber_depth = -5.0
        surface_height = 10
        conduit_points = []
        
        # Main vertical conduit
        for z in np.linspace(chamber_depth, surface_height, 15):
            r = 0.25 * (1 - (z - chamber_depth) / (surface_height - chamber_depth))
            theta = np.linspace(0, 2*np.pi, 6)
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                conduit_points.append((x, y, z))
        
        # Add secondary chamber for higher alert levels
        if alert_level in ['Watch', 'Warning']:
            # Points between main and secondary chambers
            sec_chamber_x = 2
            sec_chamber_y = 1
            sec_chamber_z = -3.0
            
            for t in np.linspace(0, 1, 5):
                x = t * sec_chamber_x
                y = t * sec_chamber_y
                z = chamber_depth + t * (sec_chamber_z - chamber_depth)
                conduit_points.append((x, y, z))
                
            # Points within secondary chamber
            for _ in range(6):
                x = sec_chamber_x + np.random.uniform(-1, 1)
                y = sec_chamber_y + np.random.uniform(-1, 1)
                z = sec_chamber_z + np.random.uniform(-0.5, 0.5)
                conduit_points.append((x, y, z))
    
    elif volcano_type == 'caldera':
        # Points for large magma reservoir and ring fractures
        chamber_depth = -3.0
        conduit_points = []
        
        # Points within main chamber
        for _ in range(20):
            r = np.random.uniform(0, 5)
            theta = np.random.uniform(0, 2*np.pi)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            z = chamber_depth + np.random.uniform(-1.5, 0)
            conduit_points.append((x, y, z))
        
        # Points along ring fractures
        ring_radius = 3.0
        ring_angles = np.linspace(0, 2*np.pi, 8)
        
        for angle in ring_angles:
            x_pos = ring_radius * np.cos(angle)
            y_pos = ring_radius * np.sin(angle)
            
            # Determine if this conduit is active based on alert level
            if alert_level == 'Normal' and angle % (np.pi/2) != 0:
                continue
            if alert_level == 'Advisory' and angle % (np.pi/4) != 0:
                continue
            
            # Get z height at this position (approximate)
            z_surface = 4 * np.exp(-0.05 * ring_radius**2) - 2 * np.exp(-0.5 * ring_radius**2)
            
            # Add points along conduit
            for z in np.linspace(chamber_depth, z_surface, 8):
                # Add slight randomness to position
                x = x_pos + np.random.uniform(-0.2, 0.2)
                y = y_pos + np.random.uniform(-0.2, 0.2)
                conduit_points.append((x, y, z))
    
    elif volcano_type == 'cinder_cone':
        # Points for small chamber and simple conduit
        chamber_depth = -1.0
        surface_height = 5
        conduit_points = []
        
        # Points within small chamber
        for _ in range(8):
            r = np.random.uniform(0, 1.2)
            theta = np.random.uniform(0, 2*np.pi)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            z = chamber_depth + np.random.uniform(-0.6, 0)
            conduit_points.append((x, y, z))
        
        # Points along central conduit
        for z in np.linspace(chamber_depth, surface_height, 10):
            r = 0.2 * (1 - (z - chamber_depth) / (surface_height - chamber_depth))
            theta = np.linspace(0, 2*np.pi, 4)
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                conduit_points.append((x, y, z))
    
    elif volcano_type == 'lava_dome':
        # Points for viscous magma in thick conduit
        chamber_depth = -2.0
        surface_height = 4
        conduit_points = []
        
        # Points within chamber
        for _ in range(10):
            r = np.random.uniform(0, 1.5)
            theta = np.random.uniform(0, 2*np.pi)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            z = chamber_depth + np.random.uniform(-0.8, 0)
            conduit_points.append((x, y, z))
        
        # Points along thick conduit
        for z in np.linspace(chamber_depth, surface_height, 12):
            r_max = 0.5 * (1 - (z - chamber_depth) / (surface_height - chamber_depth))
            theta = np.linspace(0, 2*np.pi, 6)
            for t in theta:
                x = r_max * np.cos(t)
                y = r_max * np.sin(t)
                conduit_points.append((x, y, z))
        
        # Add extrusion pulse for higher alert levels
        if alert_level in ['Watch', 'Warning']:
            # Add pulse points near the top
            for _ in range(8):
                r = np.random.uniform(0, 0.4)
                theta = np.random.uniform(0, 2*np.pi)
                x = r * np.cos(theta)
                y = r * np.sin(theta)
                z = surface_height * 0.6 + np.random.uniform(-0.2, 0.2)
                conduit_points.append((x, y, z))
    
    # Create animation frames with particles flowing through conduits
    all_particles = []
    
    # Create initial particles at random positions in the conduit system
    n_particles = 50  # Number of particles
    for i in range(n_particles):
        # Pick a random conduit point as starting position
        p_idx = np.random.randint(0, len(conduit_points))
        pos = conduit_points[p_idx]
        
        # Add random offset
        pos = (
            pos[0] + np.random.uniform(-0.1, 0.1),
            pos[1] + np.random.uniform(-0.1, 0.1),
            pos[2] + np.random.uniform(-0.1, 0.1)
        )
        
        # Assign a random velocity vector based on volcano type
        if volcano_type == 'shield':
            # More horizontal flow possible
            if np.random.random() < 0.3 and alert_level in ['Watch', 'Warning']:
                # Lateral flow
                angle = np.random.choice([0, 2*np.pi/3, 4*np.pi/3])
                vx = np.cos(angle) * flow_rate * np.random.uniform(0.01, 0.03)
                vy = np.sin(angle) * flow_rate * np.random.uniform(0.01, 0.03)
                vz = flow_rate * np.random.uniform(0.005, 0.01)
            else:
                # Vertical flow
                vx = 0
                vy = 0
                vz = flow_rate * np.random.uniform(0.02, 0.04)
        
        elif volcano_type == 'stratovolcano':
            if pos[0] > 0.5 and alert_level in ['Watch', 'Warning']:
                # Flow toward secondary chamber
                vx = flow_rate * np.random.uniform(0.01, 0.03)
                vy = flow_rate * np.random.uniform(0.005, 0.015)
                vz = flow_rate * np.random.uniform(0.015, 0.025)
            else:
                # Mainly vertical flow
                vx = 0
                vy = 0
                vz = flow_rate * np.random.uniform(0.02, 0.04)
        
        elif volcano_type == 'caldera':
            # More chaotic flow in caldera systems
            if np.random.random() < 0.5:
                # Flow toward random ring fracture
                angle = np.random.choice(ring_angles)
                target_x = ring_radius * np.cos(angle)
                target_y = ring_radius * np.sin(angle)
                direction = np.arctan2(target_y - pos[1], target_x - pos[0])
                vx = np.cos(direction) * flow_rate * np.random.uniform(0.01, 0.03)
                vy = np.sin(direction) * flow_rate * np.random.uniform(0.01, 0.03)
                vz = flow_rate * np.random.uniform(0.01, 0.03)
            else:
                # General upward flow
                vx = flow_rate * np.random.uniform(-0.01, 0.01)
                vy = flow_rate * np.random.uniform(-0.01, 0.01)
                vz = flow_rate * np.random.uniform(0.015, 0.035)
        
        elif volcano_type == 'cinder_cone':
            # Straightforward vertical flow in simple system
            vx = flow_rate * np.random.uniform(-0.005, 0.005)
            vy = flow_rate * np.random.uniform(-0.005, 0.005)
            vz = flow_rate * np.random.uniform(0.02, 0.05)  # Faster in small systems
        
        elif volcano_type == 'lava_dome':
            # Slow, viscous flow
            vx = flow_rate * np.random.uniform(-0.005, 0.005)
            vy = flow_rate * np.random.uniform(-0.005, 0.005)
            vz = flow_rate * np.random.uniform(0.005, 0.02)  # Slower due to viscosity
        
        else:
            # Default flow
            vx = 0
            vy = 0
            vz = flow_rate * np.random.uniform(0.02, 0.04)
        
        # Add to particle list
        all_particles.append({
            'pos': list(pos),
            'vel': [vx, vy, vz],
            'size': np.random.uniform(5, 10)
        })
    
    # Create animation frames
    for frame_idx in range(frames):
        # Create frame data
        particle_x = []
        particle_y = []
        particle_z = []
        particle_size = []
        
        # Update each particle
        for particle in all_particles:
            pos = particle['pos']
            vel = particle['vel']
            
            # Update position
            pos[0] += vel[0]
            pos[1] += vel[1]
            pos[2] += vel[2]
            
            # Reset particles that go too high or too far
            if pos[2] > surface_height + 1 or np.sqrt(pos[0]**2 + pos[1]**2) > 10:
                # Reset to random position in chamber
                if volcano_type == 'shield':
                    pos[0] = np.random.uniform(-3, 3)
                    pos[1] = np.random.uniform(-3, 3)
                    pos[2] = chamber_depth + np.random.uniform(-1, 0)
                elif volcano_type == 'stratovolcano':
                    if np.random.random() < 0.2 and alert_level in ['Watch', 'Warning']:
                        # Start in secondary chamber
                        pos[0] = 2 + np.random.uniform(-1, 1)
                        pos[1] = 1 + np.random.uniform(-1, 1)
                        pos[2] = -3.0 + np.random.uniform(-0.5, 0.5)
                    else:
                        # Start in main chamber
                        pos[0] = np.random.uniform(-2, 2)
                        pos[1] = np.random.uniform(-2, 2)
                        pos[2] = chamber_depth + np.random.uniform(-1, 0)
                elif volcano_type == 'caldera':
                    # Large magma reservoir
                    pos[0] = np.random.uniform(-4, 4)
                    pos[1] = np.random.uniform(-4, 4)
                    pos[2] = chamber_depth + np.random.uniform(-1, 0)
                elif volcano_type == 'cinder_cone':
                    # Small chamber
                    pos[0] = np.random.uniform(-1, 1)
                    pos[1] = np.random.uniform(-1, 1)
                    pos[2] = chamber_depth + np.random.uniform(-0.5, 0)
                elif volcano_type == 'lava_dome':
                    # Reset to chamber
                    pos[0] = np.random.uniform(-1.5, 1.5)
                    pos[1] = np.random.uniform(-1.5, 1.5)
                    pos[2] = chamber_depth + np.random.uniform(-0.8, 0)
            
            # Collect particle data
            particle_x.append(pos[0])
            particle_y.append(pos[1])
            particle_z.append(pos[2])
            particle_size.append(particle['size'])
        
        # Create frame
        frame = go.Frame(
            data=[
                # Keep all original data from figure
                # (all surfaces remain the same)
                *fig.data,
                # Add moving particles
                go.Scatter3d(
                    x=particle_x,
                    y=particle_y,
                    z=particle_z,
                    mode='markers',
                    marker=dict(
                        size=particle_size,
                        color=magma_color[0],
                        opacity=0.9
                    ),
                    showlegend=False
                )
            ]
        )
        
        animation_frames.append(frame)
    
    # Add frames to figure
    fig.frames = animation_frames
    
    # Add animation controls
    fig.update_layout(
        width=1200,
        height=900,
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': 'Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 50, 'redraw': True},
                        'fromcurrent': True,
                        'transition': {'duration': 0}
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
    
    return fig, chamber_metrics