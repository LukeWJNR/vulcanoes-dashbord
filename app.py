import streamlit as st

# Set page config - MUST be the first Streamlit command
st.set_page_config(
    page_title="Volcano Monitoring Dashboard",
    page_icon="🌋",
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/openvolcano/data',
        'About': 'Volcano Monitoring Dashboard providing real-time information about active volcanoes worldwide with InSAR satellite imagery links.'
    }
)

import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import time
import os
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.runtime.state import SessionStateProxy

# Import analytics utilities
from utils.analytics import inject_ga_tracking, track_event

# Inject Google Analytics tracking code
try:
    inject_ga_tracking()
except Exception as e:
    st.error(f"Error with analytics: {str(e)}")

# Load custom CSS
try:
    with open("assets/custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading CSS: {str(e)}")
    
# Initialize session state variables at the start
if 'selected_volcano' not in st.session_state:
    st.session_state.selected_volcano = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'user_note' not in st.session_state:
    st.session_state.user_note = ""
if 'favorites' not in st.session_state:
    st.session_state.favorites = []
if 'last_region' not in st.session_state:
    st.session_state.last_region = "All"
if 'last_name_filter' not in st.session_state:
    st.session_state.last_name_filter = ""
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

# Function to switch pages in a multi-page app
def switch_page(page_name: str):
    """
    Switch to a different page in a Streamlit multi-page app
    
    Args:
        page_name (str): Name of the page to switch to (without .py extension)
    """
    from streamlit.runtime.scriptrunner import RerunData, RerunException
    
    def standardize_name(name: str) -> str:
        return name.lower().replace("_", " ")
    
    page_name = standardize_name(page_name)
    
    # Get current page info
    ctx = get_script_run_ctx()
    if ctx is None:
        raise RuntimeError("Could not get script context")
    
    # Get all pages
    pages = ctx.page_script_hash.keys()
    
    # Find the matching page
    for page in pages:
        if standardize_name(page.split("/")[-1].split(".")[0]) == page_name:
            raise RerunException(
                RerunData(
                    page_script_hash=ctx.page_script_hash,
                    page_name=page,
                    query_string=ctx.query_string
                )
            )

from utils.api import get_volcano_data, get_volcano_details
from utils.risk_assessment import calculate_volcano_metrics, calculate_lava_buildup_index
from utils.map_utils import create_volcano_map, create_popup_html
from utils.web_scraper import get_so2_data as get_satellite_so2_data
from utils.web_scraper import get_volcanic_ash_data, get_radon_data
from utils.insar_data import get_insar_url_for_volcano, generate_sentinel_hub_url, generate_copernicus_url, generate_smithsonian_wms_url
from utils.comet_utils import get_comet_url_for_volcano
from utils.wovodat_utils import (
    get_wovodat_volcano_data,
    get_so2_data as get_wovodat_so2_data,
    get_lava_injection_data,
    get_wovodat_insar_url,
    get_volcano_monitoring_status
)
from utils.db_utils import (
    add_favorite_volcano, 
    remove_favorite_volcano, 
    get_favorite_volcanoes, 
    is_favorite_volcano,
    add_search_history,
    get_search_history,
    add_user_note,
    get_user_note,
    get_all_user_notes,
    # New database functions
    get_volcano_characteristics,
    save_volcano_characteristics,
    get_volcano_eruption_history,
    add_eruption_event,
    get_volcano_satellite_images,
    add_satellite_image,
    get_volcano_risk_assessment
)

# Page config already set at the top of the file

