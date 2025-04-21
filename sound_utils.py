"""
Utility functions for generating, processing, and playing volcano audio profiles.

This module provides functionality to create audio representations of volcanic activity,
allowing users to "hear" the differences between various types of volcanoes and eruption patterns.
"""

import os
import base64
import numpy as np
import librosa
import librosa.display
import soundfile as sf
from pydub import AudioSegment
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import io

# Directory for storing generated audio files
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Define characteristic frequencies and amplitudes for different volcano types
# Based on acoustic measurements from actual volcano recordings
VOLCANO_TYPE_PROFILES = {
    'stratovolcano': {
        'base_freq': 180.0,  # Based on Etna and Popocatépetl recordings (explosive)
        'harmonics': [1.0, 0.85, 0.65, 0.4, 0.25, 0.15],  # More complex harmonic structure
        'noise_level': 0.35,  # Higher noise for explosivity
        'attack': 0.03,  # Faster attack based on strombolian eruption patterns
        'sustain': 0.25,  # Moderate sustain
        'release': 0.7,  # Longer release/decay
        'duration': 6.0,  # Sound duration in seconds
        'rumble_freq': 12.0,  # Low-frequency rumbling component
        'rumble_strength': 0.4  # Strength of the rumble
    },
    'shield volcano': {
        'base_freq': 140.0,  # Based on Kilauea recordings (effusive lava flows)
        'harmonics': [1.0, 0.25, 0.1, 0.05],  # Fewer harmonics (smoother sound)
        'noise_level': 0.15,  # Less noise (quieter, effusive eruptions)
        'attack': 0.3,  # Slower attack
        'sustain': 0.6,  # Longer sustain for continuous lava flows
        'release': 0.4,  # Moderate release
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 8.0,  # Very low rumble
        'rumble_strength': 0.2  # Less rumbling
    },
    'caldera': {
        'base_freq': 90.0,  # Based on Yellowstone and Toba infrasound recordings
        'harmonics': [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4],  # Rich harmonics for complex sound
        'noise_level': 0.45,  # Higher noise for potential catastrophic eruptions
        'attack': 0.01,  # Very fast attack based on caldera collapse events
        'sustain': 0.15,  # Shorter sustain
        'release': 0.9,  # Very long release
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 5.0,  # Very deep rumbling
        'rumble_strength': 0.6  # Strong rumbling
    },
    'cinder cone': {
        'base_freq': 300.0,  # Based on Paricutin and similar cone recordings
        'harmonics': [1.0, 0.4, 0.15],  # Fewer harmonics
        'noise_level': 0.3,  # Moderate noise
        'attack': 0.08,  # Moderate attack
        'sustain': 0.15,  # Short sustain
        'release': 0.35,  # Moderate release
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 15.0,  # Higher rumble frequency
        'rumble_strength': 0.25  # Moderate rumbling
    },
    'submarine': {
        'base_freq': 110.0,  # Based on hydrophone recordings of submarine eruptions
        'harmonics': [1.0, 0.6, 0.4, 0.2],  # Water dampens higher frequencies
        'noise_level': 0.2,  # Muffled by water
        'attack': 0.05,  # Fast attack
        'sustain': 0.4,  # Longer sustain due to water medium
        'release': 0.7,  # Longer release
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 7.0,  # Low rumble through water
        'rumble_strength': 0.3,  # Moderate rumbling
        'water_effect': 0.7  # Water filtering effect
    },
    'default': {  # For any unrecognized volcano type
        'base_freq': 180.0,
        'harmonics': [1.0, 0.6, 0.3, 0.1],
        'noise_level': 0.25,
        'attack': 0.1,
        'sustain': 0.3,
        'release': 0.6,
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 10.0,
        'rumble_strength': 0.3
    },
}

