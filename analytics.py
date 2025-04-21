"""
Analytics utilities for the Volcano Monitoring Dashboard.

This module provides functions for integrating analytics tracking
into the Streamlit application.
"""

import streamlit as st
import streamlit.components.v1 as components

def inject_ga_tracking():
    """
    Inject Google Analytics tracking code into the Streamlit app.
    This should be called at the top of each page to ensure tracking is in place.
    """
    # Google Analytics tracking code
    ga_tracking = """
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-GFPNQB0M23"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
    
      gtag('config', 'G-GFPNQB0M23');
    </script>
    """
    
    # Inject the tracking code
    components.html(ga_tracking, height=0, width=0)
    
def track_event(event_category, event_action, event_label=None, event_value=None):
    """
    Track a custom event in Google Analytics.
    
    Args:
        event_category (str): The event category
        event_action (str): The event action
        event_label (str, optional): The event label
        event_value (int, optional): The event value
    """
    event_js = """
    <script>
    // Check if gtag is defined
    if (typeof gtag === 'function') {
        gtag('event', '%s', {
            'event_category': '%s',
            'event_label': '%s',
            'value': %s
        });
    }
    </script>
    """ % (
        event_action,
        event_category,
        event_label or '',
        str(event_value) if event_value is not None else '0'
    )
    
    # Inject the event tracking code
    components.html(event_js, height=0, width=0)