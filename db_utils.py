"""
Database utilities for the Volcano Monitoring Dashboard.

This module provides functions for interacting with the database,
including user preferences, favorites, notes, and other persistent data.
"""

import os
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Database setup
DB_PATH = "data/volcano_dashboard.db"

def get_db_connection():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with necessary tables."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    
    # Create tables for user data
    conn.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volcano_id TEXT NOT NULL,
        name TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        country TEXT,
        region TEXT,
        type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_term TEXT NOT NULL,
        search_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volcano_id TEXT NOT NULL,
        volcano_name TEXT NOT NULL,
        note_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Volcano characteristics for user observations and custom data
    conn.execute("""
    CREATE TABLE IF NOT EXISTS volcano_characteristics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volcano_id TEXT NOT NULL,
        observation_type TEXT NOT NULL,
        value TEXT NOT NULL,
        confidence REAL,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Eruption history table for custom events
    conn.execute("""
    CREATE TABLE IF NOT EXISTS eruption_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volcano_id TEXT NOT NULL,
        eruption_date TEXT NOT NULL,
        vei INTEGER,
        description TEXT,
        data_source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Satellite image links
    conn.execute("""
    CREATE TABLE IF NOT EXISTS satellite_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volcano_id TEXT NOT NULL,
        image_date TEXT NOT NULL,
        image_url TEXT NOT NULL,
        image_type TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Risk assessment data
    conn.execute("""
    CREATE TABLE IF NOT EXISTS risk_assessment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volcano_id TEXT NOT NULL,
        risk_factor TEXT NOT NULL,
        risk_value REAL NOT NULL,
        assessment_date TEXT NOT NULL,
        methodology TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Ensure database is initialized
try:
    init_db()
except Exception as e:
    print(f"Database initialization error: {str(e)}")

# Favorites functions
def add_favorite_volcano(volcano: Dict[str, Any]) -> bool:
    """
    Add a volcano to favorites.
    
    Args:
        volcano (Dict[str, Any]): Volcano data dictionary
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        
        # Check if already exists
        cursor = conn.execute(
            "SELECT id FROM favorites WHERE volcano_id = ?", 
            (volcano['id'],)
        )
        
        if cursor.fetchone() is not None:
            # Already exists, return True
            conn.close()
            return True
            
        conn.execute(
            """
            INSERT INTO favorites (volcano_id, name, latitude, longitude, country, region, type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                volcano['id'],
                volcano['name'],
                volcano.get('latitude', None),
                volcano.get('longitude', None),
                volcano.get('country', None),
                volcano.get('region', None),
                volcano.get('type', None)
            )
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding to favorites: {str(e)}")
        return False

def remove_favorite_volcano(volcano_id: str) -> bool:
    """
    Remove a volcano from favorites.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        conn.execute(
            "DELETE FROM favorites WHERE volcano_id = ?",
            (volcano_id,)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing from favorites: {str(e)}")
        return False

def get_favorite_volcanoes() -> List[Dict[str, Any]]:
    """
    Get all favorite volcanoes.
    
    Returns:
        List[Dict[str, Any]]: List of favorite volcano dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM favorites ORDER BY created_at DESC"
        )
        
        favorites = []
        for row in cursor:
            favorites.append({
                'id': row['volcano_id'],
                'name': row['name'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'country': row['country'],
                'region': row['region'],
                'type': row['type'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return favorites
    except Exception as e:
        print(f"Error getting favorites: {str(e)}")
        return []

def is_favorite_volcano(volcano_id: str) -> bool:
    """
    Check if a volcano is in favorites.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        bool: True if in favorites, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT id FROM favorites WHERE volcano_id = ?",
            (volcano_id,)
        )
        
        is_favorite = cursor.fetchone() is not None
        conn.close()
        return is_favorite
    except Exception as e:
        print(f"Error checking favorite status: {str(e)}")
        return False

# Search history functions
def add_search_history(search_term: str, search_type: str) -> bool:
    """
    Add a search term to search history.
    
    Args:
        search_term (str): Search term
        search_type (str): Type of search (e.g., 'name', 'region')
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO search_history (search_term, search_type)
            VALUES (?, ?)
            """,
            (search_term, search_type)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding to search history: {str(e)}")
        return False

def get_search_history(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get search history.
    
    Args:
        limit (int): Maximum number of entries to return
        
    Returns:
        List[Dict[str, Any]]: List of search history entries
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            f"SELECT * FROM search_history ORDER BY created_at DESC LIMIT {limit}"
        )
        
        history = []
        for row in cursor:
            history.append({
                'id': row['id'],
                'search_term': row['search_term'],
                'search_type': row['search_type'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return history
    except Exception as e:
        print(f"Error getting search history: {str(e)}")
        return []

# User notes functions
def add_user_note(volcano_id: str, volcano_name: str, note_text: str) -> bool:
    """
    Add or update a user note for a volcano.
    
    Args:
        volcano_id (str): Volcano ID
        volcano_name (str): Volcano name
        note_text (str): Note text
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        
        # Check if note already exists
        cursor = conn.execute(
            "SELECT id FROM user_notes WHERE volcano_id = ?",
            (volcano_id,)
        )
        
        row = cursor.fetchone()
        if row is not None:
            # Update existing note
            conn.execute(
                """
                UPDATE user_notes 
                SET note_text = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (note_text, row['id'])
            )
        else:
            # Insert new note
            conn.execute(
                """
                INSERT INTO user_notes (volcano_id, volcano_name, note_text)
                VALUES (?, ?, ?)
                """,
                (volcano_id, volcano_name, note_text)
            )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding/updating note: {str(e)}")
        return False

def get_user_note(volcano_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user note for a volcano.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        Optional[Dict[str, Any]]: Note dictionary or None if not found
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM user_notes WHERE volcano_id = ?",
            (volcano_id,)
        )
        
        row = cursor.fetchone()
        if row is not None:
            note = {
                'id': row['id'],
                'volcano_id': row['volcano_id'],
                'volcano_name': row['volcano_name'],
                'note_text': row['note_text'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
        else:
            note = None
            
        conn.close()
        return note
    except Exception as e:
        print(f"Error getting note: {str(e)}")
        return None

def get_all_user_notes() -> List[Dict[str, Any]]:
    """
    Get all user notes.
    
    Returns:
        List[Dict[str, Any]]: List of note dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM user_notes ORDER BY updated_at DESC"
        )
        
        notes = []
        for row in cursor:
            notes.append({
                'id': row['id'],
                'volcano_id': row['volcano_id'],
                'volcano_name': row['volcano_name'],
                'note_text': row['note_text'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
            
        conn.close()
        return notes
    except Exception as e:
        print(f"Error getting all notes: {str(e)}")
        return []

# Volcano characteristics functions
def get_volcano_characteristics(volcano_id: str, observation_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get volcano characteristics.
    
    Args:
        volcano_id (str): Volcano ID
        observation_type (Optional[str]): Filter by observation type
        
    Returns:
        List[Dict[str, Any]]: List of characteristic dictionaries
    """
    try:
        conn = get_db_connection()
        
        if observation_type is not None:
            # Get by type
            cursor = conn.execute(
                """
                SELECT * FROM volcano_characteristics 
                WHERE volcano_id = ? AND observation_type = ?
                ORDER BY created_at DESC
                """,
                (volcano_id, observation_type)
            )
        else:
            # Get all
            cursor = conn.execute(
                """
                SELECT * FROM volcano_characteristics 
                WHERE volcano_id = ?
                ORDER BY observation_type, created_at DESC
                """,
                (volcano_id,)
            )
        
        characteristics = []
        for row in cursor:
            characteristics.append({
                'id': row['id'],
                'volcano_id': row['volcano_id'],
                'observation_type': row['observation_type'],
                'value': row['value'],
                'confidence': row['confidence'],
                'source': row['source'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return characteristics
    except Exception as e:
        print(f"Error getting volcano characteristics: {str(e)}")
        return []

def save_volcano_characteristics(
    volcano_id: str, 
    observation_type: str, 
    value: str, 
    confidence: Optional[float] = None, 
    source: Optional[str] = None
) -> bool:
    """
    Save a volcano characteristic.
    
    Args:
        volcano_id (str): Volcano ID
        observation_type (str): Type of observation
        value (str): Value of observation
        confidence (float, optional): Confidence level (0-1)
        source (str, optional): Source of observation
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        
        conn.execute(
            """
            INSERT INTO volcano_characteristics 
            (volcano_id, observation_type, value, confidence, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (volcano_id, observation_type, value, confidence, source)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving volcano characteristic: {str(e)}")
        return False

# Eruption history functions
def get_volcano_eruption_history(volcano_id: str) -> List[Dict[str, Any]]:
    """
    Get eruption history for a volcano.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        List[Dict[str, Any]]: List of eruption events
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            """
            SELECT * FROM eruption_history 
            WHERE volcano_id = ?
            ORDER BY eruption_date DESC
            """,
            (volcano_id,)
        )
        
        events = []
        for row in cursor:
            events.append({
                'id': row['id'],
                'volcano_id': row['volcano_id'],
                'eruption_date': row['eruption_date'],
                'vei': row['vei'],
                'description': row['description'],
                'data_source': row['data_source'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return events
    except Exception as e:
        print(f"Error getting eruption history: {str(e)}")
        return []

def add_eruption_event(
    volcano_id: str, 
    eruption_date: str, 
    vei: Optional[int] = None, 
    description: Optional[str] = None, 
    data_source: Optional[str] = None
) -> bool:
    """
    Add an eruption event to history.
    
    Args:
        volcano_id (str): Volcano ID
        eruption_date (str): Date of eruption (format flexible)
        vei (int, optional): Volcanic Explosivity Index
        description (str, optional): Description of eruption
        data_source (str, optional): Source of data
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        
        conn.execute(
            """
            INSERT INTO eruption_history 
            (volcano_id, eruption_date, vei, description, data_source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (volcano_id, eruption_date, vei, description, data_source)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding eruption event: {str(e)}")
        return False

# Satellite image functions
def get_volcano_satellite_images(volcano_id: str, image_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get satellite images for a volcano.
    
    Args:
        volcano_id (str): Volcano ID
        image_type (Optional[str]): Filter by image type
        
    Returns:
        List[Dict[str, Any]]: List of image dictionaries
    """
    try:
        conn = get_db_connection()
        
        if image_type is not None:
            # Get by type
            cursor = conn.execute(
                """
                SELECT * FROM satellite_images 
                WHERE volcano_id = ? AND image_type = ?
                ORDER BY image_date DESC
                """,
                (volcano_id, image_type)
            )
        else:
            # Get all
            cursor = conn.execute(
                """
                SELECT * FROM satellite_images 
                WHERE volcano_id = ?
                ORDER BY image_date DESC
                """,
                (volcano_id,)
            )
        
        images = []
        for row in cursor:
            images.append({
                'id': row['id'],
                'volcano_id': row['volcano_id'],
                'image_date': row['image_date'],
                'image_url': row['image_url'],
                'image_type': row['image_type'],
                'description': row['description'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return images
    except Exception as e:
        print(f"Error getting satellite images: {str(e)}")
        return []

def add_satellite_image(
    volcano_id: str, 
    image_url: str, 
    image_date: str, 
    image_type: str, 
    description: Optional[str] = None
) -> bool:
    """
    Add a satellite image.
    
    Args:
        volcano_id (str): Volcano ID
        image_url (str): URL to image
        image_date (str): Date of image capture
        image_type (str): Type of image (e.g., 'InSAR', 'Thermal', 'RGB')
        description (str, optional): Description of image
        
    Returns:
        bool: Success status
    """
    try:
        conn = get_db_connection()
        
        conn.execute(
            """
            INSERT INTO satellite_images 
            (volcano_id, image_url, image_date, image_type, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (volcano_id, image_url, image_date, image_type, description)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding satellite image: {str(e)}")
        return False

# Risk assessment functions
def get_volcano_risk_assessment(volcano_id: str) -> List[Dict[str, Any]]:
    """
    Get risk assessment data for a volcano.
    
    Args:
        volcano_id (str): Volcano ID
        
    Returns:
        List[Dict[str, Any]]: List of risk assessment dictionaries
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute(
            """
            SELECT * FROM risk_assessment 
            WHERE volcano_id = ?
            ORDER BY risk_factor
            """,
            (volcano_id,)
        )
        
        assessments = []
        for row in cursor:
            assessments.append({
                'id': row['id'],
                'volcano_id': row['volcano_id'],
                'risk_factor': row['risk_factor'],
                'risk_value': row['risk_value'],
                'assessment_date': row['assessment_date'],
                'methodology': row['methodology'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return assessments
    except Exception as e:
        print(f"Error getting risk assessment: {str(e)}")
        return []