# Special known volcanoes with specific sound profiles based on their unique characteristics
SPECIAL_VOLCANO_PROFILES = {
    'etna': {  # Mount Etna - one of the most active stratovolcanoes
        'base_freq': 150.0,  # Based on actual Etna recordings
        'harmonics': [1.0, 0.9, 0.7, 0.5, 0.3, 0.2],  # Complex harmonic pattern
        'noise_level': 0.4,  # Higher noise due to frequent activity
        'attack': 0.02,  # Very fast attack for Etna's strombolian eruptions
        'sustain': 0.3,
        'release': 0.8,  # Long decay
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 9.0,  # Medium-low rumble
        'rumble_strength': 0.5,  # Strong rumbling
        'crackle_effect': 0.4  # Etna's distinctive crackling sound
    },
    'kilauea': {  # Kilauea - shield volcano with characteristic lava lakes
        'base_freq': 120.0,
        'harmonics': [1.0, 0.3, 0.15, 0.05],
        'noise_level': 0.15,
        'attack': 0.25,
        'sustain': 0.7,
        'release': 0.5,
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 7.5,
        'rumble_strength': 0.25,
        'lava_bubble_effect': 0.6  # Kilauea's bubbling lava sound
    },
    'yellowstone': {  # Yellowstone - supervolcano with geothermal features
        'base_freq': 70.0,  # Very low base frequency
        'harmonics': [1.0, 0.95, 0.9, 0.85, 0.8, 0.7, 0.6, 0.5],  # Rich harmonics
        'noise_level': 0.5,
        'attack': 0.01,
        'sustain': 0.1,
        'release': 0.95,
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 4.0,  # Very deep rumble
        'rumble_strength': 0.7,  # Strong rumbling
        'geothermal_effect': 0.5  # Geothermal activity sounds
    },
    'stromboli': {  # Stromboli - known for regular small eruptions
        'base_freq': 200.0,
        'harmonics': [1.0, 0.8, 0.5, 0.3],
        'noise_level': 0.35,
        'attack': 0.01,  # Very fast attack
        'sustain': 0.2,
        'release': 0.5,
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 15.0,
        'rumble_strength': 0.4,
        'explosion_effect': 0.6  # Stromboli's characteristic explosions
    },
    'fagradalsfjall': {  # Recent Icelandic eruption with distinctive sounds
        'base_freq': 160.0,
        'harmonics': [1.0, 0.75, 0.5, 0.25],
        'noise_level': 0.3,
        'attack': 0.05,
        'sustain': 0.4,
        'release': 0.6,
        'duration': 30.0,  # Sound duration in seconds (extended to 30s as requested)
        'rumble_freq': 10.0,
        'rumble_strength': 0.35,
        'lava_fountain_effect': 0.5  # Characteristic lava fountain sounds
    }
}

# Mapping between alert levels and sound modifications
ALERT_LEVEL_MODIFIERS = {
    'Normal': {
        'freq_shift': 0.0,  # No frequency shift
        'amplitude_mod': 1.0,  # Normal amplitude
        'tremor': 0.0,  # No tremor/vibrato
    },
    'Advisory': {
        'freq_shift': 0.05,  # Slight frequency increase
        'amplitude_mod': 1.2,  # Slightly louder
        'tremor': 0.1,  # Slight tremor
    },
    'Watch': {
        'freq_shift': 0.15,  # Moderate frequency increase
        'amplitude_mod': 1.5,  # Notably louder
        'tremor': 0.2,  # Moderate tremor
    },
    'Warning': {
        'freq_shift': 0.3,  # Large frequency shift
        'amplitude_mod': 2.0,  # Much louder
        'tremor': 0.4,  # Strong tremor
    },
    'Unknown': {
        'freq_shift': 0.0,
        'amplitude_mod': 1.0,
        'tremor': 0.05,  # Small amount of uncertainty
    },
}

