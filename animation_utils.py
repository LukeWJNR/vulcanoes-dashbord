"""
Animation utilities for the Volcano Monitoring Dashboard.

This module provides functions to generate animation data and visualizations
for various volcano types and eruption phases.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional

# Volcano type definitions
VOLCANO_TYPES = {
    "shield": {
        "description": "Broad, gently sloping volcano with basaltic lava flows",
        "examples": ["Mauna Loa", "Kilauea"],
        "eruption_style": "Effusive",
        "magma_viscosity": "Low",
        "explosivity": "Low",
        "dome_formation": False,
        "caldera_formation": False,
        "plume_height_avg": 2.5,  # in km
        "plume_height_max": 8.0,  # in km
        "lava_flow_rate_avg": 50.0,  # in m³/s
        "magma_temperature": 1200,  # in °C
        "magma_composition": "Basaltic",
        "magma_chamber_depth": 3.5,  # in km
        "secondary_chambers": True,
        "deformation_pattern": "Broad, radial inflation during magma accumulation"
    },
    "stratovolcano": {
        "description": "Steep-sided, symmetrical cone with alternating layers of lava and pyroclastics",
        "examples": ["Mount Fuji", "Mount St. Helens"],
        "eruption_style": "Explosive",
        "magma_viscosity": "High",
        "explosivity": "High",
        "dome_formation": True,
        "caldera_formation": False,
        "plume_height_avg": 15.0,  # in km
        "plume_height_max": 25.0,  # in km
        "lava_flow_rate_avg": 10.0,  # in m³/s
        "magma_temperature": 950,  # in °C
        "magma_composition": "Andesitic to Dacitic",
        "magma_chamber_depth": 5.0,  # in km
        "secondary_chambers": True,
        "deformation_pattern": "Asymmetric patterns due to complex structure and flank instability"
    },
    "caldera": {
        "description": "Large, basin-shaped depression formed by collapse",
        "examples": ["Yellowstone", "Toba"],
        "eruption_style": "Highly Explosive",
        "magma_viscosity": "Very High",
        "explosivity": "Very High",
        "dome_formation": True,
        "caldera_formation": True,
        "plume_height_avg": 25.0,  # in km
        "plume_height_max": 40.0,  # in km
        "lava_flow_rate_avg": 5.0,  # in m³/s
        "magma_temperature": 850,  # in °C
        "magma_composition": "Rhyolitic",
        "magma_chamber_depth": 8.0,  # in km
        "secondary_chambers": True,
        "deformation_pattern": "Ring-like patterns with complex subsidence/uplift interactions"
    },
    "cinder_cone": {
        "description": "Small, steep-sided cone built from ejected lava fragments",
        "examples": ["Paricutin", "Cerro Negro"],
        "eruption_style": "Mild to Moderate Explosive",
        "magma_viscosity": "Moderate",
        "explosivity": "Moderate",
        "dome_formation": False,
        "caldera_formation": False,
        "plume_height_avg": 5.0,  # in km
        "plume_height_max": 10.0,  # in km
        "lava_flow_rate_avg": 15.0,  # in m³/s
        "magma_temperature": 1050,  # in °C
        "magma_composition": "Basaltic to Andesitic",
        "magma_chamber_depth": 2.0,  # in km
        "secondary_chambers": False,
        "deformation_pattern": "Localized, minor ground movement with minimal pre-eruption signals"
    },
    "lava_dome": {
        "description": "Rounded, steep-sided mass formed by viscous lava",
        "examples": ["Soufrière Hills", "Mount St. Helens Dome"],
        "eruption_style": "Effusive to Explosive",
        "magma_viscosity": "Very High",
        "explosivity": "Moderate",
        "dome_formation": True,
        "caldera_formation": False,
        "plume_height_avg": 8.0,  # in km
        "plume_height_max": 15.0,  # in km
        "lava_flow_rate_avg": 2.0,  # in m³/s
        "magma_temperature": 800,  # in °C
        "magma_composition": "Dacitic to Rhyolitic",
        "magma_chamber_depth": 4.0,  # in km
        "secondary_chambers": False,
        "deformation_pattern": "Very localized, high-gradient deformation with potential flank instability"
    }
}

# Alert level definitions
ALERT_LEVELS = {
    "Normal": {
        "description": "Volcano is in typical background, non-eruptive state",
        "color": "green",
        "hazard_radius_km": 0,
        "evacuation_recommended": False,
        "monitoring_level": "Routine",
        "update_frequency": "Monthly"
    },
    "Advisory": {
        "description": "Volcano is exhibiting signs of elevated unrest above known background level",
        "color": "yellow",
        "hazard_radius_km": 2,
        "evacuation_recommended": False,
        "monitoring_level": "Heightened",
        "update_frequency": "Weekly"
    },
    "Watch": {
        "description": "Volcano is exhibiting heightened or escalating unrest with increased potential of eruption",
        "color": "orange",
        "hazard_radius_km": 5,
        "evacuation_recommended": "Prepare",
        "monitoring_level": "Elevated",
        "update_frequency": "Daily"
    },
    "Warning": {
        "description": "Hazardous eruption is imminent, underway, or suspected",
        "color": "red",
        "hazard_radius_km": 10,
        "evacuation_recommended": True,
        "monitoring_level": "Maximum",
        "update_frequency": "Multiple times daily"
    }
}

def determine_volcano_type(volcano_data: Dict[str, Any]) -> str:
    """
    Determine the volcano type based on its characteristics.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano information
        
    Returns:
        str: Volcano type (shield, stratovolcano, caldera, cinder_cone, lava_dome)
    """
    volcano_type = volcano_data.get('type', '').lower()
    
    # Check for specific keywords in the type field
    if 'shield' in volcano_type:
        return 'shield'
    elif any(x in volcano_type for x in ['strato', 'composite', 'stratovol']):
        return 'stratovolcano'
    elif any(x in volcano_type for x in ['caldera', 'collapse']):
        return 'caldera'
    elif any(x in volcano_type for x in ['cinder', 'scoria', 'cone']):
        return 'cinder_cone'
    elif any(x in volcano_type for x in ['dome', 'lava dome']):
        return 'lava_dome'
    
    # Default to stratovolcano as the most common type
    return 'stratovolcano'

def get_eruption_probability(volcano_data: Dict[str, Any]) -> float:
    """
    Calculate eruption probability based on volcano characteristics.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano information
        
    Returns:
        float: Eruption probability (0-100)
    """
    # Start with a base probability
    base_probability = 5.0
    
    # Adjust based on alert level
    alert_level = volcano_data.get('alert_level', 'Normal')
    alert_adjustments = {
        'Normal': 0,
        'Advisory': 15,
        'Watch': 35,
        'Warning': 60
    }
    
    probability = base_probability + alert_adjustments.get(alert_level, 0)
    
    # Adjust based on time since last eruption
    last_eruption = volcano_data.get('last_eruption')
    if last_eruption:
        try:
            # Convert to year if it's a date string
            if isinstance(last_eruption, str) and '-' in last_eruption:
                year = int(last_eruption.split('-')[0])
            else:
                year = int(last_eruption)
                
            years_since = 2025 - year  # Current year minus last eruption year
            
            # Volcanoes that have been quiet for very long might be less likely to erupt
            # unless they're in an active phase
            if years_since < 10:
                probability += 15  # Recently active
            elif years_since < 50:
                probability += 5   # Active in living memory
            elif years_since < 200:
                probability -= 2   # Long dormant
            else:
                probability -= 5   # Very long dormant
                
        except (ValueError, TypeError):
            # If we can't parse the date, don't adjust
            pass
    
    # Ensure probability is within 0-100 range
    return max(0, min(100, probability))

def generate_eruption_timeline(
    volcano_type: str, 
    eruption_probability: float, 
    days: int = 30
) -> Dict[str, List[Any]]:
    """
    Generate a timeline of eruption events and precursors.
    
    Args:
        volcano_type (str): Type of volcano
        eruption_probability (float): Probability of eruption (0-100)
        days (int): Number of days to simulate
        
    Returns:
        Dict[str, List[Any]]: Dictionary containing timeline series data
    """
    # Determine if an eruption will occur based on probability
    eruption_occurs = np.random.random() * 100 < eruption_probability
    
    # Create time points for each day
    time_points = np.arange(days)
    
    # Initialize data series
    seismic_activity = np.zeros(days)
    gas_emissions = np.zeros(days)
    deformation = np.zeros(days)
    temperature = np.zeros(days)
    eruption_intensity = np.zeros(days)
    
    if not eruption_occurs:
        # No eruption, just random background noise
        seismic_activity = np.random.normal(5, 2, days)
        gas_emissions = np.random.normal(10, 3, days)
        deformation = np.random.normal(2, 0.5, days)
        temperature = np.random.normal(15, 2, days)
        
        # Ensure non-negative values
        seismic_activity = np.maximum(seismic_activity, 0)
        gas_emissions = np.maximum(gas_emissions, 0)
        deformation = np.maximum(deformation, 0)
        temperature = np.maximum(temperature, 0)
    else:
        # Determine eruption day based on timeline
        eruption_day = int(days * 0.6)  # Eruption at 60% of timeline
        
        # Generate precursor data
        for i in range(days):
            # Pre-eruption build-up
            if i < eruption_day:
                # Exponential increase in activity leading up to eruption
                progress = i / eruption_day
                
                # Each volcano type has different precursor patterns
                if volcano_type == 'shield':
                    # Shield volcanoes often have more gradual build-up
                    seismic_activity[i] = 5 + 15 * progress**2
                    gas_emissions[i] = 10 + 30 * progress**1.5
                    deformation[i] = 2 + 8 * progress**2
                    temperature[i] = 15 + 25 * progress
                    
                elif volcano_type == 'stratovolcano':
                    # Stratovolcanoes often have sharper increase before eruption
                    seismic_activity[i] = 5 + 25 * progress**3
                    gas_emissions[i] = 10 + 50 * progress**2
                    deformation[i] = 2 + 12 * progress**1.5
                    temperature[i] = 15 + 35 * progress**1.2
                    
                elif volcano_type == 'caldera':
                    # Calderas can have massive build-up
                    seismic_activity[i] = 5 + 35 * progress**2.5
                    gas_emissions[i] = 10 + 70 * progress**2
                    deformation[i] = 2 + 18 * progress**2
                    temperature[i] = 15 + 45 * progress**1.5
                    
                elif volcano_type == 'cinder_cone':
                    # Cinder cones often have less obvious precursors
                    seismic_activity[i] = 5 + 10 * progress**1.5
                    gas_emissions[i] = 10 + 20 * progress
                    deformation[i] = 2 + 5 * progress
                    temperature[i] = 15 + 15 * progress
                    
                elif volcano_type == 'lava_dome':
                    # Lava domes often show deformation and temperature changes
                    seismic_activity[i] = 5 + 15 * progress**2
                    gas_emissions[i] = 10 + 25 * progress**1.5
                    deformation[i] = 2 + 15 * progress**1.8
                    temperature[i] = 15 + 40 * progress**1.5
                
                # Add some random noise to make it more realistic
                seismic_activity[i] += np.random.normal(0, 2)
                gas_emissions[i] += np.random.normal(0, 3)
                deformation[i] += np.random.normal(0, 0.5)
                temperature[i] += np.random.normal(0, 2)
                
            # Eruption and post-eruption
            else:
                # Days since eruption start
                days_since = i - eruption_day
                
                # Eruption intensity varies by volcano type
                if volcano_type == 'shield':
                    # Shield volcanoes: longer, less explosive eruptions
                    max_intensity = 60
                    decay_rate = 0.1  # Slower decay
                    
                elif volcano_type == 'stratovolcano':
                    # Stratovolcanoes: intense, explosive eruptions
                    max_intensity = 85
                    decay_rate = 0.3
                    
                elif volcano_type == 'caldera':
                    # Calderas: most intense eruptions
                    max_intensity = 95
                    decay_rate = 0.2
                    
                elif volcano_type == 'cinder_cone':
                    # Cinder cones: moderate eruptions
                    max_intensity = 65
                    decay_rate = 0.4  # Faster decay
                    
                elif volcano_type == 'lava_dome':
                    # Lava domes: less explosive, longer-lasting
                    max_intensity = 50
                    decay_rate = 0.1  # Much slower decay
                    
                else:
                    # Default values
                    max_intensity = 70
                    decay_rate = 0.2
                
                # Calculate eruption intensity with decay over time
                eruption_intensity[i] = max_intensity * np.exp(-decay_rate * days_since)
                
                # During eruption, other indicators behave differently
                seismic_activity[i] = 20 + eruption_intensity[i] * 0.5 + np.random.normal(0, 5)
                gas_emissions[i] = 40 + eruption_intensity[i] * 0.7 + np.random.normal(0, 7)
                deformation[i] = 10 - days_since * 0.5 + np.random.normal(0, 1)  # Decreases after eruption
                temperature[i] = 30 + eruption_intensity[i] * 0.6 + np.random.normal(0, 4)
                
                # Ensure deformation doesn't go negative
                deformation[i] = max(deformation[i], 0)
        
        # Ensure non-negative values for all series
        seismic_activity = np.maximum(seismic_activity, 0)
        gas_emissions = np.maximum(gas_emissions, 0)
        deformation = np.maximum(deformation, 0)
        temperature = np.maximum(temperature, 0)
    
    # Return the time series data
    return {
        'time': time_points.tolist(),
        'seismic_activity': seismic_activity.tolist(),
        'gas_emissions': gas_emissions.tolist(),
        'deformation': deformation.tolist(),
        'temperature': temperature.tolist(),
        'eruption_intensity': eruption_intensity.tolist(),
        'eruption_occurred': eruption_occurs
    }
    
def generate_magma_chamber_animation(volcano_type: str, time_step: int, max_steps: int = 100) -> dict:
    """
    Generate data for animating a magma chamber based on volcano type and time step.
    
    Args:
        volcano_type (str): Type of volcano (shield, stratovolcano, etc)
        time_step (int): Current time step in the animation sequence
        max_steps (int): Total number of steps in animation
        
    Returns:
        dict: Dictionary with magma chamber animation data
    """
    # Get volcano type characteristics
    volcano_info = VOLCANO_TYPES.get(volcano_type, VOLCANO_TYPES['stratovolcano'])
    
    # Chamber depth varies by volcano type
    chamber_depth = volcano_info.get('magma_chamber_depth', 5.0)
    has_secondary = volcano_info.get('secondary_chambers', False)
    
    # Calculate fill percentage based on time step
    progress = min(1.0, time_step / (0.7 * max_steps))  # Magma fills up to 70% of timeline
    
    # Chamber dimensions
    main_chamber = {
        'width': 3.0 + 1.0 * progress,  # Grows slightly as it fills
        'height': 1.5 + 0.5 * progress,
        'depth': chamber_depth,
        'fill_percent': min(100, progress * 120),  # 0-100%
        'pressure': progress ** 2 * 100,  # 0-100 MPa
        'temperature': volcano_info.get('magma_temperature', 1000) * (0.8 + 0.2 * progress)
    }
    
    # Secondary chambers if applicable
    secondary_chambers = []
    if has_secondary:
        # Add a deeper, smaller chamber
        secondary_chambers.append({
            'width': 2.0 + 0.5 * progress,
            'height': 1.0 + 0.2 * progress,
            'depth': chamber_depth * 1.5,  # Deeper than main chamber
            'fill_percent': min(100, progress * 150),  # Fills faster than main chamber
            'pressure': progress ** 2 * 120,  # Slightly higher pressure
            'temperature': volcano_info.get('magma_temperature', 1000) * (0.9 + 0.15 * progress)
        })
    
    # Calculate conduit dimensions
    conduit_width = 0.2 + 0.3 * progress
    
    # For shield volcanoes, create a wider plumbing system
    if volcano_type == 'shield':
        conduit_width *= 1.5
        main_chamber['width'] *= 1.2
    
    # For calderas, create a much larger chamber system
    elif volcano_type == 'caldera':
        main_chamber['width'] *= 1.5
        main_chamber['height'] *= 1.3
    
    # Return complete animation data
    return {
        'main_chamber': main_chamber,
        'secondary_chambers': secondary_chambers,
        'conduit_width': conduit_width,
        'magma_viscosity': volcano_info.get('magma_viscosity', 'Medium'),
        'magma_composition': volcano_info.get('magma_composition', 'Andesitic'),
        'time_step': time_step,
        'max_steps': max_steps,
        'progress_percent': progress * 100
    }

def generate_deformation_plot(volcano_type: str, time_steps: int, max_steps: int) -> dict:
    """
    Generate data for ground deformation plot based on volcano type.
    
    Args:
        volcano_type (str): Type of volcano
        time_steps (int): Current time step
        max_steps (int): Maximum time steps
        
    Returns:
        dict: Dictionary with deformation data
    """
    # Get volcano type characteristics
    volcano_info = VOLCANO_TYPES.get(volcano_type, VOLCANO_TYPES['stratovolcano'])
    
    # Calculate progress as a percentage of total steps
    progress = min(1.0, time_steps / max_steps)
    
    # Initialize distance and deformation arrays
    distances = np.linspace(-10, 10, 100)  # km from center of volcano
    deformation = np.zeros_like(distances)
    
    # Different volcano types have different deformation patterns
    max_deform = {
        'shield': 0.15,          # Less deformation in shield volcanoes
        'stratovolcano': 0.25,   # Moderate deformation
        'caldera': 0.4,          # Significant deformation
        'cinder_cone': 0.1,      # Minor deformation
        'lava_dome': 0.3         # Significant surface deformation
    }.get(volcano_type, 0.2)
    
    # Shape parameters for the deformation curve
    width_param = {
        'shield': 3.5,           # Wider deformation field
        'stratovolcano': 2.5,    # Medium width
        'caldera': 4.0,          # Very wide
        'cinder_cone': 1.8,      # Narrow
        'lava_dome': 2.0         # Narrow and concentrated
    }.get(volcano_type, 2.5)
    
    # Calculate the deformation curve (bell curve shape)
    deformation = max_deform * progress * np.exp(-(distances**2) / width_param**2)
    
    # Add some random noise to make it look more realistic
    noise = np.random.normal(0, 0.01, size=len(distances))
    deformation += noise
    
    # Only return what we need
    return {
        'distances': distances.tolist(),
        'deformation': deformation.tolist(),
        'max_deformation': float(np.max(deformation)),
        'min_deformation': float(np.min(deformation)),
        'time_step': time_steps,
        'max_steps': max_steps,
        'progress_percent': progress * 100
    }

def generate_eruption_sequence_animation(volcano_type: str, time_step: int, max_steps: int) -> dict:
    """
    Generate eruption sequence animation data.
    
    Args:
        volcano_type (str): Type of volcano
        time_step (int): Current time step
        max_steps (int): Maximum time steps
        
    Returns:
        dict: Dictionary with eruption sequence data
    """
    # Get volcano type characteristics
    volcano_info = VOLCANO_TYPES.get(volcano_type, VOLCANO_TYPES['stratovolcano'])
    
    # Calculate progress
    progress = min(1.0, time_step / max_steps)
    
    # Define phases of eruption
    phases = {
        'pre_eruption': progress < 0.4,
        'initial_eruption': 0.4 <= progress < 0.6,
        'main_eruption': 0.6 <= progress < 0.85,
        'waning': 0.85 <= progress
    }
    
    # Current phase
    current_phase = next((name for name, is_active in phases.items() if is_active), 'pre_eruption')
    
    # Calculate phase-specific progress
    phase_progress = {
        'pre_eruption': min(1.0, progress / 0.4),
        'initial_eruption': min(1.0, (progress - 0.4) / 0.2),
        'main_eruption': min(1.0, (progress - 0.6) / 0.25),
        'waning': min(1.0, (progress - 0.85) / 0.15)
    }
    
    # Volcanic plume height (in kilometers)
    max_plume_height = volcano_info.get('plume_height_max', 10.0)
    plume_height = 0
    
    # Ash columns develop during initial and main phases
    if current_phase == 'initial_eruption':
        plume_height = max_plume_height * 0.5 * phase_progress[current_phase]
    elif current_phase == 'main_eruption':
        plume_height = max_plume_height * (0.5 + 0.5 * phase_progress[current_phase])
    elif current_phase == 'waning':
        plume_height = max_plume_height * (1.0 - 0.7 * phase_progress[current_phase])
    
    # Lava flow parameters
    lava_flow_length = 0
    max_flow_length = {
        'shield': 10.0,           # Long flows
        'stratovolcano': 5.0,     # Medium flows
        'caldera': 3.0,           # Short flows, more explosive
        'cinder_cone': 2.0,       # Short flows
        'lava_dome': 1.0          # Very short flows
    }.get(volcano_type, 5.0)
    
    # Calculate lava flow length
    if current_phase == 'initial_eruption':
        lava_flow_length = max_flow_length * 0.2 * phase_progress[current_phase]
    elif current_phase == 'main_eruption':
        lava_flow_length = max_flow_length * (0.2 + 0.7 * phase_progress[current_phase])
    elif current_phase == 'waning':
        lava_flow_length = max_flow_length * (0.9 + 0.1 * phase_progress[current_phase])
    
    # Pyroclastic flows mainly occur in explosive eruptions
    pyroclastic_flow_length = 0
    if volcano_type in ['stratovolcano', 'caldera']:
        if current_phase == 'main_eruption':
            pyroclastic_flow_length = 4.0 * phase_progress[current_phase]
    
    # Ash deposit thickness (in meters)
    ash_thickness = 0
    if current_phase in ['initial_eruption', 'main_eruption', 'waning']:
        ash_accumulation_rate = {
            'shield': 0.01,        # Minimal ash
            'stratovolcano': 0.1,  # Moderate ash
            'caldera': 0.3,        # Heavy ash
            'cinder_cone': 0.05,   # Light ash
            'lava_dome': 0.02      # Very light ash
        }.get(volcano_type, 0.1)
        
        # Ash accumulates over time
        if current_phase == 'initial_eruption':
            ash_thickness = ash_accumulation_rate * phase_progress[current_phase]
        elif current_phase == 'main_eruption':
            ash_thickness = ash_accumulation_rate * (1.0 + 2.0 * phase_progress[current_phase])
        elif current_phase == 'waning':
            ash_thickness = ash_accumulation_rate * (3.0 + 0.5 * phase_progress[current_phase])
    
    # Return all animation data
    return {
        'volcano_type': volcano_type,
        'time_step': time_step,
        'max_steps': max_steps,
        'progress': progress * 100,
        'current_phase': current_phase,
        'phase_progress': phase_progress[current_phase] * 100,
        'plume_height': plume_height,
        'lava_flow_length': lava_flow_length,
        'pyroclastic_flow_length': pyroclastic_flow_length,
        'ash_thickness': ash_thickness,
        'explosion_intensity': volcano_info.get('explosivity', 'Medium'),
        'magma_viscosity': volcano_info.get('magma_viscosity', 'Medium')
    }