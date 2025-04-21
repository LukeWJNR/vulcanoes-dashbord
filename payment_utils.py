"""
Payment utilities for the Volcano Monitoring Dashboard.

This module handles PayPal integration, subscription management, and
payment processing for premium features like the Eruption Simulator.
"""

import os
import json
import time
import hashlib
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

import streamlit as st
from utils.db_utils import execute_query, fetch_one, fetch_all

# Initialize database tables if they don't exist
def initialize_payment_tables():
    """
    Create the necessary database tables for handling payments and subscriptions
    """
    # Create payments table
    execute_query("""
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        payment_id TEXT UNIQUE,
        amount NUMERIC(10, 2) NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    )
    """)

    # Create subscriptions table
    execute_query("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        subscription_id TEXT UNIQUE,
        plan_type TEXT NOT NULL,
        status TEXT NOT NULL,
        start_date TIMESTAMP NOT NULL,
        end_date TIMESTAMP,
        trial_end_date TIMESTAMP,
        last_payment_id INTEGER REFERENCES payments(id),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB
    )
    """)

    # Create feature access table
    execute_query("""
    CREATE TABLE IF NOT EXISTS feature_access (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        feature_name TEXT NOT NULL,
        access_level TEXT NOT NULL,
        granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        metadata JSONB,
        UNIQUE(user_id, feature_name)
    )
    """)

def get_session_id() -> str:
    """
    Get or create a unique session ID for the current user

    Returns:
        str: The session ID
    """
    if 'user_id' not in st.session_state:
        # In a real application, this would be a proper user ID from authentication
        # For demo purposes, we create a simple session-based ID
        current_time = str(time.time())
        browser_info = json.dumps(st.get_user_info(), default=str)
        unique_string = f"{current_time}_{browser_info}"
        session_id = hashlib.md5(unique_string.encode()).hexdigest()
        st.session_state.user_id = session_id

    return st.session_state.user_id

def has_active_subscription(user_id: str) -> bool:
    """
    Check if the user has an active subscription or free trial

    Args:
        user_id (str): The user ID to check

    Returns:
        bool: True if the user has an active subscription, False otherwise
    """
    # Check for active subscription
    query = """
    SELECT * FROM subscriptions 
    WHERE user_id = %s 
    AND status = 'active' 
    AND (end_date IS NULL OR end_date > NOW())
    """

    result = fetch_one(query, (user_id,))

    if result:
        return True

    # Check for active trial
    query = """
    SELECT * FROM subscriptions 
    WHERE user_id = %s 
    AND status = 'trial' 
    AND trial_end_date > NOW()
    """

    result = fetch_one(query, (user_id,))

    return result is not None

def start_free_trial(user_id: str, days: int = 7) -> bool:
    """
    Start a free trial for the user

    Args:
        user_id (str): The user ID
        days (int): Number of trial days

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if user already has a subscription or trial
    if has_active_subscription(user_id):
        return False

    # Check if user has had a trial before
    query = "SELECT * FROM subscriptions WHERE user_id = %s AND status = 'trial'"
    result = fetch_one(query, (user_id,))

    if result:
        # Already had a trial
        return False

    # Create trial subscription
    start_date = datetime.now()
    trial_end_date = start_date + timedelta(days=days)

    query = """
    INSERT INTO subscriptions (
        user_id, subscription_id, plan_type, status, 
        start_date, trial_end_date, metadata
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s
    )
    """

    # Generate a unique subscription ID
    subscription_id = f"trial_{user_id}_{int(time.time())}"

    # Insert the trial subscription
    try:
        execute_query(
            query, 
            (
                user_id, 
                subscription_id, 
                'premium', 
                'trial', 
                start_date, 
                trial_end_date,
                json.dumps({"source": "free_trial"})
            )
        )

        # Grant feature access
        grant_feature_access(user_id, 'eruption_simulator', 'premium', trial_end_date)

        return True
    except Exception as e:
        print(f"Error starting free trial: {e}")
        return False