# Custom CSS for iframe embedding
st.markdown("""
<style>
    /* Make the app more compact for iframe embedding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Adjust header sizes for compact display */
    h1 {
        font-size: 1.8rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
    }
    
    h3 {
        font-size: 1.2rem !important;
    }
    
    /* Make sidebar narrower to maximize map space */
    [data-testid="stSidebar"] {
        min-width: 250px !important;
        max-width: 250px !important;
    }
    
    /* Responsive adjustments for iframe */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.5rem !important;
        }
        
        [data-testid="stSidebar"] {
            min-width: 200px !important;
            max-width: 200px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# App title and introduction
st.title("🌋 Volcano Monitoring Dashboard")

# Two-column layout for intro text and features
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("""
    This dashboard displays real-time data about active volcanoes around the world, 
    sourced from the USGS Volcano Hazards Program. You can explore the map, filter volcanoes, 
    and access InSAR satellite imagery data for research and monitoring purposes.
    """)

with col2:
    st.markdown("""
    ### Key Features
    - 🌎 **Interactive Global Map** with 1,400+ volcanoes
    - 🔍 **Region & Name Filtering** for precise research
    - 🛰️ **InSAR Satellite Data** integration for deformation monitoring
    - 📊 **Scientific Visualizations** showing eruption processes
    - 🧪 **Eruption Simulator** with risk assessment
    - 🧊 **Climate Connection** analysis of glaciated volcanoes
    """)

# Add horizontal rule for visual separation
st.markdown("---")

# Create the main map section immediately after introduction
# Create two columns with map taking more space
map_col1, map_col2 = st.columns([7, 3])

with map_col1:
    # Create and display the map
    st.subheader("Active Volcano Map")
    
    # Display a message about the number of volcanos shown
    try:
        # Load volcano data for the map
        with st.spinner("Loading volcano data..."):
            volcanos_df = get_volcano_data()
            # Calculate volcano risk metrics including Lava Build-Up Index
            volcanos_df = calculate_volcano_metrics(volcanos_df)
            if st.session_state.last_update is None:
                st.session_state.last_update = datetime.now()
        
        # Get filter values from UI with defaults
        filter_region = selected_region if 'selected_region' in locals() else "All"
        filter_name = volcano_name_filter if 'volcano_name_filter' in locals() else ""
        
        # Get data layer values with defaults
        show_monitoring = True
        if 'include_monitoring_data' in locals():
            show_monitoring = include_monitoring_data
            
        show_eq = True
        if 'show_earthquakes' in locals():
            show_eq = show_earthquakes
            
        show_eq_swarms = True
        if 'show_swarms' in locals():
            show_eq_swarms = show_swarms
            
        show_deform = True
        if 'show_deformation' in locals():
            show_deform = show_deformation
                
        # Apply filters
        filtered_df = volcanos_df.copy()
        if filter_region != "All":
            filtered_df = filtered_df[filtered_df['region'] == filter_region]
            
        if filter_name:
            filtered_df = filtered_df[filtered_df['name'].str.contains(filter_name, case=False)]
            
        st.markdown(f"Showing {len(filtered_df)} volcanos")
        
        # Create the map with optional monitoring data layers
        m = create_volcano_map(filtered_df, 
                             include_monitoring_data=show_monitoring,
                             show_earthquakes=show_eq,
                             show_swarms=show_eq_swarms,
                             show_deformation=show_deform)
        
        # Add custom styling for proper iframe embedding
        st.markdown("""
        <style>
            /* Make the map container responsive */
            iframe {
                width: 100%;
                min-height: 450px;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Display the map
        st_folium(
            m,
            height=500,
            width=700,
            returned_objects=[],
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Error displaying volcano map: {str(e)}")

# Additional horizontal rule for visual separation
st.markdown("---")

# Define our professional icons using SVG format
icons = {
    "dashboard": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>""",
    
    "eruption": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5h8l4 8-4 8H8l-4-8 4-8z"></path><path d="M12 9v12"></path><path d="M8 13h8"></path></svg>""",
    
    "satellite": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4.5h18"></path><path d="M5 4.5a9.16 9.16 0 0 1-.5 5.24"></path><path d="M7 4.5a5.89 5.89 0 0 0 .5 5.24"></path><path d="M4.24 10.24a9.45 9.45 0 0 0 7.5 2.75"></path><circle cx="14.5" cy="13" r="4"></circle><path d="m17 15.5 3.5 3.5"></path></svg>""",
    
    "risk": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>""",
    
    "news": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8V6Z"></path></svg>""",
    
    "favorites": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>""",
    
    "notes": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><line x1="10" y1="9" x2="8" y2="9"></line></svg>"""
}

# Add navigation links with professional SVG icons
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    st.markdown(f"""<a href="/" target="_self" class="nav-link">
                    {icons['dashboard']} <span>Dashboard</span>
                </a>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<a href="/pages/eruption_simulator.py" target="_self" class="nav-link">
                    {icons['eruption']} <span>Simulator</span>
                </a>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<a href="/pages/sar_animations.py" target="_self" class="nav-link">
                    {icons['satellite']} <span>SAR Data</span>
                </a>""", unsafe_allow_html=True)
# Risk Map removed as requested
# with col4:
#     st.markdown(f"""<a href="/pages/risk_map.py" target="_self" class="nav-link">
#                     {icons['risk']} <span>Risk Map</span>
#                 </a>""", unsafe_allow_html=True)
with col5:
    st.markdown(f"""<a href="/pages/volcano_news.py" target="_self" class="nav-link">
                    {icons['news']} <span>News</span>
                </a>""", unsafe_allow_html=True)
with col6:
    st.markdown(f"""<a href="/pages/favorites.py" target="_self" class="nav-link">
                    {icons['favorites']} <span>Favorites</span>
                </a>""", unsafe_allow_html=True)
with col7:
    st.markdown(f"""<a href="/pages/notes.py" target="_self" class="nav-link">
                    {icons['notes']} <span>Notes</span>
                </a>""", unsafe_allow_html=True)

st.markdown("---")

# Initialize session state for storing selected volcano
if 'selected_volcano' not in st.session_state:
    st.session_state.selected_volcano = None

if 'last_update' not in st.session_state:
    st.session_state.last_update = None
    
# Initialize other session state variables
if 'user_note' not in st.session_state:
    st.session_state.user_note = ""
    
if 'favorites' not in st.session_state:
    # Load favorites from database
    try:
        st.session_state.favorites = get_favorite_volcanoes()
    except Exception as e:
        st.session_state.favorites = []
        st.warning(f"Could not load favorites: {str(e)}")

# Load volcano data first - we'll need this for both the filters and the map
with st.spinner("Loading volcano data..."):
    try:
        volcanos_df = get_volcano_data()
        # Calculate volcano risk metrics including Lava Build-Up Index
        volcanos_df = calculate_volcano_metrics(volcanos_df)
        if st.session_state.last_update is None:
            st.session_state.last_update = datetime.now()
    except Exception as e:
        st.error(f"Error loading volcano data: {str(e)}")
        st.stop()

# Extract unique regions for filter
regions = sorted(volcanos_df['region'].unique().tolist())

# Create top filters and data layers section instead of sidebar
st.markdown("<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>", unsafe_allow_html=True)

# Use columns for the filters and data layers
filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])

# Set default filter values
selected_region = "All"
volcano_name_filter = ""
include_monitoring_data = True
show_earthquakes = True
show_swarms = True
show_deformation = True

with filter_col1:
    st.markdown("<h3 style='margin-top: 0px; font-size: 1.2rem;'>Filters</h3>", unsafe_allow_html=True)
    selected_region = st.selectbox("Select Region", ["All"] + regions, key="region_filter_top")

with filter_col2:
    st.markdown("<h3 style='margin-top: 0px; font-size: 1.2rem;'>Search</h3>", unsafe_allow_html=True)
    volcano_name_filter = st.text_input("Filter by Volcano Name", key="name_filter_top")

with filter_col3:
    st.markdown("<h3 style='margin-top: 0px; font-size: 1.2rem;'>Data Layers</h3>", unsafe_allow_html=True)
    include_monitoring_data = st.checkbox("Show Monitoring Data", value=True, help="Display SO2, volcanic ash, and radon gas monitoring data layers on the map")
    
    # Add additional data layer checkboxes in a row
    col_eq, col_swarm, col_deform = st.columns(3)
    with col_eq:
        show_earthquakes = st.checkbox("Show Earthquakes", value=True, help="Display recent earthquakes (last 24h)")
    with col_swarm:
        show_swarms = st.checkbox("Show Earthquake Swarms", value=True, help="Display earthquake swarm locations and details")
    with col_deform:
        show_deformation = st.checkbox("Show Ground Deformation", value=True, help="Display ground uplift and subsidence data")

st.markdown("</div>", unsafe_allow_html=True)

# Keep a copy in the sidebar for compatibility
st.sidebar.title("Filters")
st.sidebar.selectbox("Select Region", ["All"] + regions, key="region_filter_sidebar", index=0 if selected_region == "All" else regions.index(selected_region) + 1)
st.sidebar.text_input("Filter by Volcano Name", value=volcano_name_filter, key="name_filter_sidebar")
st.sidebar.markdown("---")
st.sidebar.subheader("Data Layers")
st.sidebar.checkbox("Show Monitoring Data", value=include_monitoring_data, key="monitoring_sidebar")

# Track search filters
if 'last_region' not in st.session_state:
    st.session_state.last_region = "All"
    
if 'last_name_filter' not in st.session_state:
    st.session_state.last_name_filter = ""

# Apply filters
filtered_df = volcanos_df.copy()
if selected_region != "All":
    filtered_df = filtered_df[filtered_df['region'] == selected_region]
    
    # Track region change for search history
    if selected_region != st.session_state.last_region:
        try:
            add_search_history(selected_region, "region")
            st.session_state.last_region = selected_region
        except Exception as e:
            st.sidebar.warning(f"Could not save search history: {str(e)}")

if volcano_name_filter:
    filtered_df = filtered_df[filtered_df['name'].str.contains(volcano_name_filter, case=False)]
    
    # Track name filter change for search history
    if volcano_name_filter != st.session_state.last_name_filter:
        try:
            add_search_history(volcano_name_filter, "name")
            st.session_state.last_name_filter = volcano_name_filter
        except Exception as e:
            st.sidebar.warning(f"Could not save search history: {str(e)}")

# Display last update time
if st.session_state.last_update:
    st.sidebar.markdown(f"**Last updated:** {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

# Refresh button
if st.sidebar.button("Refresh Data"):
    with st.spinner("Refreshing volcano data..."):
        try:
            # Store old data for alert level comparison
            old_volcanos_df = None
            if 'volcanos_df' in locals():
                old_volcanos_df = volcanos_df.copy()
                
            # Get fresh data
            volcanos_df = get_volcano_data()
            # Calculate volcano risk metrics including Lava Build-Up Index
            volcanos_df = calculate_volcano_metrics(volcanos_df)
            st.session_state.last_update = datetime.now()
            
            # Check for alert level changes and notify subscribers if needed
            if old_volcanos_df is not None:
                try:
                    from utils.alerts import check_alert_level_changes
                    
                    # Process each volcano to check for alert level changes
                    alert_changes = []
                    for _, row in volcanos_df.iterrows():
                        volcano_id = row.get('id')
                        if volcano_id:
                            # Find old alert level
                            old_row = old_volcanos_df[old_volcanos_df['id'] == volcano_id]
                            old_alert_level = None
                            if not old_row.empty:
                                old_alert_level = old_row.iloc[0].get('alert_level')
                            
                            # Check if alert level changed and send notifications
                            result = check_alert_level_changes(row.to_dict(), old_alert_level)
                            if result:
                                alert_changes.append({
                                    'volcano': row.get('name', 'Unknown'),
                                    'new_level': row.get('alert_level', 'Unknown'),
                                    'old_level': old_alert_level,
                                    'alerts_sent': len(result)
                                })
                    
                    # Show summary of alert notifications if any were sent
                    if alert_changes:
                        st.sidebar.success(f"Sent alert notifications for {len(alert_changes)} volcanoes with changed alert levels.")
                        
                except Exception as e:
                    st.sidebar.warning(f"Alert notification processing error: {str(e)}")
            
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error refreshing data: {str(e)}")

# Favorite Volcanoes section in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Your Favorite Volcanoes")

# Display favorites
if st.session_state.favorites and len(st.session_state.favorites) > 0:
    for fav in st.session_state.favorites:
        if st.sidebar.button(f"🌋 {fav['name']}", key=f"fav_{fav['id']}"):
            # Find the volcano in the dataframe and set as selected
            selected_row = filtered_df[filtered_df['name'] == fav['name']]
            if not selected_row.empty:
                st.session_state.selected_volcano = selected_row.iloc[0].to_dict()
                st.rerun()
else:
    st.sidebar.info("You haven't added any favorites yet. Click on a volcano and use the 'Add to Favorites' button to save it here.")

# Search History section
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

# Toggle for search history
st.sidebar.markdown("---")
show_history = st.sidebar.checkbox("Show Search History", value=st.session_state.show_history)
if show_history != st.session_state.show_history:
    st.session_state.show_history = show_history
    st.rerun()

if st.session_state.show_history:
    st.sidebar.subheader("Recent Searches")
    
    try:
        history = get_search_history(limit=5)
        if history and len(history) > 0:
            for item in history:
                st.sidebar.markdown(
                    f"**{item['search_term']}** ({item['search_type']}) - {item['created_at']}"
                )
        else:
            st.sidebar.info("No search history yet")
    except Exception as e:
        st.sidebar.warning(f"Could not load search history: {str(e)}")

# Page navigation
st.sidebar.markdown("---")
st.sidebar.subheader("Navigation")

# Early Warning System page link
warning_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 21H8l-4-7H2v-2h2.7l4 7h1.1l2.5-7.5c1-3 2.1-3.5 6.7-3.5v2c-3.7 0-4 .2-4.5 1.6L11 18l-0.7 3Z"></path><path d="M17 8v12"></path><path d="M13 8h8"></path></svg>"""
if st.sidebar.button(f"{warning_icon} Early Warning System", help="Subscribe to volcano alert notifications"):
    switch_page("early_warning")

# Volcano Animations page link
animations_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path><path d="M5 3v4"></path><path d="M19 17v4"></path><path d="M3 5h4"></path><path d="M17 19h4"></path></svg>"""
if st.sidebar.button(f"{animations_icon} Volcano Animations", help="Explore interactive volcano visualizations"):
    switch_page("volcano_animations")

# Sound Profiles page link
sound_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 14l.001 7a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2v-7"></path><path d="M8 9v-.956a6 6 0 0 1 2.671-4.972L12 2l1.329 1.072A6 6 0 0 1 16 8.044V9"></path><path d="M18 9h-12a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1a2 2 0 0 0-2-2z"></path></svg>"""
if st.sidebar.button(f"{sound_icon} Volcano Sound Profiles", help="Explore volcanic acoustic signatures"):
    switch_page("sound_profiles")

# SAR Animations page link
sar_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="14.31" y1="8" x2="20.05" y2="17.94"></line><line x1="9.69" y1="8" x2="21.17" y2="8"></line><line x1="7.38" y1="12" x2="13.12" y2="2.06"></line><line x1="9.69" y1="16" x2="3.95" y2="6.06"></line><line x1="14.31" y1="16" x2="2.83" y2="16"></line><line x1="16.62" y1="12" x2="10.88" y2="21.94"></line></svg>"""
if st.sidebar.button(f"{sar_icon} SAR Animations", help="View SAR data and animations from COMET Volcano Portal"):
    switch_page("sar_animations")

# Volcanic Cloud Tracker page link
cloud_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path><path d="M22 19h-2"></path><path d="M9 13v2"></path><path d="M13 13v-2"></path><path d="M13 17v-2"></path><path d="M17 13v-2"></path><path d="M17 17v-2"></path></svg>"""
if st.sidebar.button(f"{cloud_icon} Volcanic Cloud Tracker", help="Track volcanic ash and gas clouds"):
    switch_page("volcanic_cloud_tracker")

# 2D Eruption Animation (Lightweight)
eruption_2d_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path></svg>"""
if st.sidebar.button(f"{eruption_2d_icon} 2D Eruption (Lightweight)", help="View lightweight 2D eruption visualization"):
    switch_page("lightweight_2d_eruption")

# Scientific 3D Eruption page link
scientific_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3"></path><path d="M21 8V5a2 2 0 0 0-2-2H8"></path><path d="M3 16v3a2 2 0 0 0 2 2h8"></path><path d="M16 21h5a2 2 0 0 0 2-2V8"></path><path d="M7 10v11"></path><path d="M14 13l3 3"></path><path d="M14 19l3-3"></path></svg>"""
if st.sidebar.button(f"{scientific_icon} Scientific 3D Eruption", help="Explore scientifically accurate 3D eruption model"):
    switch_page("scientific_3d_eruption")

# Anak Krakatau Case Study page link
case_study_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 7 9 6 9-6"></path><path d="M12 19 3 13v8l9 6 9-6v-8l-9 6z"></path><path d="m12 3-9 6 9 6 9-6-9-6z"></path></svg>"""
if st.sidebar.button(f"{case_study_icon} Anak Krakatau Study", help="View the 2018 Anak Krakatau collapse case study"):
    switch_page("anak_krakatau_case_study")

# Scientific Paper Reader page link
paper_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><rect x="8" y="12" width="8" height="2"></rect><rect x="8" y="16" width="8" height="2"></rect><path d="M10 8H8"></path></svg>"""
if st.sidebar.button(f"{paper_icon} Scientific Paper Reader", help="Analyze scientific papers on volcanology"):
    switch_page("scientific_paper_reader")

# Risk Map page link - removed as requested
# risk_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 19 21 12 17 5 21 12 2"></polygon></svg>"""
# if st.sidebar.button(f"{risk_icon} Risk Heat Map", help="View volcanic risk assessment heat map"):
#     switch_page("risk_map")
    
# Volcano News page link
news_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8V6Z"></path></svg>"""
if st.sidebar.button(f"{news_icon} Volcano News", help="View volcano news and external monitoring resources"):
    switch_page("volcano_news")

# Favorites page link
fav_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>"""
if st.sidebar.button(f"{fav_icon} My Favorites", help="View your favorite volcanoes"):
    switch_page("favorites")

# Notes page link
notes_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><line x1="10" y1="9" x2="8" y2="9"></line></svg>"""
if st.sidebar.button(f"{notes_icon} My Notes", help="View your volcano notes"):
    switch_page("notes")

# Information about data source
st.sidebar.markdown("---")
st.sidebar.markdown("""
### Data Sources
- Volcano data: [USGS Volcano Hazards Program](https://www.usgs.gov/programs/VHP)
- InSAR data: Links to appropriate satellite imagery providers
- Additional information: [Climate Links - Volcanoes](https://climatelinks.weebly.com/volcanoes.html)
""")

# Create two columns for the volcano information section
col1, col2 = st.columns([7, 3])

with col2:
    st.subheader("Volcano Information")
    
    if st.session_state.selected_volcano:
        volcano = st.session_state.selected_volcano
        
        # Main info panel with professional styling
        st.markdown('<div class="info-panel">', unsafe_allow_html=True)
        
        # Favorite button
        is_favorite = is_favorite_volcano(volcano['id'])
        col_info, col_fav = st.columns([3, 1])
        
        with col_info:
            st.markdown(f"<h3>{volcano['name']}</h3>", unsafe_allow_html=True)
        
        with col_fav:
            if is_favorite:
                favorite_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#FF5A5F" stroke="#FF5A5F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>"""
                if st.button(f"{favorite_icon} Remove from Favorites", help="Remove this volcano from your favorites"):
                    try:
                        remove_favorite_volcano(volcano['id'])
                        st.success(f"Removed {volcano['name']} from favorites")
                        # Reload favorites
                        st.session_state.favorites = get_favorite_volcanoes()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error removing from favorites: {str(e)}")
            else:
                favorite_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>"""
                if st.button(f"{favorite_icon} Add to Favorites", help="Add this volcano to your favorites"):
                    try:
                        add_favorite_volcano(volcano)
                        st.success(f"Added {volcano['name']} to favorites")
                        # Reload favorites
                        st.session_state.favorites = get_favorite_volcanoes()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding to favorites: {str(e)}")
        
        # Key statistics in nice cards
        st.markdown('<div class="stat-container">', unsafe_allow_html=True)
        
        # Elevation stat
        elevation = volcano.get('elevation', 'N/A')
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{elevation} m</div>
            <div class="stat-label">Elevation</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Type stat
        volcano_type = volcano.get('type', 'Unknown')
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{volcano_type.split()[0]}</div>
            <div class="stat-label">Type</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Last eruption stat
        last_eruption = volcano.get('last_eruption', 'Unknown')
        if last_eruption and len(str(last_eruption)) > 10:
            last_eruption = str(last_eruption)[:10] + "..."
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{last_eruption}</div>
            <div class="stat-label">Last Eruption</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close stat container
        
        # Location information
        st.markdown('<div class="info-section">', unsafe_allow_html=True)
        st.markdown('<h4>Location</h4>', unsafe_allow_html=True)
        
        # Region and country with icons
        location_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="10" r="3"></circle><path d="M12 2a8 8 0 0 0-8 8c0 1.892.402 3.13 1.5 4.5L12 22l6.5-7.5c1.098-1.37 1.5-2.608 1.5-4.5a8 8 0 0 0-8-8z"></path></svg>"""
        st.markdown(f"""
        <p>{location_icon} <strong>Region:</strong> {volcano['region']}</p>
        <p>{location_icon} <strong>Country:</strong> {volcano['country']}</p>
        """, unsafe_allow_html=True)
        
        # Add coordinates if available
        if 'latitude' in volcano and 'longitude' in volcano:
            coord_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path></svg>"""
            st.markdown(f"""
            <p>{coord_icon} <strong>Coordinates:</strong> {volcano['latitude']:.4f}, {volcano['longitude']:.4f}</p>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close info section
        
        # Alert level section with color-coded tag
        st.markdown('<div class="info-section">', unsafe_allow_html=True)
        st.markdown('<h4>Current Status</h4>', unsafe_allow_html=True)
        
        # Alert level with tag styling
        alert_level = volcano.get('alert_level', 'Unknown')
        alert_tag_class = {
            'Normal': 'tag-normal',
            'Advisory': 'tag-advisory',
            'Watch': 'tag-watch',
            'Warning': 'tag-warning',
            'Unknown': 'tag-uncertain'
        }.get(alert_level, 'tag-uncertain')
        
        status_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m8 2 1.88 1.88"></path><path d="M14.12 3.88 16 2"></path><path d="M9 7.13v-1a3.003 3.003 0 1 1 6 0v1"></path><path d="M12 20h0"></path><path d="m4.93 19.07 2.83-2.83 10.18-10.18c.96-.96.96-2.51 0-3.47-.96-.96-2.51-.96-3.47 0l-10.18 10.18-2.83 2.83c-.76.76-.76 2.01 0 2.83.76.76 2.01.76 2.83 0z"></path><path d="M18 12v4.5"></path><path d="M8.5 21A4.5 4.5 0 0 1 4 16.5V13"></path><path d="M22 16.5A4.5 4.5 0 0 1 17.5 21H13"></path></svg>"""
        
        st.markdown(f"""
        <p>{status_icon} <strong>Alert Level:</strong> <span class="info-tag {alert_tag_class}">{alert_level}</span></p>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close info section
        st.markdown('</div>', unsafe_allow_html=True)  # Close info panel
        
        # Fetch and display additional details
        try:
            volcano_details = get_volcano_details(volcano['id'])
            
            if volcano_details:
                # Additional Info Panel
                st.markdown('<div class="info-panel">', unsafe_allow_html=True)
                st.markdown('<h3>Additional Information</h3>', unsafe_allow_html=True)
                
                if 'description' in volcano_details and volcano_details['description']:
                    st.markdown('<div class="info-section">', unsafe_allow_html=True)
                    description_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>"""
                    st.markdown(f'<h4>{description_icon} Description</h4>', unsafe_allow_html=True)
                    st.markdown(f"<p>{volcano_details['description']}</p>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)  # Close info section
                
                if 'activity' in volcano_details and volcano_details['activity']:
                    st.markdown('<div class="info-section">', unsafe_allow_html=True)
                    activity_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"></path><path d="M14.5 9.5 16 8"></path><path d="M14.5 14.5 16 16"></path><path d="M9.5 14.5 8 16"></path><path d="M9.5 9.5 8 8"></path><path d="m12 6 1.5-1.5"></path><path d="M18 12h1.5"></path><path d="M12 18v1.5"></path><path d="M6 12H4.5"></path></svg>"""
                    st.markdown(f'<h4>{activity_icon} Recent Activity</h4>', unsafe_allow_html=True)
                    st.markdown(f"<p>{volcano_details['activity']}</p>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)  # Close info section
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close info panel
        except Exception as e:
            st.warning(f"Could not load additional details: {str(e)}")
        
        # User Notes section with styled panel
        st.markdown('<div class="info-panel">', unsafe_allow_html=True)
        notes_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><line x1="10" y1="9" x2="8" y2="9"></line></svg>"""
        st.markdown(f'<h3>{notes_icon} Your Notes</h3>', unsafe_allow_html=True)
        
        # Get existing note if any
        existing_note = get_user_note(volcano['id'])
        note_text = existing_note['note_text'] if existing_note else ""
        
        # Note timestamp
        if existing_note and existing_note.get('created_at'):
            st.markdown(f'<p class="text-muted"><small>Last updated: {existing_note["created_at"]}</small></p>', unsafe_allow_html=True)
        
        # Note input with custom styling
        st.markdown("""
        <style>
        .stTextArea textarea {
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 12px;
            font-family: 'SF Pro Text', Arial, sans-serif;
            font-size: 14px;
            resize: vertical;
            transition: border-color 0.3s ease;
            background-color: #F9FAFB;
        }
        .stTextArea textarea:focus {
            border-color: #FF5A5F;
            outline: none;
            box-shadow: 0 0 0 2px rgba(255, 90, 95, 0.2);
        }
        </style>
        """, unsafe_allow_html=True)
        
        user_note = st.text_area(
            "Add your notes about this volcano:",
            value=note_text,
            height=120,
            key=f"note_{volcano['id']}"
        )
        
        # Save note button with an icon
        save_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>"""
        
        col1, col2, col3 = st.columns([3, 3, 6])
        with col1:
            if st.button(f"{save_icon} Save Note", type="primary"):
                if user_note:
                    try:
                        add_user_note(volcano['id'], volcano['name'], user_note)
                        st.success("Note saved successfully!")
                    except Exception as e:
                        st.error(f"Error saving note: {str(e)}")
                else:
                    st.warning("Note is empty. Please add some text to save.")
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close info panel
        
        # InSAR Data links with professional panel
        st.markdown('<div class="info-panel">', unsafe_allow_html=True)
        satellite_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4.5h18"></path><path d="M5 4.5a9.16 9.16 0 0 1-.5 5.24"></path><path d="M7 4.5a5.89 5.89 0 0 0 .5 5.24"></path><path d="M4.24 10.24a9.45 9.45 0 0 0 7.5 2.75"></path><circle cx="14.5" cy="13" r="4"></circle><path d="m17 15.5 3.5 3.5"></path></svg>"""
        st.markdown(f'<h3>{satellite_icon} Satellite & InSAR Data</h3>', unsafe_allow_html=True)
        
        # Add styled info about InSAR
        st.markdown("""
        <p style="margin-bottom: 1rem; color: #555;">
            <strong>InSAR (Interferometric Synthetic Aperture Radar)</strong> data shows ground deformation 
            patterns that can indicate magma movement beneath volcanoes. Access current data from the 
            resources below.
        </p>
        """, unsafe_allow_html=True)
        
        # Create a grid layout for satellite data links
        st.markdown('<div class="satellite-links">', unsafe_allow_html=True)
        
        # CSS for link cards
        st.markdown("""
        <style>
        .satellite-links {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 1.5rem;
        }
        
        .link-card {
            background-color: #F9FAFB;
            border-radius: 8px;
            padding: 12px 15px;
            border: 1px solid #E5E7EB;
            transition: all 0.2s ease;
            text-decoration: none;
            color: #111827;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }
        
        .link-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            border-color: #FF5A5F;
            text-decoration: none;
        }
        
        .link-card svg {
            margin-bottom: 10px;
            stroke: #FF5A5F;
        }
        
        .link-title {
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 4px;
        }
        
        .link-description {
            font-size: 0.75rem;
            color: #4B5563;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Get specific InSAR URL for this volcano if available
        insar_url = get_insar_url_for_volcano(volcano['name'])
        if insar_url:
            insar_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.86 2h8.28L22 7.86v8.28L16.14 22H7.86L2 16.14V7.86L7.86 2z"></path><circle cx="12" cy="12" r="3"></circle><path d="m12 12 4.24 4.24"></path><path d="m12 12 3-5"></path><path d="m12 12-5-3"></path><path d="m12 12-4.24 4.24"></path></svg>"""
            st.markdown(f"""
            <a href="{insar_url}" target="_blank" class="link-card">
                {insar_icon}
                <div class="link-title">Dedicated InSAR</div>
                <div class="link-description">View InSAR data specific to {volcano['name']}</div>
            </a>
            """, unsafe_allow_html=True)
        
        # Generate Sentinel Hub URL
        sentinel_hub_url = generate_sentinel_hub_url(volcano['latitude'], volcano['longitude'])
        sentinel_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>"""
        st.markdown(f"""
        <a href="{sentinel_hub_url}" target="_blank" class="link-card">
            {sentinel_icon}
            <div class="link-title">Sentinel Hub</div>
            <div class="link-description">View satellite imagery from Sentinel-1/2</div>
        </a>
        """, unsafe_allow_html=True)
        
        # Generate ESA Copernicus URL
        copernicus_url = generate_copernicus_url(volcano['latitude'], volcano['longitude'])
        copernicus_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="m16 12-4-4-4 4"></path><path d="m16 12-4 4-4-4"></path></svg>"""
        st.markdown(f"""
        <a href="{copernicus_url}" target="_blank" class="link-card">
            {copernicus_icon}
            <div class="link-title">ESA Copernicus</div>
            <div class="link-description">Search ESA's satellite data archive</div>
        </a>
        """, unsafe_allow_html=True)
        
        # USGS link
        usgs_url = f"https://www.usgs.gov/volcanoes/volcanoes-around-the-world/{volcano['name'].lower().replace(' ', '-')}"
        usgs_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m2 12 8-2 2-8 2 8 8 2-8 2-2 8-2-8Z"></path></svg>"""
        st.markdown(f"""
        <a href="{usgs_url}" target="_blank" class="link-card">
            {usgs_icon}
            <div class="link-title">USGS Data</div>
            <div class="link-description">Official USGS volcano information</div>
        </a>
        """, unsafe_allow_html=True)
        
        # ASF SARVIEWS link (if coordinates are available)
        if 'latitude' in volcano and 'longitude' in volcano:
            sarviews_url = f"https://sarviews-hazards.alaska.edu/#{volcano['latitude']},{volcano['longitude']},6"
            sarviews_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a5 5 0 0 0-6 0 5 5 0 0 0-6 0"></path><path d="M12 8v7"></path><path d="M18 11a3 3 0 0 0-6 0 3 3 0 0 0-6 0"></path><path d="M18 14a1 1 0 0 0-2 0 1 1 0 0 0-2 0 1 1 0 0 0-2 0 1 1 0 0 0-2 0"></path><path d="M18 5a7 7 0 0 0-12 0"></path></svg>"""
            st.markdown(f"""
            <a href="{sarviews_url}" target="_blank" class="link-card">
                {sarviews_icon}
                <div class="link-title">ASF SARVIEWS</div>
                <div class="link-description">Interactive SAR data visualization</div>
            </a>
            """, unsafe_allow_html=True)
            
        # COMET Volcano Portal link
        location = {
            'latitude': volcano.get('latitude'),
            'longitude': volcano.get('longitude')
        }
        comet_url = get_comet_url_for_volcano(volcano['name'], location)
        comet_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"></path></svg>"""
        comet_portal_url = comet_url if comet_url else "https://comet.nerc.ac.uk/comet-volcano-portal/"
        st.markdown(f"""
        <a href="{comet_portal_url}" target="_blank" class="link-card">
            {comet_icon}
            <div class="link-title">COMET Portal</div>
            <div class="link-description">SAR animations and time series</div>
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close satellite links grid
        st.markdown('</div>', unsafe_allow_html=True)  # Close info panel
        
        # Risk Assessment Information with professional styling
        st.markdown('<div class="info-panel">', unsafe_allow_html=True)
        risk_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>"""
        st.markdown(f'<h3>{risk_icon} Risk Assessment</h3>', unsafe_allow_html=True)
        
        try:
            # Get risk assessment data for this volcano
            risk_data = get_volcano_risk_assessment(volcano['id'])
            
            if risk_data:
                # Set color based on risk level
                risk_levels = {
                    'Low': {
                        'color': '#3498db',
                        'tag_class': 'tag-normal',
                        'icon': """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="m9 12 2 2 4-4"></path></svg>"""
                    },
                    'Moderate': {
                        'color': '#2ecc71',
                        'tag_class': 'tag-advisory',
                        'icon': """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 8v4"></path><path d="M12 16h.01"></path></svg>"""
                    },
                    'High': {
                        'color': '#e67e22',
                        'tag_class': 'tag-watch',
                        'icon': """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m8.5 14.5 2-2-2-2"></path><path d="m13.5 14.5 2-2-2-2"></path><circle cx="12" cy="12" r="10"></circle></svg>"""
                    },
                    'Very High': {
                        'color': '#e74c3c',
                        'tag_class': 'tag-warning',
                        'icon': """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>"""
                    }
                }
                
                risk_level = risk_data['risk_level']
                risk_info = risk_levels.get(risk_level, {
                    'color': '#7f8c8d',
                    'tag_class': 'tag-uncertain',
                    'icon': """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v.01"></path><path d="M12 8a2 2 0 0 0-2 2v2a2 2 0 0 0 4 0v-2a2 2 0 0 0-2-2Z"></path></svg>"""
                })
                
                # Main risk information display
                st.markdown(f"""
                <div class="info-section">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <span class="info-tag {risk_info['tag_class']}">{risk_info['icon']} {risk_level} Risk</span>
                        <span style="font-size: 0.9rem; color: #666;">Risk Factor: {risk_data['risk_factor']:.2f}</span>
                    </div>
                    
                    <p style="margin-top: 0.5rem; color: #555; font-size: 0.9rem;">
                        This risk assessment is based on factors like eruption history, volcano type, 
                        monitoring capability, and regional vulnerability. A higher risk factor indicates 
                        a volcano that may pose greater hazards.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Create a professional gauge visualization
                st.markdown("""
                <style>
                .risk-gauge-container {
                    width: 100%;
                    height: 20px;
                    background-color: #f1f1f1;
                    border-radius: 10px;
                    margin: 15px 0;
                    overflow: hidden;
                    position: relative;
                }
                
                .risk-gauge-fill {
                    height: 100%;
                    border-radius: 10px;
                    background: linear-gradient(90deg, #3498db 0%, #2ecc71 30%, #e67e22 60%, #e74c3c 100%);
                    transition: width 0.5s ease;
                }
                
                .risk-gauge-marker {
                    position: absolute;
                    top: -8px;
                    width: 5px;
                    height: 35px;
                    background-color: rgba(0, 0, 0, 0.7);
                    transform: translateX(-50%);
                }
                
                .risk-factor-label {
                    margin-top: 8px;
                    display: flex;
                    justify-content: space-between;
                    font-size: 0.8rem;
                    color: #666;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Calculate the position of the marker (0-100%)
                # Assuming risk factor is on a scale of 0-10
                scale_max = 10.0
                marker_position = min(100, max(0, (risk_data['risk_factor'] / scale_max) * 100))
                
                st.markdown(f"""
                <div class="info-section">
                    <h4>Risk Factor</h4>
                    <div class="risk-gauge-container">
                        <div class="risk-gauge-fill" style="width: 100%;"></div>
                        <div class="risk-gauge-marker" style="left: {marker_position}%;"></div>
                    </div>
                    <div class="risk-factor-label">
                        <span>Low</span>
                        <span>Moderate</span>
                        <span>High</span>
                        <span>Very High</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Risk factor breakdown
                st.markdown('<div class="info-section">', unsafe_allow_html=True)
                st.markdown('<h4>Risk Factor Breakdown</h4>', unsafe_allow_html=True)
                
                # Create 2x2 grid of factor cards
                st.markdown('<div class="stat-container">', unsafe_allow_html=True)
                
                # Eruption Risk
                eruption_score = risk_data.get('eruption_risk_score', 0)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{eruption_score:.1f}</div>
                    <div class="stat-label">Eruption History</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Type Risk
                type_score = risk_data.get('type_risk_score', 0)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{type_score:.1f}</div>
                    <div class="stat-label">Volcano Type</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Monitoring Risk
                monitoring_score = risk_data.get('monitoring_risk_score', 0)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{monitoring_score:.1f}</div>
                    <div class="stat-label">Monitoring</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Regional Risk
                regional_score = risk_data.get('regional_risk_score', 0)
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{regional_score:.1f}</div>
                    <div class="stat-label">Regional</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close stat container
                
                # Display last updated
                st.markdown(f"""
                <p style="margin-top: 15px; font-size: 0.8rem; color: #666; text-align: right;">
                    <em>Last updated: {risk_data['last_updated']}</em>
                </p>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close info section
                
                # Link to Risk Map - removed as requested
                # st.markdown("""
                # <div style="margin-top: 10px;">
                #     <a href="/pages/risk_map.py" target="_self" style="display: inline-flex; align-items: center; gap: 5px; text-decoration: none;">
                #         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                #         View Global Risk Heat Map
                #     </a>
                # </div>
                # """, unsafe_allow_html=True)
                
            else:
                # No risk data
                no_data_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M7.91 3h8.18a2 2 0 0 1 1.63.87l2.88 3.86a2 2 0 0 1 0 2.48l-9 12.01a2 2 0 0 1-3.24 0l-9-12.01a2 2 0 0 1 0-2.48l2.88-3.86A2 2 0 0 1 7.91 3Z"></path><path d="M12 8v4"></path><path d="M12 16h.01"></path></svg>"""
                
                st.markdown(f"""
                <div style="text-align: center; padding: 2rem 1rem;">
                    {no_data_icon}
                    <p style="margin-top: 1rem; color: #666;">No risk assessment data available for this volcano.</p>
                    <!-- Risk map link removed as requested -->
                    <!-- <a href="/pages/risk_map.py" target="_self" style="display: inline-flex; align-items: center; gap: 5px; margin-top: 1rem; text-decoration: none;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                        Visit Risk Heat Map
                    </a> -->
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Could not load risk assessment data: {str(e)}")
            
        st.markdown('</div>', unsafe_allow_html=True)  # Close info panel
        
        # Volcano Characteristics Section
        st.markdown("### Detailed Characteristics")
        try:
            # Get characteristics data for this volcano
            char_data = get_volcano_characteristics(volcano['id'])
            
            if char_data:
                with st.expander("View Detailed Characteristics", expanded=False):
                    # Create two columns for better organization
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if char_data['type']:
                            st.markdown(f"**Volcano Type:** {char_data['type']}")
                        if char_data['elevation']:
                            st.markdown(f"**Elevation:** {char_data['elevation']} m")
                        if char_data['crater_diameter_km']:
                            st.markdown(f"**Crater Diameter:** {char_data['crater_diameter_km']} km")
                        if char_data['edifice_height_m']:
                            st.markdown(f"**Edifice Height:** {char_data['edifice_height_m']} m")
                    
                    with col2:
                        if char_data['tectonic_setting']:
                            st.markdown(f"**Tectonic Setting:** {char_data['tectonic_setting']}")
                        if char_data['primary_magma_type']:
                            st.markdown(f"**Magma Type:** {char_data['primary_magma_type']}")
                        if char_data['historical_fatalities'] is not None:
                            st.markdown(f"**Historical Fatalities:** {char_data['historical_fatalities']:,}")
                        if char_data['last_eruption']:
                            st.markdown(f"**Last Eruption:** {char_data['last_eruption']}")
                    
                    # Full-width items
                    if char_data['significant_eruptions']:
                        st.markdown("#### Significant Eruptions")
                        st.markdown(char_data['significant_eruptions'])
                    
                    if char_data['geological_summary']:
                        st.markdown("#### Geological Summary")
                        st.markdown(char_data['geological_summary'])
            else:
                # If no data exists, offer to add basic characteristics
                st.info("No detailed characteristics available for this volcano.")
                
                # Offer to save basic characteristics from the volcano data
                if st.button("Save Basic Characteristics"):
                    try:
                        # Create a characteristics object from available volcano data
                        basic_char = {
                            'type': volcano.get('type'),
                            'elevation': volcano.get('elevation'),
                            'last_eruption': volcano.get('last_eruption')
                        }
                        
                        # Save to database
                        save_volcano_characteristics(
                            volcano_id=volcano['id'],
                            volcano_name=volcano['name'],
                            characteristics=basic_char
                        )
                        
                        st.success("Basic characteristics saved successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving characteristics: {str(e)}")
        except Exception as e:
            st.warning(f"Could not load volcano characteristics: {str(e)}")
        
        # Eruption History Section
        st.markdown("### Eruption History")
        try:
            # Get eruption history for this volcano
            eruption_history = get_volcano_eruption_history(volcano['id'])
            
            if eruption_history and len(eruption_history) > 0:
                with st.expander("View Eruption History", expanded=False):
                    for event in eruption_history:
                        # Header with date range
                        end_date = event['eruption_end_date'] if event['eruption_end_date'] else "Ongoing"
                        st.markdown(f"#### Eruption: {event['eruption_start_date']} to {end_date}")
                        
                        # VEI if available
                        if event['vei'] is not None:
                            vei_color = "red" if event['vei'] >= 4 else "orange" if event['vei'] >= 2 else "gray"
                            st.markdown(f"**VEI:** <span style='color:{vei_color};'>{event['vei']}</span>", unsafe_allow_html=True)
                        
                        # Two columns for details
                        col1, col2 = st.columns(2)
                        with col1:
                            if event['eruption_type']:
                                st.markdown(f"**Type:** {event['eruption_type']}")
                            if event['max_plume_height_km']:
                                st.markdown(f"**Max Plume Height:** {event['max_plume_height_km']} km")
                        
                        with col2:
                            if event['fatalities'] is not None:
                                st.markdown(f"**Fatalities:** {event['fatalities']:,}")
                            if event['economic_damage_usd'] is not None:
                                st.markdown(f"**Economic Damage:** ${event['economic_damage_usd']:,} USD")
                        
                        # Description if available
                        if event['event_description']:
                            st.markdown(f"**Description:** {event['event_description']}")
                        
                        st.markdown("---")
            else:
                st.info("No eruption history available for this volcano.")
                
                # Check if there's a last eruption date in the volcano data
                if 'last_eruption' in volcano and volcano['last_eruption'] and volcano['last_eruption'] != "Unknown":
                    # Offer to add this as an eruption event
                    if st.button("Add Last Eruption to History"):
                        try:
                            # Convert last_eruption string to a date object if possible
                            from datetime import datetime
                            
                            # Try to parse the last eruption string into a date
                            # This is a simple implementation - might need enhancement based on actual data format
                            try:
                                # Try different date formats
                                date_formats = ["%Y", "%Y-%m", "%Y-%m-%d"]
                                parsed_date = None
                                
                                for fmt in date_formats:
                                    try:
                                        parsed_date = datetime.strptime(volcano['last_eruption'], fmt).date()
                                        break
                                    except:
                                        continue
                                
                                if parsed_date:
                                    # Add eruption event
                                    add_eruption_event(
                                        volcano_id=volcano['id'],
                                        volcano_name=volcano['name'],
                                        eruption_start_date=parsed_date,
                                        eruption_data={
                                            'event_description': f"Last known eruption based on catalog data.",
                                            'data_source': "Volcano catalog"
                                        }
                                    )
                                    
                                    st.success("Eruption event added successfully!")
                                    st.rerun()
                                else:
                                    st.warning(f"Could not parse date: {volcano['last_eruption']}")
                            except Exception as e:
                                st.warning(f"Could not parse last eruption date: {str(e)}")
                        except Exception as e:
                            st.error(f"Error adding eruption event: {str(e)}")
        except Exception as e:
            st.warning(f"Could not load eruption history: {str(e)}")
        
        # Satellite Imagery Section
        st.markdown("### Satellite Imagery")
        
        # Generate Smithsonian WMS URL with high zoom for detailed view
        smithsonian_wms_url = generate_smithsonian_wms_url(
            latitude=volcano['latitude'], 
            longitude=volcano['longitude'],
            width=800,
            height=600,
            zoom_level=12  # Higher zoom for individual volcano (increased from 10 to 12)
        )
        
        # Display the Smithsonian Volcanoes of the World WMS link
        st.markdown("#### Holocene Eruptions Map")
        
        # Show the Smithsonian WMS map in an iframe for direct viewing
        st.markdown(f"""
        <div style="border:1px solid #ddd; padding:5px; border-radius:5px; margin-bottom:10px;">
            <iframe src="{smithsonian_wms_url}" width="100%" height="400" frameborder="0"></iframe>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"[Open in New Tab]({smithsonian_wms_url})")
        st.markdown("*Data source: Smithsonian Global Volcanism Program*")
        
        # Add button to save the Smithsonian WMS link to the database
        if st.button("Save Smithsonian WMS Map to Database"):
            try:
                # Current date for the database record
                from datetime import date
                today = date.today()
                
                # Add to satellite imagery database
                add_satellite_image(
                    volcano_id=volcano['id'],
                    volcano_name=volcano['name'],
                    image_type="Holocene Eruptions",
                    image_url=smithsonian_wms_url,
                    provider="Smithsonian VOTW/SPREP Geoserver",
                    capture_date=today,
                    description="Smithsonian Volcanoes of the World Holocene Eruptions Map"
                )
                
                st.success("Smithsonian WMS Map added to image database!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding Smithsonian WMS Map to database: {str(e)}")
                
        st.markdown("---")
        
        try:
            # Get satellite imagery for this volcano
            satellite_images = get_volcano_satellite_images(volcano['id'])
            
            if satellite_images and len(satellite_images) > 0:
                with st.expander("View Satellite Imagery", expanded=False):
                    # Group images by type
                    image_types = {}
                    for img in satellite_images:
                        if img['image_type'] not in image_types:
                            image_types[img['image_type']] = []
                        image_types[img['image_type']].append(img)
                    
                    # Display each type in its own section
                    for img_type, images in image_types.items():
                        st.markdown(f"#### {img_type} Images")
                        
                        for img in images:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                if img['description']:
                                    link_text = img['description']
                                else:
                                    # Construct a description from available data
                                    date_str = f" ({img['capture_date']})" if img['capture_date'] else ""
                                    provider_str = f" from {img['provider']}" if img['provider'] else ""
                                    link_text = f"{img['image_type']} Image{date_str}{provider_str}"
                                
                                st.markdown(f"[{link_text}]({img['image_url']})")
                            
                            with col2:
                                if img['capture_date']:
                                    st.markdown(f"*{img['capture_date']}*")
            else:
                st.info("No satellite imagery links available for this volcano.")
                
                # Offer to add InSAR image if available
                if insar_url:
                    if st.button("Add InSAR Link to Image Database"):
                        try:
                            # Add to satellite imagery database
                            add_satellite_image(
                                volcano_id=volcano['id'],
                                volcano_name=volcano['name'],
                                image_type="InSAR",
                                image_url=insar_url,
                                provider="OpenVolcano",
                                description="InSAR deformation map"
                            )
                            
                            st.success("InSAR link added to image database!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding satellite image: {str(e)}")
        except Exception as e:
            st.warning(f"Could not load satellite imagery: {str(e)}")
        
        # WOVOdat Monitoring Data
        st.markdown("### WOVOdat Monitoring Data")
        with st.expander("View Monitoring Data from WOVOdat", expanded=False):
            with st.spinner("Loading WOVOdat data..."):
                try:
                    # Get WOVOdat volcano data
                    wovodat_data = get_wovodat_volcano_data(volcano['name'])
                    
                    if wovodat_data:
                        # Check if it's an Icelandic volcano or standard WOVOdat
                        if wovodat_data.get('is_iceland', False):
                            # Display Iceland-specific information
                            st.markdown("### Icelandic Volcano Monitoring")
                            st.markdown(f"[Icelandic Met Office Volcanic Monitoring]({wovodat_data['wovodat_url']})")
                            
                            if 'volcano_discovery_url' in wovodat_data:
                                st.markdown(f"[VolcanoDiscovery - Reykjanes]({wovodat_data['volcano_discovery_url']})")
                            
                            if 'icelandic_met_url' in wovodat_data:
                                st.markdown(f"[Latest Magma Movement - IMO]({wovodat_data['icelandic_met_url']})")
                                
                            if 'special_note' in wovodat_data:
                                st.info(wovodat_data['special_note'])
                        else:
                            # Standard WOVOdat link
                            st.markdown(f"[View on WOVOdat]({wovodat_data['wovodat_url']})")
                        
                        # Get monitoring status
                        monitoring_status = get_volcano_monitoring_status(volcano['name'])
                        
                        # Display monitoring status
                        st.markdown("#### Monitoring Status")
                        st.markdown(monitoring_status['description'])
                        
                        # Show source if available
                        if 'source' in monitoring_status:
                            st.caption(f"Source: {monitoring_status['source']}")
                        
                        # Create tabs for different types of monitoring data
                        if wovodat_data.get('is_iceland', False):
                            # Iceland-specific tabs
                            iceland_tab1, iceland_tab2, iceland_tab3, iceland_tab4 = st.tabs([
                                "Ground Deformation", "Gas Emissions", 
                                "Magma Movement", "Live Monitoring"
                            ])
                            
                            with iceland_tab1:
                                # InSAR/GPS data from Icelandic Met Office
                                insar_url = get_wovodat_insar_url(volcano['name'])
                                if insar_url:
                                    st.markdown(f"[View Ground Deformation Data]({insar_url})")
                                    st.markdown("The Icelandic Meteorological Office uses GPS and InSAR data to monitor ground deformation at Icelandic volcanoes. This helps detect magma movement and potential eruption precursors.")
                                    st.markdown("![InSAR Example](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/thumbnails/image/Mauna%20Loa%20interferogram.jpg)")
                                    st.caption("Example of InSAR interferogram showing ground deformation")
                                
                            with iceland_tab2:
                                # SO2 data from Icelandic Met Office
                                so2_data = get_wovodat_so2_data(volcano['name'])
                                if so2_data:
                                    st.markdown(f"[View Gas Emission Data]({so2_data['url']})")
                                    st.markdown(so2_data['description'])
                                    if 'notes' in so2_data:
                                        st.markdown(so2_data['notes'])
                            
                            with iceland_tab3:
                                # Magma movement data
                                lava_data = get_lava_injection_data(volcano['name'])
                                if lava_data:
                                    st.markdown(f"[View Magma Movement/Eruption Data]({lava_data['url']})")
                                    st.markdown(lava_data['description'])
                                    
                                    # Special notes for Reykjanes
                                    if volcano['name'] == "Reykjanes" and 'notes' in lava_data:
                                        st.info(lava_data['notes'])
                                    
                                    if 'volcano_discovery_url' in lava_data:
                                        st.markdown(f"[VolcanoDiscovery - Additional Data]({lava_data['volcano_discovery_url']})")
                            
                            with iceland_tab4:
                                # Live monitoring from Icelandic Met Office
                                st.markdown("### Live Monitoring Data")
                                st.markdown("[Live Earthquake Data from Icelandic Met Office](https://en.vedur.is/earthquakes-and-volcanism/earthquakes)")
                                st.markdown("[Live Webcams of Volcanic Areas](https://www.ruv.is/frett/2023/03/30/live-feed-from-the-eruption)")
                                
                                # Embed an iframe with the IMO earthquake map
                                st.markdown("""
                                <iframe src="https://en.vedur.is/earthquakes-and-volcanism/earthquakes/reykjanespeninsula" 
                                width="100%" height="600" frameborder="0"></iframe>
                                """, unsafe_allow_html=True)
                        else:
                            # Standard WOVOdat tabs
                            wovodat_tab1, wovodat_tab2, wovodat_tab3 = st.tabs(["InSAR Data", "SO2 Emissions", "Lava Injection"])
                            
                            with wovodat_tab1:
                                # InSAR data from WOVOdat
                                insar_wovodat_url = get_wovodat_insar_url(volcano['name'])
                                if insar_wovodat_url:
                                    st.markdown(f"[View InSAR Data on WOVOdat]({insar_wovodat_url})")
                                    st.markdown("InSAR (Interferometric Synthetic Aperture Radar) data shows ground deformation, which can indicate magma movement beneath the volcano.")
                                    st.markdown("![InSAR Example](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/thumbnails/image/Mauna%20Loa%20interferogram.jpg)")
                                    st.caption("Example of InSAR interferogram showing ground deformation")
                                else:
                                    st.info("No InSAR data available for this volcano in WOVOdat.")
                            
                            with wovodat_tab2:
                                # SO2 data
                                so2_data = get_wovodat_so2_data(volcano['name'])
                                if so2_data:
                                    st.markdown(f"[View SO2 Emission Data on WOVOdat]({so2_data['url']})")
                                    st.markdown(so2_data['description'])
                                    st.markdown("SO2 (sulfur dioxide) is a significant gas released during volcanic eruptions. Monitoring SO2 levels helps track volcanic activity and potential environmental impacts.")
                                else:
                                    st.info("No SO2 emission data available for this volcano in WOVOdat.")
                            
                            with wovodat_tab3:
                                # Lava injection data
                                lava_data = get_lava_injection_data(volcano['name'])
                                if lava_data:
                                    st.markdown(f"[View Eruption/Lava Data on WOVOdat]({lava_data['url']})")
                                    st.markdown(lava_data['description'])
                                    st.markdown("Lava injection and eruption data provides information about the volume, composition, and behavior of magma during volcanic activity.")
                                else:
                                    st.info("No lava injection/eruption data available for this volcano in WOVOdat.")
                    else:
                        st.info("This volcano does not have monitoring data in WOVOdat.")
                        st.markdown("[Visit WOVOdat](https://wovodat.org/gvmid/index.php?type=world) to explore other monitored volcanoes.")
                except Exception as e:
                    st.warning(f"Could not load WOVOdat data: {str(e)}")
        
        # Climate Links Information
        st.markdown("### Climate Links Information")
        with st.expander("View Educational Information", expanded=False):
            with st.spinner("Loading educational information..."):
                try:
                    # Simplified climate links information
                    st.markdown("For educational information about volcanoes, check out the Climate Links website.")
                    st.markdown("[Visit Climate Links Volcanoes Page](https://climatelinks.weebly.com/volcanoes.html)")
                except Exception as e:
                    st.warning(f"Could not load educational information: {str(e)}")
    else:
        st.info("Select a volcano on the map to view details")

# Function to handle volcano selection from the map
def handle_volcano_selection():
    # This function works with streamlit_folium's callbacks
    # That's handled in the map_utils.py file
    pass

# Create a placeholder for map click events
volcano_selector = st.empty()

# Manual volcano selection (as an alternative to map clicks)
st.markdown("### Can't use the map? Select a volcano from the list:")
selected_volcano_name = st.selectbox(
    "Choose a volcano",
    options=filtered_df['name'].tolist(),
    index=None,
    key="volcano_selector"
)

if selected_volcano_name:
    selected_volcano_data = filtered_df[filtered_df['name'] == selected_volcano_name].iloc[0].to_dict()
    st.session_state.selected_volcano = selected_volcano_data
    st.rerun()
