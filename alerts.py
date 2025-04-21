"""
Volcano early warning alert system for the Volcano Monitoring Dashboard.

This module provides functionality for sending alerts to subscribers via email and SMS
when volcanic activity changes or reaches certain thresholds.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import requests

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Constants
ALERT_LEVELS = ["Normal", "Advisory", "Watch", "Warning"]
ALERT_FREQUENCIES = ["Immediate", "Daily", "Weekly"]
DEFAULT_FROM_EMAIL = "alerts@volcano-dashboard.com"

# Database Models
class Subscriber(Base):
    """Subscriber model for users who want to receive volcano alerts."""
    __tablename__ = "subscribers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    active = Column(Boolean, default=True)
    subscription_level = Column(String(20), default="free")  # free, basic, premium
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default={})
    
    alerts = relationship("SubscriberAlert", back_populates="subscriber")
    volcanoes = relationship("SubscriberVolcano", back_populates="subscriber")
    
    def __repr__(self):
        return f"<Subscriber {self.name}, email: {self.email}, phone: {self.phone}>"


class SubscriberVolcano(Base):
    """Association model linking subscribers to volcanoes they're interested in."""
    __tablename__ = "subscriber_volcanoes"
    
    id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"))
    volcano_id = Column(String(50), nullable=False)
    alert_threshold = Column(String(20), default="Warning")  # Minimum level to send alert
    alert_frequency = Column(String(20), default="Immediate")
    
    subscriber = relationship("Subscriber", back_populates="volcanoes")
    
    def __repr__(self):
        return f"<SubscriberVolcano {self.subscriber_id}, volcano_id: {self.volcano_id}>"