def grant_feature_access(user_id: str, feature_name: str, access_level: str, expires_at: Optional[datetime] = None) -> bool:
    """
    Grant access to a feature for a user

    Args:
        user_id (str): The user ID
        feature_name (str): Name of the feature
        access_level (str): Level of access (e.g., 'basic', 'premium')
        expires_at (datetime, optional): When access expires

    Returns:
        bool: True if successful, False otherwise
    """
    query = """
    INSERT INTO feature_access (
        user_id, feature_name, access_level, expires_at
    ) VALUES (
        %s, %s, %s, %s
    )
    ON CONFLICT (user_id, feature_name) DO UPDATE
    SET access_level = EXCLUDED.access_level,
        expires_at = EXCLUDED.expires_at,
        granted_at = CURRENT_TIMESTAMP
    """

    try:
        execute_query(query, (user_id, feature_name, access_level, expires_at))
        return True
    except Exception as e:
        print(f"Error granting feature access: {e}")
        return False

def has_feature_access(user_id: str, feature_name: str, required_level: str = 'basic') -> bool:
    """
    Check if a user has access to a specific feature at the required level

    Args:
        user_id (str): The user ID
        feature_name (str): Name of the feature
        required_level (str): Minimum required access level

    Returns:
        bool: True if the user has access, False otherwise
    """
    # Define access level hierarchy
    access_levels = {
        'basic': 0,
        'standard': 1,
        'premium': 2
    }

    query = """
    SELECT access_level, expires_at FROM feature_access
    WHERE user_id = %s AND feature_name = %s
    """

    result = fetch_one(query, (user_id, feature_name))

    if not result:
        return False

    access_level, expires_at = result

    # Check if access has expired
    if expires_at and expires_at < datetime.now():
        return False

    # Check if access level is sufficient
    return access_levels.get(access_level, -1) >= access_levels.get(required_level, 0)

def get_subscription_details(user_id: str) -> Dict[str, Any]:
    """
    Get subscription details for a user

    Args:
        user_id (str): The user ID

    Returns:
        Dict[str, Any]: Subscription details
    """
    query = """
    SELECT * FROM subscriptions
    WHERE user_id = %s
    ORDER BY created_at DESC
    LIMIT 1
    """

    result = fetch_one(query, (user_id,))

    if not result:
        return {
            'has_subscription': False,
            'status': 'none',
            'plan_type': None,
            'is_trial': False,
            'days_remaining': 0
        }

    # Convert SQL result to dictionary
    subscription = dict(zip(
        ['id', 'user_id', 'subscription_id', 'plan_type', 'status', 
         'start_date', 'end_date', 'trial_end_date', 'last_payment_id', 
         'created_at', 'metadata'],
        result
    ))

    # Calculate days remaining
    days_remaining = 0
    current_date = datetime.now()

    if subscription['status'] == 'trial' and subscription['trial_end_date']:
        if subscription['trial_end_date'] > current_date:
            days_remaining = (subscription['trial_end_date'] - current_date).days
    elif subscription['status'] == 'active' and subscription['end_date']:
        if subscription['end_date'] > current_date:
            days_remaining = (subscription['end_date'] - current_date).days

    return {
        'has_subscription': subscription['status'] in ['active', 'trial'],
        'status': subscription['status'],
        'plan_type': subscription['plan_type'],
        'is_trial': subscription['status'] == 'trial',
        'days_remaining': days_remaining,
        'start_date': subscription['start_date'],
        'end_date': subscription['end_date'] if subscription['status'] != 'trial' else subscription['trial_end_date']
    }

def create_paypal_button_html(item_name: str, amount: float, currency: str = 'USD') -> str:
    """
    Create HTML for a PayPal payment button

    Args:
        item_name (str): Name of the item being purchased
        amount (float): Amount to charge
        currency (str): Currency code

    Returns:
        str: HTML for the PayPal button
    """
    # In a real application, this would integrate with PayPal's API
    # For demo purposes, we're creating a simple button

    # Clean the item name for URL
    clean_item_name = item_name.replace(' ', '%20')

    button_html = f"""
    <form action="https://www.paypal.com/cgi-bin/webscr" method="post" target="_blank">
        <input type="hidden" name="cmd" value="_xclick">
        <input type="hidden" name="business" value="paypal@volcanomonitor.com">
        <input type="hidden" name="item_name" value="{item_name}">
        <input type="hidden" name="amount" value="{amount}">
        <input type="hidden" name="currency_code" value="{currency}">
        <input type="hidden" name="return" value="https://volcano-dashboard.replit.app/payment_success">
        <input type="hidden" name="cancel_return" value="https://volcano-dashboard.replit.app/payment_cancel">

        <button type="submit" 
            style="background-color:#0070BA; color:white; padding:10px 15px; 
                   border-radius:5px; border:none; font-weight:bold; cursor:pointer;
                   display:flex; align-items:center; gap:8px">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                <path d="M20.067 8.478c.492.88.556 2.014.3 3.327-.74 3.806-3.276 5.12-6.514 5.12h-.5a.805.805 0 0 0-.794.68l-.04.22-.63 4.023-.03.143a.804.804 0 0 1-.794.679h-2.52c-.092 0-.175-.043-.232-.144a.39.39 0 0 1-.035-.263l.955-6.055-.03.199h1.69l.56-3.563.93-5.9a.42.42 0 0 1 .415-.354h6.95c.18 0 .355.064.491.206a.69.69 0 0 1 .206.541c0 .045-.007.089-.017.134l-.526 1.007" fill="#253B80"></path>
                <path d="M9.118 7.655a.347.347 0 0 1 .348-.298h4.374c.5 0 .966.073 1.39.22-.683-3.292-3.71-4.428-6.803-4.428H4.07c-.368 0-.682.27-.739.635L.084 18.04a.437.437 0 0 0 .432.504h3.154l.789-5.003 1.07-6.798.032-.088" fill="#179BD7"></path>
            </svg>
            Pay with PayPal
        </button>
    </form>
    """

    return button_html

