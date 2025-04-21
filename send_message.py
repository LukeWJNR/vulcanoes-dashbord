import os

from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")


def send_twilio_message(to_phone_number: str, message: str) -> bool:
    """
    Send an SMS message using Twilio.
    
    Args:
        to_phone_number (str): The recipient's phone number including country code
        message (str): The SMS message to send
        
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    # Check if Twilio credentials are available
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("Twilio credentials not configured. Cannot send SMS.")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Sending the SMS message
        message = client.messages.create(
            body=message, from_=TWILIO_PHONE_NUMBER, to=to_phone_number
        )

        print(f"Message sent with SID: {message.sid}")
        return True
    
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return False


if __name__ == "__main__":
    # Example usage
    recipient = "+1234567890"  # Replace with an actual phone number
    msg = "Test message from Volcano Dashboard Alert System"
    
    success = send_twilio_message(recipient, msg)
    if success:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")