class SubscriberAlert(Base):
    """Record of alerts sent to subscribers."""
    __tablename__ = "subscriber_alerts"
    
    id = Column(Integer, primary_key=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"))
    volcano_id = Column(String(50), nullable=False)
    alert_level = Column(String(20), nullable=False)
    alert_message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered = Column(Boolean, default=False)
    delivery_method = Column(String(20), nullable=False)  # email, sms
    
    subscriber = relationship("Subscriber", back_populates="alerts")
    
    def __repr__(self):
        return f"<SubscriberAlert {self.subscriber_id}, volcano: {self.volcano_id}, level: {self.alert_level}>"


# Initialize database
def init_db():
    """Initialize the database schema."""
    Base.metadata.create_all(engine)


# Email functionality
def send_email_alert(recipient_email: str, subject: str, message: str) -> bool:
    """
    Send an email alert to a subscriber.
    
    Args:
        recipient_email (str): Email address to send to
        subject (str): Email subject line
        message (str): Email body content
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # In a production environment, you would configure a real SMTP server here
        # For now, we'll just log the email that would be sent
        logger.info(f"EMAIL ALERT to {recipient_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Message: {message}")
        
        # Return success for now - in production, we'd check the actual SMTP response
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        return False


# SMS functionality
def send_sms_alert(recipient_phone: str, message: str) -> bool:
    """
    Send an SMS alert to a subscriber via Twilio.
    
    Args:
        recipient_phone (str): Phone number to send to
        message (str): SMS message content
        
    Returns:
        bool: True if SMS was sent successfully, False otherwise
    """
    # Check if Twilio credentials are available
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_phone = os.environ.get("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, from_phone]):
        logger.warning("Twilio credentials not found. SMS notification simulated.")
        logger.info(f"SMS ALERT to {recipient_phone}: {message}")
        return False
    
    try:
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        
        twilio_message = client.messages.create(
            body=message,
            from_=from_phone,
            to=recipient_phone
        )
        
        logger.info(f"Sent SMS to {recipient_phone}, SID: {twilio_message.sid}")
        return True
    except ImportError:
        logger.error("Twilio library not installed. Use 'pip install twilio'.")
        return False
    except Exception as e:
        logger.error(f"Failed to send SMS to {recipient_phone}: {str(e)}")
        return False


# Alert processing functions
def send_volcano_alert(volcano_data: Dict[str, Any], alert_level: str) -> List[Dict]:
    """
    Send alerts to subscribers for a specific volcano based on alert level.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano information
        alert_level (str): Current alert level for the volcano
        
    Returns:
        List[Dict]: List of alert records that were sent
    """
    volcano_id = volcano_data.get("id", "unknown")
    volcano_name = volcano_data.get("name", "Unknown Volcano")
    
    session = Session()
    sent_alerts = []
    
    try:
        # Find all subscribers who should receive this alert
        subscribers_query = session.query(Subscriber, SubscriberVolcano).join(
            SubscriberVolcano, 
            Subscriber.id == SubscriberVolcano.subscriber_id
        ).filter(
            SubscriberVolcano.volcano_id == volcano_id,
            Subscriber.active == True,
            # Only send alerts for the appropriate threshold level
            sa.case(
                {level: i for i, level in enumerate(ALERT_LEVELS)}
            )[SubscriberVolcano.alert_threshold] <= 
            sa.case(
                {level: i for i, level in enumerate(ALERT_LEVELS)}
            )[alert_level]
        )
        
        for subscriber, subscription in subscribers_query:
            # Prepare alert message
            alert_message = f"VOLCANO ALERT: {volcano_name} is now at {alert_level} level. "
            
            if alert_level == "Warning":
                alert_message += "Immediate action may be required. Check dashboard for details."
            elif alert_level == "Watch":
                alert_message += "Be prepared for possible evacuation. Monitor situation closely."
            elif alert_level == "Advisory":
                alert_message += "Be aware of increased volcanic activity."
            else:
                alert_message += "Activity has returned to normal levels."
            
            # Add current time
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            alert_message += f" (Alert time: {current_time})"
            
            # Send email alert if email is available
            email_delivered = False
            if subscriber.email:
                subject = f"Volcano Alert: {volcano_name} - {alert_level}"
                email_delivered = send_email_alert(subscriber.email, subject, alert_message)
                
                # Record the alert
                email_alert = SubscriberAlert(
                    subscriber_id=subscriber.id,
                    volcano_id=volcano_id,
                    alert_level=alert_level,
                    alert_message=alert_message,
                    delivered=email_delivered,
                    delivery_method="email"
                )
                session.add(email_alert)
                sent_alerts.append({
                    "subscriber": subscriber.name,
                    "method": "email",
                    "delivered": email_delivered
                })
            
            # Send SMS alert if phone is available and subscriber level allows it
            sms_delivered = False
            if subscriber.phone and subscriber.subscription_level in ["basic", "premium"]:
                sms_delivered = send_sms_alert(subscriber.phone, alert_message)
                
                # Record the alert
                sms_alert = SubscriberAlert(
                    subscriber_id=subscriber.id,
                    volcano_id=volcano_id,
                    alert_level=alert_level,
                    alert_message=alert_message,
                    delivered=sms_delivered,
                    delivery_method="sms"
                )
                session.add(sms_alert)
                sent_alerts.append({
                    "subscriber": subscriber.name,
                    "method": "sms",
                    "delivered": sms_delivered
                })
        
        session.commit()
        return sent_alerts
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error sending volcano alerts: {str(e)}")
        return []
    
    finally:
        session.close()


def check_alert_level_changes(volcano_data: Dict[str, Any], 
                              previous_level: Optional[str] = None) -> Optional[List[Dict]]:
    """
    Check if a volcano's alert level has changed and send alerts if needed.
    
    Args:
        volcano_data (Dict[str, Any]): Dictionary containing volcano data
        previous_level (Optional[str]): Previous alert level if known
        
    Returns:
        Optional[List[Dict]]: List of sent alerts, or None if no alerts were sent
    """
    volcano_id = volcano_data.get("id", "unknown")
    current_level = volcano_data.get("alert_level")
    
    # Skip if no alert level is set
    if not current_level:
        return None
    
    # If no previous level is provided, check the database
    if previous_level is None:
        session = Session()
        try:
            # Get the most recent alert for this volcano
            latest_alert = session.query(SubscriberAlert).filter(
                SubscriberAlert.volcano_id == volcano_id
            ).order_by(
                SubscriberAlert.sent_at.desc()
            ).first()
            
            if latest_alert:
                previous_level = latest_alert.alert_level
        finally:
            session.close()
    
    # If the level has changed (or previous is unknown), send alerts
    if previous_level != current_level:
        return send_volcano_alert(volcano_data, current_level)
    
    return None


def subscribe_to_volcano(name: str, email: str, phone: str, 
                         volcano_id: str, subscription_level: str = "free", 
                         alert_threshold: str = "Warning",
                         alert_frequency: str = "Immediate") -> Tuple[bool, str]:
    """
    Subscribe a user to volcano alerts.
    
    Args:
        name (str): Subscriber's name
        email (str): Subscriber's email
        phone (str): Subscriber's phone number (optional for free tier)
        volcano_id (str): Volcano ID to subscribe to
        subscription_level (str): Subscription level (free, basic, premium)
        alert_threshold (str): Minimum alert level to notify about
        alert_frequency (str): How frequently to send alerts
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    session = Session()
    
    try:
        # Check if subscriber already exists
        subscriber = session.query(Subscriber).filter(
            (Subscriber.email == email) | 
            ((Subscriber.phone == phone) if phone else False)
        ).first()
        
        if not subscriber:
            # Create new subscriber
            subscriber = Subscriber(
                name=name,
                email=email,
                phone=phone,
                subscription_level=subscription_level
            )
            session.add(subscriber)
            session.flush()  # Get the ID without committing
        
        # Check if already subscribed to this volcano
        existing_subscription = session.query(SubscriberVolcano).filter(
            SubscriberVolcano.subscriber_id == subscriber.id,
            SubscriberVolcano.volcano_id == volcano_id
        ).first()
        
        if existing_subscription:
            # Update existing subscription
            existing_subscription.alert_threshold = alert_threshold
            existing_subscription.alert_frequency = alert_frequency
            message = "Subscription updated successfully."
        else:
            # Create new subscription
            subscription = SubscriberVolcano(
                subscriber_id=subscriber.id,
                volcano_id=volcano_id,
                alert_threshold=alert_threshold,
                alert_frequency=alert_frequency
            )
            session.add(subscription)
            message = "Subscribed successfully."
        
        session.commit()
        return True, message
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error subscribing to volcano: {str(e)}")
        return False, f"Subscription failed: {str(e)}"
    
    finally:
        session.close()


def get_subscriber_volcanoes(email: str = None, phone: str = None) -> List[Dict]:
    """
    Get all volcanoes a subscriber is monitoring.
    
    Args:
        email (str, optional): Subscriber's email address
        phone (str, optional): Subscriber's phone number
        
    Returns:
        List[Dict]: List of volcano subscriptions
    """
    if not email and not phone:
        return []
    
    session = Session()
    
    try:
        # Find the subscriber
        query_conditions = []
        if email:
            query_conditions.append(Subscriber.email == email)
        if phone:
            query_conditions.append(Subscriber.phone == phone)
            
        subscriber = session.query(Subscriber).filter(sa.or_(*query_conditions)).first()
        
        if not subscriber:
            return []
        
        # Get all volcano subscriptions
        subscriptions = session.query(SubscriberVolcano).filter(
            SubscriberVolcano.subscriber_id == subscriber.id
        ).all()
        
        # Format the results
        result = []
        for sub in subscriptions:
            result.append({
                "volcano_id": sub.volcano_id,
                "alert_threshold": sub.alert_threshold,
                "alert_frequency": sub.alert_frequency
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting subscriber volcanoes: {str(e)}")
        return []
    
    finally:
        session.close()


def unsubscribe_from_volcano(email: str, volcano_id: str) -> Tuple[bool, str]:
    """
    Unsubscribe from volcano alerts.
    
    Args:
        email (str): Subscriber's email address
        volcano_id (str): Volcano ID to unsubscribe from
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    session = Session()
    
    try:
        # Find the subscriber
        subscriber = session.query(Subscriber).filter(Subscriber.email == email).first()
        
        if not subscriber:
            return False, "Subscriber not found."
        
        # Find the subscription
        subscription = session.query(SubscriberVolcano).filter(
            SubscriberVolcano.subscriber_id == subscriber.id,
            SubscriberVolcano.volcano_id == volcano_id
        ).first()
        
        if not subscription:
            return False, "No active subscription found for this volcano."
        
        # Delete the subscription
        session.delete(subscription)
        session.commit()
        
        return True, "Unsubscribed successfully."
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error unsubscribing from volcano: {str(e)}")
        return False, f"Unsubscribe failed: {str(e)}"
    
    finally:
        session.close()


def get_subscription_plans() -> List[Dict]:
    """
    Get available subscription plans for volcano alerts.
    
    Returns:
        List[Dict]: List of subscription plans and features
    """
    return [
        {
            "name": "Free",
            "price": "$0/month",
            "features": [
                "Email alerts only",
                "Maximum of 3 volcano subscriptions",
                "Daily alert summaries",
                "Warning level alerts only"
            ]
        },
        {
            "name": "Basic",
            "price": "$4.99/month",
            "features": [
                "Email and SMS alerts",
                "Up to 10 volcano subscriptions",
                "Alert threshold customization",
                "Daily and immediate notifications",
                "Watch level and above alerts"
            ]
        },
        {
            "name": "Premium",
            "price": "$9.99/month",
            "features": [
                "Email and SMS alerts",
                "Unlimited volcano subscriptions",
                "Custom alert thresholds",
                "Real-time notifications",
                "All alert levels",
                "API access to alert data",
                "Weekly volcano risk assessment reports"
            ]
        }
    ]