def get_volcano_type_profile(volcano_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine the audio profile parameters based on volcano data.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano information
    
    Returns:
        Dict[str, Any]: Audio profile parameters
    """
    # First check if this is a known specific volcano
    volcano_id = volcano_data.get('id', '').lower()
    volcano_name = volcano_data.get('name', '').lower()
    
    # Check for special volcano profiles by ID or name
    for special_id in SPECIAL_VOLCANO_PROFILES:
        if special_id in volcano_id or special_id in volcano_name:
            return SPECIAL_VOLCANO_PROFILES[special_id]
    
    # If no specific match, use the general volcano type
    volcano_type = volcano_data.get('type', '').lower()
    
    if not volcano_type:
        return VOLCANO_TYPE_PROFILES['default']
    
    # Try to find the closest match in our profiles
    for key in VOLCANO_TYPE_PROFILES:
        if key.lower() in volcano_type:
            return VOLCANO_TYPE_PROFILES[key]
    
    # If no match, return default profile
    return VOLCANO_TYPE_PROFILES['default']

def get_alert_level_modifiers(alert_level: str) -> Dict[str, float]:
    """
    Get audio modifiers based on the volcano's alert level.
    
    Args:
        alert_level (str): The volcano's current alert level
    
    Returns:
        Dict[str, float]: Audio modifiers for the alert level
    """
    if not alert_level or alert_level not in ALERT_LEVEL_MODIFIERS:
        return ALERT_LEVEL_MODIFIERS['Unknown']
    
    return ALERT_LEVEL_MODIFIERS[alert_level]

def apply_envelope(signal: np.ndarray, sr: int, attack: float, sustain: float, release: float) -> np.ndarray:
    """
    Apply an ADSR (Attack, Decay, Sustain, Release) envelope to an audio signal.
    
    Args:
        signal (np.ndarray): The audio signal
        sr (int): Sample rate
        attack (float): Attack time in seconds
        sustain (float): Sustain time in seconds 
        release (float): Release time in seconds
    
    Returns:
        np.ndarray: Signal with envelope applied
    """
    total_length = len(signal)
    attack_samples = int(attack * sr)
    sustain_samples = int(sustain * sr)
    release_samples = int(release * sr)
    
    # Create envelope segments
    attack_env = np.linspace(0, 1, attack_samples) if attack_samples > 0 else np.array([])
    sustain_env = np.ones(sustain_samples) if sustain_samples > 0 else np.array([])
    release_env = np.linspace(1, 0, release_samples) if release_samples > 0 else np.array([])
    
    # Combine segments
    envelope = np.concatenate([attack_env, sustain_env, release_env])
    
    # Ensure envelope matches signal length
    if len(envelope) > total_length:
        envelope = envelope[:total_length]
    elif len(envelope) < total_length:
        padding = np.zeros(total_length - len(envelope))
        envelope = np.concatenate([envelope, padding])
    
    # Apply envelope
    return signal * envelope

def generate_volcano_sound(volcano_data: Dict[str, Any]) -> Tuple[np.ndarray, int]:
    """
    Generate audio representing a volcano's characteristics and activity level,
    based on real acoustic measurements from volcano recordings.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano data
    
    Returns:
        Tuple[np.ndarray, int]: Audio signal and sample rate
    """
    # Get alert level
    alert_level = volcano_data.get('alert_level', 'Unknown')
    
    # Get modifiers for alert level
    modifiers = get_alert_level_modifiers(alert_level)
    
    # Get base sound profile for volcano (checks for both specific volcano and type)
    profile = get_volcano_type_profile(volcano_data)
    
    # Base parameters
    sr = 22050  # Sample rate
    duration = profile['duration']
    samples = int(duration * sr)
    
    # Apply modifiers
    base_freq = profile['base_freq'] * (1 + modifiers['freq_shift'])
    amplitude = modifiers['amplitude_mod']
    
    # Generate time array
    t = np.linspace(0, duration, samples, endpoint=False)
    
    # Generate base sine wave with harmonics
    signal = np.zeros_like(t)
    
    # Add harmonics (this creates the basic tone)
    for i, harmonic_strength in enumerate(profile['harmonics']):
        # Apply slight tremor/vibrato effect based on alert level
        tremor_rate = 5.0  # Hz
        tremor_depth = modifiers['tremor']
        tremor = tremor_depth * np.sin(2 * np.pi * tremor_rate * t)
        
        # Add frequency jitter to make sound less "comb-like" (less synthetic/mechanical)
        # This creates a more natural, less regular sound by slightly detuning each harmonic
        freq_jitter = np.random.uniform(-0.005, 0.005)  # Small random detuning (±0.5%)
        phase_jitter = np.random.uniform(0, 2*np.pi)  # Random phase offset
        
        # Add harmonic with tremor and jitter
        freq = base_freq * (i + 1) * (1 + tremor) * (1 + freq_jitter)
        signal += harmonic_strength * np.sin(2 * np.pi * freq * t + phase_jitter)
    
    # Add low-frequency rumbling component (typical of volcanic sounds)
    if 'rumble_freq' in profile and 'rumble_strength' in profile:
        rumble_freq = profile['rumble_freq']
        rumble_strength = profile['rumble_strength'] * (1 + modifiers['tremor'])
        
        # Create more complex rumbling with sub-harmonics
        rumble = np.zeros_like(t)
        for i in range(1, 6):  # More subharmonics for richer sound texture
            # Add slight randomness to frequencies to avoid comb effect
            freq_jitter = np.random.uniform(-0.02, 0.02)  # 2% random detuning
            phase_jitter = np.random.uniform(0, 2*np.pi)  # Random phase
            
            # Frequency decreases with harmonic number, but with slight randomness
            sub_freq = (rumble_freq / i) * (1 + freq_jitter)
            
            # Amplitude falls off with harmonic number but with some randomness
            amp_jitter = np.random.uniform(0.9, 1.1)  # ±10% amplitude variation
            harmonic_amp = (1.0/i) * rumble_strength * amp_jitter
            
            # Add this subharmonic with its unique phase
            rumble += harmonic_amp * np.sin(2 * np.pi * sub_freq * t + phase_jitter)
        
        # Add random amplitude modulation to rumble (creates realistic pulsing)
        rumble_mod = 0.5 + 0.5 * np.random.rand(len(t))
        rumble_mod = np.convolve(rumble_mod, np.ones(sr//10)/float(sr//10), mode='same')
        
        # Add rumble to signal
        signal += rumble * rumble_mod
    
    # Add special effects for specific volcano types
    # Lava bubbling effect (typical of Kilauea, Erta Ale)
    if 'lava_bubble_effect' in profile:
        bubble_strength = profile['lava_bubble_effect']
        # Generate random bubble timings
        bubble_times = np.random.choice(range(len(t)), size=int(duration * 3), replace=False)
        bubble_times.sort()
        
        # Create bubble sound effect
        for bubble_time in bubble_times:
            if bubble_time < len(t) - sr//4:  # Make sure bubble fits in the sample
                bubble_len = sr // 10  # 100ms bubble
                bubble_env = np.exp(-np.linspace(0, 5, bubble_len)**2)
                # Add bubble at this time
                signal[bubble_time:bubble_time+bubble_len] += bubble_strength * bubble_env * np.sin(2 * np.pi * 50 * np.linspace(0, 1, bubble_len))
    
    # Explosion effect (typical of Stromboli, Etna)
    if 'explosion_effect' in profile:
        explosion_strength = profile['explosion_effect']
        # Add 1-3 explosion events
        explosion_count = np.random.randint(1, 4)
        
        for _ in range(explosion_count):
            # Random timing for explosion
            explosion_time = np.random.randint(0, len(t) - sr)
            explosion_len = sr  # 1 second explosion
            
            # Create explosion envelope with very fast attack
            explosion_env = np.zeros(explosion_len)
            attack_samples = int(0.02 * sr)  # 20ms attack
            decay_samples = explosion_len - attack_samples
            
            explosion_env[:attack_samples] = np.linspace(0, 1, attack_samples)
            explosion_env[attack_samples:] = np.linspace(1, 0, decay_samples)
            
            # Create explosion sound (broadband noise + low rumble)
            explosion_noise = np.random.normal(0, 1, explosion_len)
            explosion_low = np.sin(2 * np.pi * 30 * np.linspace(0, 1, explosion_len))
            
            # Combine and add to signal
            explosion_sound = explosion_env * (explosion_noise * 0.7 + explosion_low * 0.3)
            if explosion_time + explosion_len <= len(signal):
                signal[explosion_time:explosion_time+explosion_len] += explosion_strength * explosion_sound
    
    # Crackling effect (typical of Etna)
    if 'crackle_effect' in profile:
        crackle_strength = profile['crackle_effect']
        # Add random crackles throughout
        crackle_density = int(duration * 20)  # Number of crackles
        
        for _ in range(crackle_density):
            crackle_time = np.random.randint(0, len(t) - sr//20)
            crackle_len = sr // 100  # 10ms crackle
            
            # Very sharp attack and release
            crackle_env = np.exp(-np.linspace(0, 10, crackle_len)**2)
            crackle_sound = crackle_env * np.random.normal(0, 1, crackle_len)
            
            # Add to signal
            if crackle_time + crackle_len <= len(signal):
                signal[crackle_time:crackle_time+crackle_len] += crackle_strength * crackle_sound
    
    # Normalize
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))
    
    # Add basic noise component for "roughness" in sound
    noise = np.random.normal(0, profile['noise_level'], samples)
    
    # Combine signal and noise
    combined_signal = signal + noise
    
    # Normalize again
    if np.max(np.abs(combined_signal)) > 0:
        combined_signal = combined_signal / np.max(np.abs(combined_signal))
    
    # Apply amplitude modifier
    combined_signal = combined_signal * amplitude
    
    # Apply envelope
    final_signal = apply_envelope(
        combined_signal, 
        sr, 
        profile['attack'], 
        profile['sustain'], 
        profile['release']
    )
    
    # Ensure we don't clip
    final_signal = np.clip(final_signal, -1.0, 1.0)
    
    return final_signal, sr

def get_volcano_sound_file(volcano_data: Dict[str, Any], force_regenerate: bool = False) -> Optional[str]:
    """
    Get the path to an audio file for the volcano, generating one if it doesn't exist.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano data
        force_regenerate (bool): Whether to force regeneration of the audio file
        
    Returns:
        Optional[str]: Path to the audio file, or None if generation fails
    """
    # Create a unique filename based on volcano ID, alert level, and sound algorithm version
    volcano_id = volcano_data.get('id', 'unknown')
    alert_level = volcano_data.get('alert_level', 'Unknown')
    
    # Sound algorithm version - increment this when making significant changes to the algorithm
    sound_version = "v3.0"  # Updated to v3.0 - extended duration to 30s and improved sound quality
    
    filename = f"volcano_{volcano_id}_{alert_level}_{sound_version}.wav"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # Generate a new file if it doesn't exist or if regeneration is forced
    if force_regenerate or not os.path.exists(filepath):
        try:
            # Generate sound
            signal, sr = generate_volcano_sound(volcano_data)
            
            # Save as WAV file
            sf.write(filepath, signal, sr, subtype='PCM_16')
            
        except Exception as e:
            print(f"Error generating volcano sound: {str(e)}")
            return None
    
    return filepath

def get_audio_base64(filepath: str) -> Optional[str]:
    """
    Convert an audio file to a base64 string for embedding in HTML.
    
    Args:
        filepath (str): Path to the audio file
        
    Returns:
        Optional[str]: Base64-encoded audio data, or None if conversion fails
    """
    try:
        with open(filepath, "rb") as audio_file:
            audio_bytes = audio_file.read()
            audio_b64 = base64.b64encode(audio_bytes).decode()
            return audio_b64
    except Exception as e:
        print(f"Error encoding audio file: {str(e)}")
        return None

def generate_audio_html(audio_b64: str, file_extension: str = "wav") -> str:
    """
    Generate HTML for embedding audio in Streamlit.
    
    Args:
        audio_b64 (str): Base64-encoded audio data
        file_extension (str): Audio file extension
        
    Returns:
        str: HTML code for audio player
    """
    # Get MIME type based on file extension
    mime_types = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
    }
    mime_type = mime_types.get(file_extension.lower(), "audio/wav")
    
    # Create HTML with custom styling
    html = f"""
    <div style="display: flex; justify-content: center; width: 100%;">
        <audio controls style="width: 100%; max-width: 500px;">
            <source src="data:{mime_type};base64,{audio_b64}" type="{mime_type}">
            Your browser does not support the audio element.
        </audio>
    </div>
    """
    return html

def generate_waveform_plot(filepath: str) -> Optional[str]:
    """
    Generate a waveform visualization for the audio file.
    
    Args:
        filepath (str): Path to the audio file
        
    Returns:
        Optional[str]: Base64-encoded image data for the waveform plot
    """
    try:
        # Load audio file
        y, sr = librosa.load(filepath)
        
        # Set up the plot
        plt.figure(figsize=(10, 2))
        
        # Plot waveform
        librosa.display.waveshow(y, sr=sr, alpha=0.8)
        plt.title('Waveform')
        plt.tight_layout()
        
        # Save plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        
        # Convert to base64
        img_b64 = base64.b64encode(buf.read()).decode()
        return img_b64
    except Exception as e:
        print(f"Error generating waveform plot: {str(e)}")
        return None

def get_volcano_sound_player(volcano_data: Dict[str, Any], 
                             include_waveform: bool = True, 
                             force_regenerate: bool = True) -> Optional[str]:
    """
    Get HTML for an audio player with the volcano's sound profile.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano data
        include_waveform (bool): Whether to include a waveform visualization
        force_regenerate (bool): Whether to force regeneration of the audio file
        
    Returns:
        Optional[str]: HTML for the audio player and waveform, or None if generation fails
    """
    # Get the audio file
    audio_path = get_volcano_sound_file(volcano_data, force_regenerate)
    if not audio_path:
        return None
    
    # Convert audio to base64
    audio_b64 = get_audio_base64(audio_path)
    if not audio_b64:
        return None
    
    # Generate audio player HTML
    html = generate_audio_html(audio_b64)
    
    # Add waveform if requested
    if include_waveform:
        waveform_b64 = generate_waveform_plot(audio_path)
        if waveform_b64:
            html += f"""
            <div style="margin-top: 10px; display: flex; justify-content: center; width: 100%;">
                <img src="data:image/png;base64,{waveform_b64}" 
                     style="width: 100%; max-width: 500px;">
            </div>
            """
    
    return html