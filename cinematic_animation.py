"""
Cinematic volcano eruption animation utilities.

This module provides functions to create movie-like animated visualizations
of volcanic eruptions, showing the complete process from magma buildup to eruption.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
import math

from utils.animation_utils import determine_volcano_type, VOLCANO_TYPES, ALERT_LEVELS

def validate_rgb(r: int, g: int, b: int) -> Tuple[int, int, int]:
    """
    Ensure RGB values are within 0-255 range
    
    Args:
        r (int): Red value
        g (int): Green value
        b (int): Blue value
    
    Returns:
        Tuple[int, int, int]: Validated RGB values
    """
    return max(0, min(r, 255)), max(0, min(g, 255)), max(0, min(b, 255))

def ensure_valid_color(color: Any) -> str:
    """
    Ensures that a color value is in a valid format for Plotly.
    
    Args:
        color: Color value as string ('rgb(r,g,b)' or 'rgba(r,g,b,a)') or tuple/list of RGB/RGBA values
        
    Returns:
        str: Validated color string in 'rgb(r,g,b)' or 'rgba(r,g,b,a)' format
    """
    import re
    
    # If already a valid RGB string, check and validate the values
    if isinstance(color, str) and color.startswith('rgb(') and color.endswith(')'):
        try:
            # Extract the RGB values
            rgb_values = re.findall(r'\d+', color)
            if len(rgb_values) == 3:
                r, g, b = map(int, rgb_values)
                r, g, b = validate_rgb(r, g, b)
                return f'rgb({r}, {g}, {b})'
        except Exception:
            pass
    
    # If already a valid RGBA string, check and validate the values
    elif isinstance(color, str) and color.startswith('rgba(') and color.endswith(')'):
        try:
            # Extract all values from the string
            values = re.findall(r'[\d\.]+', color)
            if len(values) == 4:
                # RGB values should be integers
                r, g, b = map(int, values[:3])
                # Alpha should be a float between 0 and 1
                a = float(values[3])
                
                # Validate RGB
                r, g, b = validate_rgb(r, g, b)
                # Validate alpha
                a = max(0.0, min(1.0, a))
                
                return f'rgba({r}, {g}, {b}, {a})'
        except Exception:
            pass
    
    # If a tuple or list of RGB values
    elif isinstance(color, (tuple, list)):
        try:
            if len(color) == 3:
                # RGB values
                r, g, b = map(int, color)
                r, g, b = validate_rgb(r, g, b)
                return f'rgb({r}, {g}, {b})'
            elif len(color) == 4:
                # RGBA values
                r, g, b = map(int, color[:3])
                a = float(color[3])
                r, g, b = validate_rgb(r, g, b)
                a = max(0.0, min(1.0, a))
                return f'rgba({r}, {g}, {b}, {a})'
        except Exception:
            pass
    
    # Default to a safe color if validation fails
    return 'rgb(128, 128, 128)'  # Default gray

def generate_cinematic_eruption(volcano_data: Dict, frames: int = 120) -> Dict:
    """
    Generate a cinematic animation of a volcanic eruption from magma buildup to ash cloud.
    
    Args:
        volcano_data (Dict): Volcano data dictionary
        frames (int): Number of frames in the animation
        
    Returns:
        Dict: Dictionary with animation data and metadata
    """
    # Determine volcano type
    volcano_type = determine_volcano_type(volcano_data)
    volcano_name = volcano_data.get('name', 'Volcano')
    
    # Create figure with appropriate aspect ratio for cinematic view
    fig = go.Figure()
    
    # Set up the scene with appropriate dimensions based on volcano type
    # Each volcano type needs different viewing parameters to show their proportions
    if volcano_type == 'shield':
        # Shield volcanoes are very wide with gentle slopes
        x_range = [-20, 20]  # Wide viewing range
        y_range = [-20, 20]  
        z_range = [-8, 15]   # Less height needed
    elif volcano_type == 'stratovolcano':
        # Stratovolcanoes are tall with narrower base
        x_range = [-15, 15]
        y_range = [-15, 15]
        z_range = [-10, 25]  # Need more height for tall eruption columns
    elif volcano_type == 'caldera':
        # Calderas are wide with a depression
        x_range = [-20, 20]
        y_range = [-20, 20]
        z_range = [-8, 25]   # Need height for large eruption columns
    elif volcano_type == 'cinder_cone':
        # Cinder cones are small
        x_range = [-8, 8]
        y_range = [-8, 8]
        z_range = [-5, 15]   # Less height overall
    elif volcano_type == 'lava_dome':
        # Lava domes are small but can have tall eruption columns
        x_range = [-8, 8]
        y_range = [-8, 8]
        z_range = [-8, 15]
    else:
        # Default dimensions
        x_range = [-15, 15]
        y_range = [-15, 15]
        z_range = [-8, 20]  # Extra height for ash clouds and eruption columns
    
    # Generate ground surface based on volcano type
    resolution = 50
    x = np.linspace(x_range[0], x_range[1], resolution)
    y = np.linspace(y_range[0], y_range[1], resolution)
    X, Y = np.meshgrid(x, y)
    
    # Calculate distance from center
    R = np.sqrt(X**2 + Y**2)
    
    # Base surface shape depends on volcano type with more realistic proportions
    if volcano_type == 'shield':
        # Shield volcanoes: Very wide base with gently sloping sides (like Hawaiian volcanoes)
        # Typically 1:20 height to width ratio
        base_width = 20.0  # Wide base
        height = 3.0       # Moderate height
        Z_surface = height * np.exp(-0.02 * (R**2 / base_width))
    elif volcano_type == 'stratovolcano':
        # Stratovolcanoes: Steep conical shape with height to width ratio of 1:3 (like Mt. Fuji)
        base_width = 8.0   # Medium-wide base
        height = 7.0       # Tall
        # More realistic steep sides with slightly concave shape
        Z_surface = height * np.exp(-0.2 * (R**2 / base_width))
    elif volcano_type == 'caldera':
        # Calderas: Wide with a depression in the middle (like Yellowstone)
        base_width = 15.0  # Wide base
        rim_height = 2.5   # Moderate rim height
        depression_width = 6.0  # Size of the central depression
        # Rim with central depression
        Z_surface = rim_height * np.exp(-0.05 * (R**2 / base_width)) - 2.0 * np.exp(-1.0 * (R**2 / depression_width))
    elif volcano_type == 'cinder_cone':
        # Cinder cones: Small, steep sides, height to width ratio around 1:4 (like Paricutin)
        base_width = 4.0   # Narrow base
        height = 3.0       # Small height
        # Steep sides with very small summit crater
        Z_surface = height * np.exp(-0.5 * (R**2 / base_width)) - 0.5 * np.exp(-10.0 * R**2)
    elif volcano_type == 'lava_dome':
        # Lava domes: Small, bulbous, steep-sided (like Mount St. Helens dome)
        base_width = 3.0   # Very narrow base
        height = 2.5       # Small height
        # Bulbous shape with steep sides
        Z_surface = height * (np.exp(-0.8 * (R**2 / base_width)) + 0.3 * np.exp(-4.0 * R**2))
    else:
        # Default - generic volcano shape
        Z_surface = 5 * np.exp(-0.1 * R**2)
    
    # Generate comprehensive volcanic plumbing system with realistic dimensions
    # Based on research from "Volcanic and igneous plumbing systems"
    
    # Initialize default values for all parameters to avoid any unbound variables
    # Magma chamber parameters
    chamber_depth = -5  
    chamber_width = 6   
    chamber_height = 2  
    has_deep_reservoir = False
    deep_reservoir_depth = -10
    deep_reservoir_width = 8
    deep_reservoir_height = 3
    has_shallow_chamber = False
    shallow_chamber_depth = -2
    shallow_chamber_width = 4
    shallow_chamber_height = 1
    conduit_complexity = "simple"
    
    # Default volcano parameters for all volcano types
    # These will be used if not specifically set for a volcano type above
    height = 5.0
    base_width = 10.0
    rim_height = 3.0
    depression_width = 5.0
    
    # Then set specific values based on volcano type
    if volcano_type == 'stratovolcano':
        # Stratovolcano plumbing systems typically have:
        # 1. Deep crustal reservoir (magma generation zone)
        # 2. Mid-crustal storage zone (main magma chamber)
        # 3. Shallow holding area (subsidiary chamber)
        # 4. Complex conduit system
        
        # Main magma chamber (mid-crustal)
        chamber_depth = -8  # Deep magma chamber
        chamber_width = 7   # Wide chamber but not as wide as shield volcanoes
        chamber_height = 3  # Tall chamber for rising magma bodies
        
        # Secondary features
        has_deep_reservoir = True
        deep_reservoir_depth = -15
        deep_reservoir_width = 12
        deep_reservoir_height = 4
        
        has_shallow_chamber = True
        shallow_chamber_depth = -3
        shallow_chamber_width = 3
        shallow_chamber_height = 1
        
        conduit_complexity = "complex"  # Can be "simple", "complex", or "network"
        
    elif volcano_type == 'shield':
        # Shield volcano plumbing systems typically have:
        # 1. Deeper primary magma reservoir
        # 2. Shallow, laterally extensive sill-like chamber
        # 3. Rift zones (lateral magma movement)
        
        # Main shallow, sill-like chamber
        chamber_depth = -4  # Shallow magma chamber for shield volcanoes
        chamber_width = 15  # Very wide, horizontally extensive chamber
        chamber_height = 2  # Relatively flat chamber (high width to height ratio)
        
        # Secondary features
        has_deep_reservoir = True
        deep_reservoir_depth = -12
        deep_reservoir_width = 10
        deep_reservoir_height = 3
        
        has_shallow_chamber = False  # Shield volcanoes often lack distinct shallow chambers
        shallow_chamber_depth = -2  # Initialize even if not used
        shallow_chamber_width = 3
        shallow_chamber_height = 1
        
        conduit_complexity = "network"  # Shield volcanoes often have complex rift zone systems
        
    elif volcano_type == 'caldera':
        # Caldera systems have:
        # 1. Large, shallow magma chambers
        # 2. Often multiple interconnected chambers
        # 3. Ring fracture systems
        
        # Main large, shallow chamber
        chamber_depth = -5  # Moderate depth for calderas
        chamber_width = 14  # Very wide chamber system
        chamber_height = 4  # Substantial vertical extent
        
        # Secondary features
        has_deep_reservoir = True
        deep_reservoir_depth = -14
        deep_reservoir_width = 18
        deep_reservoir_height = 5
        
        has_shallow_chamber = True
        shallow_chamber_depth = -2
        shallow_chamber_width = 8
        shallow_chamber_height = 2
        
        conduit_complexity = "network"  # Ring fractures with multiple paths
        
    elif volcano_type == 'cinder_cone':
        # Cinder cones have:
        # 1. Small, shallow magma source
        # 2. Simple, direct conduit
        # 3. Often monogenetic (single eruption history)
        
        # Small, shallow chamber
        chamber_depth = -3  # Very shallow for cinder cones
        chamber_width = 2   # Small chamber for cinder cones
        chamber_height = 1  # Small vertical extent
        
        # Secondary features
        has_deep_reservoir = False  # Cinder cones often lack deep reservoirs
        deep_reservoir_depth = -6   # Initialize even if not used
        deep_reservoir_width = 3
        deep_reservoir_height = 1
        
        has_shallow_chamber = False  # Single simple chamber is sufficient
        shallow_chamber_depth = -1.5  # Initialize even if not used
        shallow_chamber_width = 1
        shallow_chamber_height = 0.5
        
        conduit_complexity = "simple"  # Direct path from chamber to surface
        
    elif volcano_type == 'lava_dome':
        # Lava dome plumbing systems have:
        # 1. Moderately deep, viscous magma source
        # 2. Often complex conduit system with multiple branches
        
        # Moderately deep chamber
        chamber_depth = -6  # Moderately deep for lava domes
        chamber_width = 4   # Medium width chamber
        chamber_height = 2  # Medium height
        
        # Secondary features
        has_deep_reservoir = True
        deep_reservoir_depth = -12
        deep_reservoir_width = 6
        deep_reservoir_height = 3
        
        has_shallow_chamber = True
        shallow_chamber_depth = -2
        shallow_chamber_width = 2
        shallow_chamber_height = 1
        
        conduit_complexity = "complex"  # Often has multiple branches
    
    # Create a detailed magma chamber with more points for better visibility
    chamber_x = np.linspace(-chamber_width, chamber_width, 40)
    chamber_y = np.linspace(-chamber_width, chamber_width, 40)
    chamber_X, chamber_Y = np.meshgrid(chamber_x, chamber_y)
    chamber_R = np.sqrt(chamber_X**2 + chamber_Y**2)
    
    # Create the chamber shape with variable dimensions based on volcano type
    chamber_Z = chamber_depth - chamber_height * np.exp(-0.15 * (chamber_R**2) / (chamber_width*0.5))
    
    # Conduit parameters
    if volcano_type == 'shield':
        conduit_radius = 0.5
        vent_radius = 0.8
    elif volcano_type == 'stratovolcano':
        conduit_radius = 0.4
        vent_radius = 0.6
    elif volcano_type == 'caldera':
        conduit_radius = 0.6
        vent_radius = 1.0
    elif volcano_type == 'cinder_cone':
        conduit_radius = 0.3
        vent_radius = 0.5
    elif volcano_type == 'lava_dome':
        conduit_radius = 0.7
        vent_radius = 0.9
    else:
        conduit_radius = 0.5
        vent_radius = 0.7
    
    # Get the summit height
    summit_height = np.max(Z_surface)
    
    # Generate conduit system between magma chamber(s) and surface
    # The conduit complexity varies by volcano type and plumbing system
    conduit_coords = []
    
    # Main conduit from magma chamber to surface
    if conduit_complexity == "simple":
        # Simple, straight conduit
        theta = np.linspace(0, 2*np.pi, 15)
        conduit_heights = np.linspace(chamber_depth, summit_height, 25)
        
        for h in conduit_heights:
            # Conduit radius varies with height (wider near chamber, narrower near surface)
            radius_factor = (h - chamber_depth) / (summit_height - chamber_depth)
            r = conduit_radius * (1 - 0.5 * radius_factor)
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                conduit_coords.append((x, y, h))
    
    elif conduit_complexity == "complex":
        # Complex conduit with some bends and variations
        theta = np.linspace(0, 2*np.pi, 15)
        conduit_heights = np.linspace(chamber_depth, summit_height, 30)
        
        # Main conduit with slight sinusoidal offset
        for h_idx, h in enumerate(conduit_heights):
            # Add horizontal offset that varies with height
            height_fraction = h_idx / len(conduit_heights)
            offset_x = 0.6 * np.sin(height_fraction * 3 * np.pi) * (1 - height_fraction)
            offset_y = 0.3 * np.cos(height_fraction * 2 * np.pi) * (1 - height_fraction)
            
            # Conduit radius varies with height
            radius_factor = (h - chamber_depth) / (summit_height - chamber_depth)
            r = conduit_radius * (1 - 0.3 * radius_factor)
            
            for t in theta:
                x = offset_x + r * np.cos(t)
                y = offset_y + r * np.sin(t)
                conduit_coords.append((x, y, h))
        
        # Add a secondary branch if the volcano has a shallow chamber
        if has_shallow_chamber:
            # Get the midpoint of the main conduit
            mid_height_idx = len(conduit_heights) // 2
            mid_height = conduit_heights[mid_height_idx]
            
            # Create branch from midpoint to shallow chamber
            branch_heights = np.linspace(mid_height, shallow_chamber_depth, 10)
            
            for h_idx, h in enumerate(branch_heights):
                # Calculate horizontal offset for the branch
                branch_progress = h_idx / len(branch_heights)
                branch_x = 1.0 * branch_progress
                branch_y = 0.5 * branch_progress
                
                # Branch radius
                r = conduit_radius * 0.7
                
                for t in theta:
                    x = branch_x + r * np.cos(t)
                    y = branch_y + r * np.sin(t)
                    conduit_coords.append((x, y, h))
    
    elif conduit_complexity == "network":
        # Network of conduits with multiple branches (for shield volcanoes and calderas)
        theta = np.linspace(0, 2*np.pi, 12)
        conduit_heights = np.linspace(chamber_depth, summit_height, 25)
        
        # Main central conduit
        for h in conduit_heights:
            radius_factor = (h - chamber_depth) / (summit_height - chamber_depth)
            r = conduit_radius * (1 - 0.5 * radius_factor)
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                conduit_coords.append((x, y, h))
        
        # Add lateral rift zones/dikes (especially for shield volcanoes)
        if volcano_type == 'shield':
            # Create two main rift zones in opposite directions
            for direction in [0, np.pi]:
                # Heights for the rift zone
                rift_heights = np.linspace(chamber_depth + 1, chamber_depth + 2, 8)
                
                for h in rift_heights:
                    # Distance ranges along the rift
                    distances = np.linspace(1, chamber_width * 0.7, 10)
                    
                    for dist in distances:
                        # Create a tube-like structure along the rift
                        for t in np.linspace(0, 2*np.pi, 10):
                            small_r = conduit_radius * 0.4
                            x = dist * np.cos(direction) + small_r * np.cos(t)
                            y = dist * np.sin(direction) + small_r * np.sin(t)
                            conduit_coords.append((x, y, h))
        
        # For calderas, add ring dike structures
        elif volcano_type == 'caldera':
            # Create ring dike at a distance from center
            ring_radius = chamber_width * 0.4
            ring_heights = np.linspace(chamber_depth, chamber_depth + 3, 10)
            
            for h in ring_heights:
                for angle in np.linspace(0, 2*np.pi, 40):
                    x = ring_radius * np.cos(angle)
                    y = ring_radius * np.sin(angle)
                    
                    # Add some points to create thickness
                    for r_offset in np.linspace(-0.3, 0.3, 3):
                        adjusted_r = ring_radius + r_offset
                        x = adjusted_r * np.cos(angle)
                        y = adjusted_r * np.sin(angle)
                        conduit_coords.append((x, y, h))
    
    else:
        # Fallback to simple conduit
        theta = np.linspace(0, 2*np.pi, 15)
        conduit_heights = np.linspace(chamber_depth, summit_height, 25)
        
        for h in conduit_heights:
            radius_factor = (h - chamber_depth) / (summit_height - chamber_depth)
            r = conduit_radius * (1 - 0.5 * radius_factor)
            for t in theta:
                x = r * np.cos(t)
                y = r * np.sin(t)
                conduit_coords.append((x, y, h))
    
    # Define frames for the animation sequence
    # Each frame needs to show changes in the volcano state
    
    # We'll divide the animation into phases:
    # 1. Initial state (10% of frames)
    # 2. Magma buildup and deformation (30% of frames)
    # 3. Initial eruption (15% of frames)
    # 4. Main eruption phase (30% of frames)
    # 5. Waning activity (15% of frames)
    
    phase_frames = {
        'initial': int(frames * 0.1),
        'buildup': int(frames * 0.3),
        'initial_eruption': int(frames * 0.15),
        'main_eruption': int(frames * 0.3),
        'waning': frames - int(frames * 0.1) - int(frames * 0.3) - int(frames * 0.15) - int(frames * 0.3)
    }
    
    # Parameters that change during animation
    animation_data = {
        'frame': list(range(frames)),
        'phase': [],
        'deformation': [],
        'magma_level': [],
        'eruption_height': [],
        'lava_flow': [],
        'ash_density': []
    }
    
    # Deformation - how much the ground surface bulges
    deformation_max = 1.0 if volcano_type in ['stratovolcano', 'shield'] else 0.5
    
    # Magma level - how high the magma reaches in the conduit
    magma_level_max = summit_height if volcano_type != 'caldera' else summit_height - 1
    
    # Eruption height - how high the eruption column goes
    if volcano_type == 'stratovolcano':
        eruption_height_max = 15
    elif volcano_type == 'shield':
        eruption_height_max = 8
    elif volcano_type == 'caldera':
        eruption_height_max = 18
    elif volcano_type == 'cinder_cone':
        eruption_height_max = 12
    else:
        eruption_height_max = 10
    
    # Lava flow - extent of lava flows (for shield volcanoes this is higher)
    lava_flow_max = 8 if volcano_type == 'shield' else 4
    
    # Ash density - amount of ash produced (higher for explosive eruptions)
    if volcano_type in ['stratovolcano', 'caldera']:
        ash_density_max = 1.0
    elif volcano_type == 'cinder_cone':
        ash_density_max = 0.7
    elif volcano_type == 'lava_dome':
        ash_density_max = 0.5
    else:
        ash_density_max = 0.2  # Shield volcanoes produce less ash
    
    # Generate data for each frame
    current_frame = 0
    
    # Initial state phase
    for i in range(phase_frames['initial']):
        animation_data['phase'].append('initial')
        animation_data['deformation'].append(0)
        animation_data['magma_level'].append(chamber_depth * 0.8)  # Start with magma deep down
        animation_data['eruption_height'].append(0)
        animation_data['lava_flow'].append(0)
        animation_data['ash_density'].append(0)
        current_frame += 1
    
    # Buildup phase - increasing deformation and magma level
    for i in range(phase_frames['buildup']):
        progress = i / phase_frames['buildup']
        animation_data['phase'].append('buildup')
        animation_data['deformation'].append(progress * deformation_max * 0.8)  # 80% of max deformation
        animation_data['magma_level'].append(
            chamber_depth + progress * (summit_height * 0.9 - chamber_depth)
        )  # Magma rises toward surface
        animation_data['eruption_height'].append(0)
        animation_data['lava_flow'].append(0)
        animation_data['ash_density'].append(0)
        current_frame += 1
    
    # Initial eruption phase
    for i in range(phase_frames['initial_eruption']):
        progress = i / phase_frames['initial_eruption']
        animation_data['phase'].append('initial_eruption')
        
        # Deformation may decrease as pressure is released
        deform_factor = 0.8 - progress * 0.3
        animation_data['deformation'].append(deformation_max * deform_factor)
        
        # Magma reaches and slightly exceeds surface
        animation_data['magma_level'].append(summit_height + progress * 1.0)
        
        # Initial eruption column
        animation_data['eruption_height'].append(progress * eruption_height_max * 0.4)
        
        # Initial lava flows
        animation_data['lava_flow'].append(progress * lava_flow_max * 0.3)
        
        # Initial ash
        animation_data['ash_density'].append(progress * ash_density_max * 0.4)
        current_frame += 1
    
    # Main eruption phase
    for i in range(phase_frames['main_eruption']):
        progress = i / phase_frames['main_eruption']
        animation_data['phase'].append('main_eruption')
        
        # Deformation continues to decrease
        deform_factor = 0.5 - progress * 0.3
        animation_data['deformation'].append(max(0, deformation_max * deform_factor))
        
        # Magma level fluctuates slightly during eruption
        fluctuation = 0.5 * np.sin(progress * 6 * np.pi)
        animation_data['magma_level'].append(summit_height + 1.0 + fluctuation)
        
        # Eruption column reaches maximum then may fluctuate
        eruption_pattern = 0.7 + 0.3 * np.sin(progress * 4 * np.pi)
        animation_data['eruption_height'].append(eruption_height_max * eruption_pattern)
        
        # Lava flows increase steadily
        animation_data['lava_flow'].append(0.3 * lava_flow_max + progress * lava_flow_max * 0.7)
        
        # Ash density reaches peak then may fluctuate
        ash_pattern = 0.7 + 0.3 * np.sin(progress * 4 * np.pi)
        animation_data['ash_density'].append(ash_density_max * ash_pattern)
        current_frame += 1
    
    # Waning phase
    for i in range(phase_frames['waning']):
        progress = i / phase_frames['waning']
        animation_data['phase'].append('waning')
        
        # Deformation may increase slightly as magma drains back
        animation_data['deformation'].append(max(0, 0.2 * deformation_max * (1 - progress)))
        
        # Magma level drops
        animation_data['magma_level'].append(summit_height - progress * (summit_height - chamber_depth) * 0.5)
        
        # Eruption column decreases
        animation_data['eruption_height'].append(eruption_height_max * (1 - progress * 0.9))
        
        # Lava flows slow
        animation_data['lava_flow'].append(lava_flow_max * (1 - progress * 0.7))
        
        # Ash decreases
        animation_data['ash_density'].append(ash_density_max * (1 - progress * 0.8))
        current_frame += 1
    
    # Create the animation frames
    animation_frames = []
    
    # Colors for different elements - based on scientific references
    ground_color = ensure_valid_color('rgb(120, 108, 89)')  # Brown for ground
    
    # Magma colors vary with depth and composition
    deep_magma_color = ensure_valid_color('rgb(200, 0, 0)')     # Deeper red for deep magma
    magma_color = ensure_valid_color('rgb(255, 69, 0)')     # Orange-red for main chamber magma
    shallow_magma_color = ensure_valid_color('rgb(255, 100, 0)')  # Brighter orange for shallow magma
    
    # Lava colors vary by temperature and composition (Basaltic vs. Rhyolitic)
    # From Wikipedia: Lava temperatures can range from 800 °C (1,470 °F) to 1,200 °C (2,190 °F)
    if volcano_type == 'shield':
        # Shield volcanoes like Hawaii typically have basaltic lava (higher temperature)
        # Basaltic lavas are more fluid with temperatures of 1,100 to 1,200 °C
        lava_color = ensure_valid_color('rgb(255, 30, 0)')  # Brighter red-orange for hot basaltic lava
        lava_flow_type = "pahoehoe_to_aa"  # Pahoehoe (smooth) to A'a (rough) transition
    elif volcano_type in ['stratovolcano', 'caldera']:
        # Stratovolcanoes often have more viscous andesitic to dacitic lava
        # With temperatures of 800 to 1,000 °C
        lava_color = ensure_valid_color('rgb(220, 20, 0)')  # Darker red for cooler, more viscous lava
        lava_flow_type = "blocky"  # Blocky or A'a flows
    elif volcano_type == 'lava_dome':
        # Lava domes have extremely viscous rhyolitic or dacitic lava
        # With lower temperatures around 800 °C
        lava_color = ensure_valid_color('rgb(180, 10, 0)')  # Darker red for cooler, highly viscous lava
        lava_flow_type = "viscous_dome"  # Slow-moving, thick flows forming a dome
    else:  # cinder_cone or other
        # Cinder cones often have basaltic to andesitic lava
        lava_color = ensure_valid_color('rgb(230, 25, 0)')  # Intermediate red color
        lava_flow_type = "aa"  # A'a flows (rough, blocky surface)
    
    # Eruption column colors
    eruption_color = ensure_valid_color('rgba(255, 69, 0, 0.8)')  # Semi-transparent orange-red for eruption column
    
    # Ash colors - darker for more silicic compositions (stratovolcanoes)
    if volcano_type in ['stratovolcano', 'caldera']:
        ash_color = ensure_valid_color('rgba(80, 80, 80, 0.7)')  # Darker gray for silicic ash
    else:
        ash_color = ensure_valid_color('rgba(120, 120, 120, 0.7)')  # Lighter gray for basaltic ash
    
    for frame_idx in range(frames):
        # Get data for this frame
        phase = animation_data['phase'][frame_idx]
        deformation = animation_data['deformation'][frame_idx]
        magma_level = animation_data['magma_level'][frame_idx]
        eruption_height = animation_data['eruption_height'][frame_idx]
        lava_flow = animation_data['lava_flow'][frame_idx]
        ash_density = animation_data['ash_density'][frame_idx]
        
        # Create frame data
        frame_data = []
        
        # 1. Ground surface with deformation
        Z_deformed = Z_surface.copy()
        if deformation > 0:
            # Apply deformation centered on the volcano
            bulge = deformation * np.exp(-0.2 * R**2)
            Z_deformed += bulge
        
        frame_data.append(
            go.Surface(
                x=X, y=Y, z=Z_deformed,
                colorscale=[[0, ground_color], [1, ground_color]],
                showscale=False,
                opacity=1.0
            )
        )
        
        # 2. Deep magma reservoir (if present)
        if has_deep_reservoir:
            # Create deep reservoir - larger and deeper
            deep_res_x = np.linspace(-deep_reservoir_width, deep_reservoir_width, 40)
            deep_res_y = np.linspace(-deep_reservoir_width, deep_reservoir_width, 40)
            deep_res_X, deep_res_Y = np.meshgrid(deep_res_x, deep_res_y)
            deep_res_R = np.sqrt(deep_res_X**2 + deep_res_Y**2)
            
            # Calculate deep reservoir surface
            deep_res_Z = deep_reservoir_depth - deep_reservoir_height * np.exp(-0.15 * (deep_res_R**2) / (deep_reservoir_width*0.5))
            
            # Deep reservoir is shown more translucent
            frame_data.append(
                go.Surface(
                    x=deep_res_X, y=deep_res_Y, z=deep_res_Z,
                    colorscale=[[0, deep_magma_color], [1, deep_magma_color]],  # Deeper red for deep magma
                    showscale=False,
                    opacity=0.6  # More translucent
                )
            )
            
            # Add connection between deep reservoir and main chamber
            if phase != 'initial' or np.random.random() < 0.3:  # Show connections more prominently during active phases
                connection_x = []
                connection_y = []
                connection_z = []
                
                # Create connection points
                connection_points = 15
                for i in range(connection_points):
                    # Interpolate position between deep reservoir and main chamber
                    t = i / (connection_points - 1)
                    
                    # Random offset to make it look more natural
                    rand_offset_x = np.random.uniform(-0.5, 0.5)
                    rand_offset_y = np.random.uniform(-0.5, 0.5)
                    
                    # Position
                    x = rand_offset_x
                    y = rand_offset_y
                    z = deep_reservoir_depth * (1 - t) + chamber_depth * t
                    
                    connection_x.append(x)
                    connection_y.append(y)
                    connection_z.append(z)
                
                # Add the connection as a scatter3d
                frame_data.append(
                    go.Scatter3d(
                        x=connection_x, y=connection_y, z=connection_z,
                        mode='markers',
                        marker=dict(
                            size=8,
                            color=magma_color,
                            opacity=0.7
                        ),
                        showlegend=False
                    )
                )
        
        # 3. Main magma chamber (constant through animation)
        frame_data.append(
            go.Surface(
                x=chamber_X, y=chamber_Y, z=chamber_Z,
                colorscale=[[0, magma_color], [1, magma_color]],
                showscale=False,
                opacity=0.8
            )
        )
        
        # 4. Shallow subsidiary chamber (if present)
        if has_shallow_chamber:
            # Create shallow chamber - smaller and near surface
            shallow_x = np.linspace(-shallow_chamber_width, shallow_chamber_width, 30)
            shallow_y = np.linspace(-shallow_chamber_width, shallow_chamber_width, 30)
            shallow_X, shallow_Y = np.meshgrid(shallow_x, shallow_y)
            shallow_R = np.sqrt(shallow_X**2 + shallow_Y**2)
            
            # Calculate shallow chamber surface
            shallow_Z = shallow_chamber_depth - shallow_chamber_height * np.exp(-0.2 * (shallow_R**2) / (shallow_chamber_width*0.4))
            
            # Shallow chamber is brighter
            frame_data.append(
                go.Surface(
                    x=shallow_X, y=shallow_Y, z=shallow_Z,
                    colorscale=[[0, shallow_magma_color], [1, shallow_magma_color]],  # Brighter orange for shallow magma
                    showscale=False,
                    opacity=0.75
                )
            )
            
            # Add connection between main chamber and shallow chamber
            connection2_x = []
            connection2_y = []
            connection2_z = []
            
            # Create connection points
            connection_points = 10
            for i in range(connection_points):
                # Interpolate position
                t = i / (connection_points - 1)
                
                # Small random offset
                rand_offset_x = np.random.uniform(-0.3, 0.3)
                rand_offset_y = np.random.uniform(-0.3, 0.3)
                
                # Position
                x = rand_offset_x
                y = rand_offset_y
                z = chamber_depth * (1 - t) + shallow_chamber_depth * t
                
                connection2_x.append(x)
                connection2_y.append(y)
                connection2_z.append(z)
            
            # Add the connection as a scatter3d
            frame_data.append(
                go.Scatter3d(
                    x=connection2_x, y=connection2_y, z=connection2_z,
                    mode='markers',
                    marker=dict(
                        size=6,
                        color=magma_color,
                        opacity=0.8
                    ),
                    showlegend=False
                )
            )
        
        # 3. Magma in conduit up to current magma level
        # Filter conduit points up to current level
        visible_conduit = [c for c in conduit_coords if c[2] <= magma_level]
        if visible_conduit:
            conduit_x = [c[0] for c in visible_conduit]
            conduit_y = [c[1] for c in visible_conduit]
            conduit_z = [c[2] for c in visible_conduit]
            
            frame_data.append(
                go.Scatter3d(
                    x=conduit_x, y=conduit_y, z=conduit_z,
                    mode='markers',
                    marker=dict(
                        size=8,  # Increased conduit magma marker size
                        color=magma_color,
                        opacity=0.9
                    ),
                    showlegend=False
                )
            )
        
        # 4. Eruption column if present
        if eruption_height > 0:
            # Create eruption column shape (wider at top)
            column_points = []
            column_heights = np.linspace(summit_height, summit_height + eruption_height, 20)
            
            for h_idx, h in enumerate(column_heights):
                # Column gets wider as it goes up
                height_fraction = h_idx / len(column_heights)
                r = vent_radius * (1 + height_fraction * 2.5)
                
                # More particles near the top for the eruption cloud
                if height_fraction > 0.7:
                    n_points = 30  # More points near top
                else:
                    n_points = 15
                
                for _ in range(n_points):
                    angle = np.random.uniform(0, 2*np.pi)
                    # Add randomness to radius
                    rand_r = r * np.random.uniform(0.7, 1.0)
                    x = rand_r * np.cos(angle)
                    y = rand_r * np.sin(angle)
                    # Add randomness to height
                    rand_h = h + np.random.uniform(-0.5, 0.5)
                    column_points.append((x, y, rand_h))
            
            # Add points for ash cloud at the top with directional dispersal
            if ash_density > 0:
                cloud_height = summit_height + eruption_height
                cloud_radius = vent_radius * 3 * ash_density
                n_ash_points = int(150 * ash_density)  # More points for denser visualization
                
                # Create a prevailing wind direction for ash dispersal
                # Primarily eastward (positive x) with slight northern (negative y) component
                wind_direction_x = 0.8  # Positive x direction (east)
                wind_direction_y = -0.3  # Slight negative y (north)
                
                # Normalize the wind vector
                wind_mag = np.sqrt(wind_direction_x**2 + wind_direction_y**2)
                wind_direction_x /= wind_mag
                wind_direction_y /= wind_mag
                
                # Generate ash cloud with directional bias
                for _ in range(n_ash_points):
                    # Base position at eruption column top
                    base_x = 0
                    base_y = 0
                    base_z = cloud_height
                    
                    # Distance from the center, farther points for more ash spread
                    dist = np.random.exponential(scale=cloud_radius * 1.5)
                    
                    # Wind influence increases with distance
                    wind_influence = min(1.0, dist / (cloud_radius * 2))
                    
                    # Angle with wind bias (more points in wind direction)
                    angle_bias = np.random.triangular(0, np.pi, 2*np.pi)
                    if np.random.random() < 0.7:  # 70% of particles follow wind
                        # Calculate position with wind influence
                        dx = dist * (wind_direction_x * wind_influence + 
                                    np.cos(angle_bias) * (1 - wind_influence))
                        dy = dist * (wind_direction_y * wind_influence + 
                                    np.sin(angle_bias) * (1 - wind_influence))
                    else:
                        # Some random dispersion in other directions
                        dx = dist * np.cos(angle_bias)
                        dy = dist * np.sin(angle_bias)
                    
                    # Height decreases with distance from center (ash falling)
                    height_decay = np.random.uniform(0.1, 0.5) * dist / cloud_radius
                    dz = np.random.uniform(-2, 1) * ash_density - height_decay
                    
                    # Final position
                    x = base_x + dx
                    y = base_y + dy
                    z = base_z + dz
                    
                    column_points.append((x, y, z))
                
                # Add ash fallout beneath the cloud
                fallout_points = int(50 * ash_density)
                max_fallout_dist = cloud_radius * 4  # How far the ash falls
                
                for _ in range(fallout_points):
                    # Distance from center, following the wind direction
                    dist = np.random.uniform(cloud_radius * 0.5, max_fallout_dist)
                    
                    # Position biased in wind direction
                    angle_jitter = np.random.uniform(-0.5, 0.5)
                    wind_angle = np.arctan2(wind_direction_y, wind_direction_x)
                    angle = wind_angle + angle_jitter
                    
                    # Calculate position
                    x = dist * np.cos(angle)
                    y = dist * np.sin(angle)
                    
                    # Height decreases with distance (ash is falling)
                    height_factor = 1 - (dist / max_fallout_dist)
                    z_max = cloud_height * height_factor
                    z = np.random.uniform(0, z_max)
                    
                    column_points.append((x, y, z))
            
            # Add eruption column to frame
            if column_points:
                col_x = [p[0] for p in column_points]
                col_y = [p[1] for p in column_points]
                col_z = [p[2] for p in column_points]
                
                # Color mix between eruption color and ash color based on height
                colors = []
                for z in col_z:
                    if z < summit_height + eruption_height * 0.7:
                        colors.append(eruption_color)
                    else:
                        colors.append(ash_color)
                
                frame_data.append(
                    go.Scatter3d(
                        x=col_x, y=col_y, z=col_z,
                        mode='markers',
                        marker=dict(
                            size=12,  # Increased marker size for eruption column
                            color=colors,
                            opacity=0.8
                        ),
                        showlegend=False
                    )
                )
        
        # 5. Lava flows if present
        if lava_flow > 0:
            # Generate lava flow points based on volcano type and lava flow type
            flow_points = []
            
            # Number of flow directions and characteristics depend on volcano type and lava type
            if volcano_type == 'shield':
                # Shield volcanoes (e.g., Hawaii) have extensive, fluid basaltic flows
                # Often beginning as pahoehoe (smooth, ropy) and transitioning to a'a (rough, blocky)
                flow_directions = 8  # Many flow directions due to low viscosity
                max_flow_width = 0.8  # Wider flows
                flow_sinuosity = 0.1  # Fairly straight flows
                
                # Increase max distance for shield volcanoes which have longer flows
                flow_length = lava_flow * 1.5  
                
            elif volcano_type == 'caldera':
                # Caldera eruptions can produce both explosive products and effusive lava flows
                flow_directions = 6  # Multiple flows from ring fissures or rim
                max_flow_width = 0.6  # Moderate width flows
                flow_sinuosity = 0.15  # Moderate sinuosity
                flow_length = lava_flow * 1.2
                
            elif volcano_type == 'stratovolcano':
                # Stratovolcanoes (e.g., Mt. Fuji) have steeper sides and more viscous andesitic lava
                # Producing shorter, thicker flows that often follow channels/valleys
                flow_directions = 4  # Fewer, channelized flows
                max_flow_width = 0.5  # Narrower flows, confined to channels
                flow_sinuosity = 0.25  # More sinuous due to topography
                flow_length = lava_flow
                
            elif volcano_type == 'lava_dome':
                # Lava domes (e.g., Mount St. Helens dome) have extremely viscous lava
                # Often barely flowing, instead piling up at the vent
                flow_directions = 2  # Very limited flow directions
                max_flow_width = 0.9  # Very thick, bulbous flows
                flow_sinuosity = 0.05  # Minimal sinuosity due to high viscosity
                flow_length = lava_flow * 0.6  # Much shorter flows
                
            else:  # cinder_cone or other
                # Cinder cones often have a'a flows of moderate viscosity
                flow_directions = 3  # Limited flow directions
                max_flow_width = 0.4  # Moderate width
                flow_sinuosity = 0.2  # Moderate sinuosity
                flow_length = lava_flow * 0.8  # Moderately short flows
            
            # Create flows in different directions
            for direction in range(flow_directions):
                angle = direction * (2 * np.pi / flow_directions)
                
                # Apply an artificial "preferred" direction based on topography
                # In nature, flows follow the path of least resistance downslope
                if direction == 0:
                    # Make one direction the "preferred" flow path (longer/wider)
                    path_preference = 1.3
                elif direction == 1:
                    path_preference = 1.2
                else:
                    path_preference = np.random.uniform(0.7, 1.0)
                
                # Adjust flow length by preference factor
                adjusted_flow_length = flow_length * path_preference
                
                # Different flow pattern based on lava_flow_type
                if lava_flow_type == "pahoehoe_to_aa":
                    # Pahoehoe transitions to a'a with distance from vent
                    # Characteristics: Smooth near vent, rougher with distance
                    n_points = 20  # More points for detailed flows
                    
                    # Create the flow path with some meandering
                    # Pahoehoe flows often have smooth, curved edges
                    path_x = [0]  # Start at origin
                    path_y = [0]
                    
                    # Generate a meandering path
                    for i in range(1, n_points):
                        relative_dist = i / n_points
                        # More meandering in middle distances
                        meander = flow_sinuosity * np.sin(relative_dist * np.pi * 3) 
                        
                        # Calculate next point with some meandering
                        next_angle = angle + np.random.uniform(-0.1, 0.1) + meander
                        step_length = adjusted_flow_length / n_points
                        
                        # Add to path
                        path_x.append(path_x[-1] + step_length * np.cos(next_angle))
                        path_y.append(path_y[-1] + step_length * np.sin(next_angle))
                    
                    # Now create points along this path
                    for i in range(n_points):
                        # Calculate position along path
                        x = path_x[i]
                        y = path_y[i]
                        
                        # Calculate distance from origin for later use
                        r = np.sqrt(x**2 + y**2)
                        relative_dist = r / adjusted_flow_length
                        
                        # Pahoehoe is smoother and more uniform near vent,
                        # becoming rougher (a'a) with distance
                        # This affects the width variability and point distribution
                        if relative_dist < 0.3:  # Near vent - smooth pahoehoe
                            width_variability = 0.1
                            point_randomness = 0.1
                            width_scaling = max_flow_width * (0.8 + 0.4 * relative_dist)
                        elif relative_dist < 0.7:  # Transition zone
                            width_variability = 0.2 + 0.3 * (relative_dist - 0.3) / 0.4
                            point_randomness = 0.2 + 0.4 * (relative_dist - 0.3) / 0.4
                            width_scaling = max_flow_width * (0.9 + 0.2 * relative_dist)
                        else:  # Distal - a'a flow
                            width_variability = 0.5
                            point_randomness = 0.6
                            width_scaling = max_flow_width * (0.7 - 0.4 * (relative_dist - 0.7) / 0.3)
                        
                        # Find appropriate z-height based on volcano surface
                        if volcano_type == 'shield':
                            z = height * np.exp(-0.02 * (r**2 / base_width))
                        elif volcano_type == 'stratovolcano':
                            z = height * np.exp(-0.2 * (r**2 / base_width))
                        elif volcano_type == 'caldera':
                            z = rim_height * np.exp(-0.05 * (r**2 / base_width)) - 2.0 * np.exp(-1.0 * (r**2 / depression_width))
                        elif volcano_type == 'cinder_cone':
                            z = height * np.exp(-0.5 * (r**2 / base_width)) - 0.5 * np.exp(-10.0 * r**2)
                        elif volcano_type == 'lava_dome':
                            z = height * (np.exp(-0.8 * (r**2 / base_width)) + 0.3 * np.exp(-4.0 * r**2))
                        else:
                            z = 5 * np.exp(-0.1 * r**2)
                        
                        # Add small height offset for visibility
                        z += 0.1 + 0.2 * (1 - relative_dist)  # Thicker near vent
                        
                        # Multiple points across flow width to show flow morphology
                        width_points = 5 if relative_dist < 0.7 else 7  # More points for a'a (rougher texture)
                        
                        # Calculate flow direction for width
                        flow_angle = np.arctan2(path_y[i] - path_y[i-1] if i > 0 else path_y[i+1] - path_y[i], 
                                                path_x[i] - path_x[i-1] if i > 0 else path_x[i+1] - path_x[i])
                        perp_angle = flow_angle + np.pi/2
                        
                        for w in range(width_points):
                            # Calculate perpendicular offset with variability
                            width_factor = (w - (width_points-1)/2) / ((width_points-1)/2)
                            width_offset = width_scaling * width_factor * (1 + np.random.uniform(-width_variability, width_variability))
                            
                            # Apply width offset
                            x_offset = x + width_offset * np.cos(perp_angle)
                            y_offset = y + width_offset * np.sin(perp_angle)
                            
                            # Add some random height variation (greater for a'a)
                            z_offset = z + np.random.uniform(-0.1, 0.1) * point_randomness
                            
                            # Add point
                            flow_points.append((x_offset, y_offset, z_offset))
                
                elif lava_flow_type == "blocky" or lava_flow_type == "aa":
                    # A'a or blocky flows have rough, jagged surfaces
                    # Characteristics: Thicker, rough, and more channelized
                    n_points = 15
                    
                    # Path characteristics: More jagged and channelized
                    path_x = [0]
                    path_y = [0]
                    
                    # Generate a more structured, channelized path
                    channel_direction = angle + np.random.uniform(-0.15, 0.15)  # Initial direction
                    
                    for i in range(1, n_points):
                        relative_dist = i / n_points
                        
                        # More abrupt direction changes for blocky flows
                        if np.random.random() < 0.2:  # Occasional more significant direction change
                            channel_direction += np.random.uniform(-0.3, 0.3)
                        else:
                            channel_direction += np.random.uniform(-0.1, 0.1)
                        
                        step_length = adjusted_flow_length / n_points
                        
                        # Add to path
                        path_x.append(path_x[-1] + step_length * np.cos(channel_direction))
                        path_y.append(path_y[-1] + step_length * np.sin(channel_direction))
                    
                    # Create points along path
                    for i in range(n_points):
                        x = path_x[i]
                        y = path_y[i]
                        r = np.sqrt(x**2 + y**2)
                        relative_dist = r / adjusted_flow_length
                        
                        # Blocky/a'a flows maintain relatively consistent width but have variable height
                        width_scaling = max_flow_width * (1.0 - 0.3 * relative_dist)  # Slightly narrower with distance
                        
                        # Find appropriate z-height based on volcano surface
                        if volcano_type == 'shield':
                            z = height * np.exp(-0.02 * (r**2 / base_width))
                        elif volcano_type == 'stratovolcano':
                            z = height * np.exp(-0.2 * (r**2 / base_width))
                        elif volcano_type == 'caldera':
                            z = rim_height * np.exp(-0.05 * (r**2 / base_width)) - 2.0 * np.exp(-1.0 * (r**2 / depression_width))
                        elif volcano_type == 'cinder_cone':
                            z = height * np.exp(-0.5 * (r**2 / base_width)) - 0.5 * np.exp(-10.0 * r**2)
                        elif volcano_type == 'lava_dome':
                            z = height * (np.exp(-0.8 * (r**2 / base_width)) + 0.3 * np.exp(-4.0 * r**2))
                        else:
                            z = 5 * np.exp(-0.1 * r**2)
                        
                        # Add height offset for visibility - thicker and more variable for a'a/blocky flows
                        z += 0.2 + 0.3 * np.random.uniform(0, 1)
                        
                        # Calculate flow direction for width
                        flow_angle = np.arctan2(path_y[i] - path_y[i-1] if i > 0 else path_y[i+1] - path_y[i], 
                                                path_x[i] - path_x[i-1] if i > 0 else path_x[i+1] - path_x[i])
                        perp_angle = flow_angle + np.pi/2
                        
                        # More points for rougher texture
                        width_points = 6
                        
                        for w in range(width_points):
                            # Significant width variation for blocky/a'a texture
                            width_factor = (w - (width_points-1)/2) / ((width_points-1)/2)
                            width_offset = width_scaling * width_factor * (1 + np.random.uniform(-0.4, 0.4))
                            
                            # Apply width offset
                            x_offset = x + width_offset * np.cos(perp_angle)
                            y_offset = y + width_offset * np.sin(perp_angle)
                            
                            # Very irregular height for blocky texture
                            z_offset = z + np.random.uniform(-0.2, 0.4)
                            
                            # Add point
                            flow_points.append((x_offset, y_offset, z_offset))
                
                elif lava_flow_type == "viscous_dome":
                    # Viscous dome flows are very short, thick, and barely move from the vent
                    # Characteristics: Very thick, bulbous, limited extent
                    n_points = 10  # Fewer points needed due to limited extent
                    
                    # For viscous domes, flows are more radial bulges than channel-like
                    for i in range(n_points):
                        # Calculate position with limited range
                        relative_dist = (i+1) / n_points
                        dist = adjusted_flow_length * relative_dist * 0.6  # Limited flow length
                        
                        # Add some randomness to flow direction
                        angle_jitter = angle + np.random.uniform(-0.1, 0.1)
                        
                        # Calculate position
                        x = dist * np.cos(angle_jitter)
                        y = dist * np.sin(angle_jitter)
                        r = np.sqrt(x**2 + y**2)
                        
                        # Find appropriate z-height
                        if volcano_type == 'lava_dome':
                            z = height * (np.exp(-0.8 * (r**2 / base_width)) + 0.3 * np.exp(-4.0 * r**2))
                        else:
                            z = 5 * np.exp(-0.25 * r**2)
                        
                        # Significant height offset for thick dome flows
                        # Decreasing with distance from vent
                        z += 0.5 * (1 - relative_dist)
                        
                        # Multiple points across to create bulbous appearance
                        width_points = 6
                        width_scaling = max_flow_width * (1.1 - 0.5 * relative_dist)
                        
                        for w in range(width_points):
                            # Significant width variation for bulbous texture
                            width_factor = (w - (width_points-1)/2) / ((width_points-1)/2)
                            width_offset = width_scaling * width_factor * (1 + np.random.uniform(-0.3, 0.3))
                            
                            # Apply width offset
                            perp_angle = angle + np.pi/2
                            x_offset = x + width_offset * np.cos(perp_angle)
                            y_offset = y + width_offset * np.sin(perp_angle)
                            
                            # Bulbous height variation
                            bulb_factor = 1 - 4 * (width_factor * width_factor)  # More height in center
                            z_offset = z + 0.3 * bulb_factor
                            
                            # Add point 
                            flow_points.append((x_offset, y_offset, z_offset))
                
                else:
                    # Generic flow type (fallback)
                    n_points = 15
                    for i in range(n_points):
                        # Distance from center
                        dist = adjusted_flow_length * ((i+1) / n_points)
                        
                        # Add some randomness to flow path
                        angle_jitter = angle + np.random.uniform(-0.2, 0.2)
                        dist_jitter = dist * np.random.uniform(0.8, 1.2)
                        
                        # Calculate position
                        x = dist_jitter * np.cos(angle_jitter)
                        y = dist_jitter * np.sin(angle_jitter)
                        r = np.sqrt(x**2 + y**2)
                        
                        # Find appropriate z-height based on volcano shape function
                        if volcano_type == 'shield':
                            z = height * np.exp(-0.02 * (r**2 / base_width))
                        elif volcano_type == 'stratovolcano':
                            z = height * np.exp(-0.2 * (r**2 / base_width))
                        elif volcano_type == 'caldera':
                            z = rim_height * np.exp(-0.05 * (r**2 / base_width)) - 2.0 * np.exp(-1.0 * (r**2 / depression_width))
                        elif volcano_type == 'cinder_cone':
                            z = height * np.exp(-0.5 * (r**2 / base_width)) - 0.5 * np.exp(-10.0 * r**2)
                        elif volcano_type == 'lava_dome':
                            z = height * (np.exp(-0.8 * (r**2 / base_width)) + 0.3 * np.exp(-4.0 * r**2))
                        else:
                            z = 5 * np.exp(-0.1 * r**2)
                        
                        # Add small offset for visibility
                        z += 0.1
                        
                        # Multiple points across flow width
                        width_points = 3
                        for w in range(width_points):
                            # Calculate perpendicular offset
                            width_factor = (w - (width_points-1)/2) / ((width_points-1)/2)
                            perp_angle = angle + np.pi/2
                            width_offset = 0.3 * width_factor
                            
                            # Apply width offset
                            x_offset = x + width_offset * np.cos(perp_angle)
                            y_offset = y + width_offset * np.sin(perp_angle)
                            
                            # Add point
                            flow_points.append((x_offset, y_offset, z))
            
            # Add lava flow to frame
            if flow_points:
                flow_x = [p[0] for p in flow_points]
                flow_y = [p[1] for p in flow_points]
                flow_z = [p[2] for p in flow_points]
                
                # For each point, calculate distance from center to create color gradient
                # Lava cools and darkens with distance
                flow_colors = []
                for i in range(len(flow_x)):
                    dist = np.sqrt(flow_x[i]**2 + flow_y[i]**2) / flow_length
                    
                    # Parse the RGB components from the lava color
                    base_color = lava_color.replace('rgb(', '').replace(')', '').split(',')
                    r = int(base_color[0].strip())
                    g = int(base_color[1].strip())
                    b = int(base_color[2].strip())
                    
                    # Darken with distance (cooling lava)
                    cooling_factor = max(0.2, 1.0 - 0.5 * dist)  # Ensure minimum brightness
                    r_cooled = max(0, min(255, int(r * cooling_factor)))  # Clamp between 0-255
                    g_cooled = max(0, min(255, int(g * cooling_factor)))  # Clamp between 0-255
                    b_cooled = max(0, min(255, int(b * cooling_factor)))  # Clamp between 0-255
                    
                    flow_colors.append(f'rgb({r_cooled}, {g_cooled}, {b_cooled})')
                
                frame_data.append(
                    go.Scatter3d(
                        x=flow_x, y=flow_y, z=flow_z,
                        mode='markers',
                        marker=dict(
                            size=10,  # Increased marker size
                            color=flow_colors,
                            opacity=0.9
                        ),
                        showlegend=False
                    )
                )
        
        # Create the animation frame
        animation_frames.append(
            go.Frame(
                data=frame_data,
                name=f"frame{frame_idx}"
            )
        )
    
    # Add frames to figure
    fig.frames = animation_frames
    
    # Set initial data (first frame)
    fig.add_traces(animation_frames[0].data)
    
    # Add camera position for cinematic view
    # Different view angles for different volcano types
    if volcano_type == 'shield':
        camera = dict(
            eye=dict(x=12, y=10, z=15),
            center=dict(x=0, y=0, z=0)
        )
    elif volcano_type == 'stratovolcano':
        camera = dict(
            eye=dict(x=14, y=12, z=12),
            center=dict(x=0, y=0, z=5)
        )
    elif volcano_type == 'caldera':
        camera = dict(
            eye=dict(x=10, y=-10, z=15),
            center=dict(x=0, y=0, z=0)
        )
    else:
        camera = dict(
            eye=dict(x=12, y=12, z=12),
            center=dict(x=0, y=0, z=2)
        )
    
    # Update layout
    # Calculate appropriate aspect ratios based on volcano type
    if volcano_type == 'shield':
        # Shield volcanoes are very wide with gentle slopes
        # Need to exaggerate vertical scale slightly for better visualization
        aspect_ratio = dict(x=1, y=1, z=0.8)
    elif volcano_type == 'stratovolcano':
        # Stratovolcanoes are tall with steeper sides
        aspect_ratio = dict(x=1, y=1, z=1.5)
    elif volcano_type == 'caldera':
        # Calderas are wide with a depression
        aspect_ratio = dict(x=1, y=1, z=1.0)
    elif volcano_type == 'cinder_cone':
        # Cinder cones are steep but small
        aspect_ratio = dict(x=1, y=1, z=1.2)
    elif volcano_type == 'lava_dome':
        # Lava domes are small but tall
        aspect_ratio = dict(x=1, y=1, z=1.4)
    else:
        # Default aspect ratio
        aspect_ratio = dict(x=1, y=1, z=1.2)
    
    fig.update_layout(
        title=f"{volcano_name} ({volcano_type.replace('_', ' ').title()}) Eruption Animation",
        autosize=True,
        width=1200,  # Increased width
        height=900,  # Increased height
        scene=dict(
            xaxis=dict(range=x_range, autorange=False),
            yaxis=dict(range=y_range, autorange=False),
            zaxis=dict(range=z_range, autorange=False),
            aspectratio=aspect_ratio,
            camera=camera
        ),
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': 'Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 350, 'redraw': True},  # Much slower - 350ms per frame
                        'fromcurrent': True,
                        'transition': {'duration': 150}  # Smoother transitions
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
    
    # Return data
    result = {
        'figure': fig,
        'volcano_type': volcano_type,
        'animation_data': animation_data,
        'volcano_name': volcano_name
    }
    
    return result