def display_subscription_options():
    """
    Display subscription options to the user
    """
    st.markdown("### Subscription Options")

    subscription_plans = get_subscription_plans()
    for plan in subscription_plans:
        st.markdown(f"#### {plan['name']}")
        st.markdown(f"{plan['price']}")
        for feature in plan['features']:
            st.markdown(f"- {feature}")
        if plan['price'] != "Contact us":
            st.markdown(create_paypal_button_html(plan['name'] + " Subscription", float(plan['price'].replace('$', '').replace('/month', '').replace('/year', '')), currency='USD'), unsafe_allow_html=True)
        else:
            st.markdown("Please contact us for pricing and details.")
        st.markdown("---")



    # Free trial option
    user_id = get_session_id()
    subscription_details = get_subscription_details(user_id)

    if not subscription_details['has_subscription']:
        st.markdown("#### Try Premium Free")
        st.markdown("Experience all premium features free for 7 days!")

        if st.button("Start 7-Day Free Trial", type="primary"):
            success = start_free_trial(user_id)
            if success:
                st.success("Your free trial has started! Enjoy premium features for the next 7 days.")
                st.rerun()
            else:
                st.error("Unable to start free trial. You may have had a trial previously.")
    else:
        if subscription_details['is_trial']:
            st.info(f"You are currently on a free trial. {subscription_details['days_remaining']} days remaining.")
        else:
            st.success(f"You have an active {subscription_details['plan_type']} subscription.")


def get_subscription_plans() -> List[Dict]:
    """
    Get available subscription plans for volcano alerts.

    Returns:
        List[Dict]: List of subscription plans and features
    """
    return [
        {
            "name": "Community",
            "price": "$0/month",
            "features": [
                "Email alerts for critical warnings",
                "Monitor up to 5 volcanoes",
                "Daily alert summaries",
                "Basic gas emission alerts",
                "Basic earthquake notifications",
                "Access to public risk maps"
            ]
        },
        {
            "name": "Observer",
            "price": "$3.99/month",
            "features": [
                "Email and SMS alerts",
                "Monitor up to 15 volcanoes",
                "Custom alert thresholds",
                "Hourly updates for monitored volcanoes",
                "Detailed gas concentration tracking",
                "Seismic activity monitoring",
                "InSAR deformation alerts",
                "48-hour prediction warnings",
                "Mobile app access"
            ]
        },
        {
            "name": "Researcher",
            "price": "$7.99/month",
            "features": [
                "All Observer features",
                "Unlimited volcano monitoring",
                "Real-time alerts and notifications",
                "Advanced gas composition analysis",
                "Strain and deformation modeling",
                "Historical eruption patterns",
                "Custom API access",
                "Downloadable scientific data",
                "Weekly risk assessment reports",
                "Priority alert delivery",
                "Collaboration tools for teams"
            ]
        },
        {
            "name": "Institution",
            "price": "Contact us",
            "features": [
                "All Researcher features",
                "Custom deployment options",
                "Dedicated support channel",
                "Training and workshops",
                "Custom integration options",
                "White-label solutions",
                "Multi-user management",
                "Advanced analytics dashboard",
                "Raw data access",
                "Custom reporting tools"
            ]
        }
    ]