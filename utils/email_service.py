import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from utils.database import get_youth_members, get_email_recipients, get_departments
import streamlit as st

def send_birthday_email(recipients, subject, body):
    """Send email using SMTP"""
    try:
        # Get email credentials from Streamlit secrets
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]  # Using 465 for SSL
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))

        # Create secure SSL/TLS context
        context = ssl.create_default_context()

        # Connect using SSL
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            # Login
            server.login(sender_email, sender_password)
            # Send email
            server.send_message(message)
            
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

def format_birthday_email(birthday_list, days_until, time_of_day):
    """Format the birthday email HTML content"""
    today = datetime.now().strftime("%B %d, %Y")
    
    if days_until == 0:
        header = "🎂 Today's Birthdays"
        intro = "The following members are celebrating their birthdays today:"
    else:
        header = f"🎈 Upcoming Birthdays in {days_until} {'Day' if days_until == 1 else 'Days'}"
        intro = f"This is a {time_of_day} reminder for upcoming birthdays:"
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>{header}</h2>
        <p>{intro}</p>
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
    """
    
    for member in birthday_list:
        html += f"""
            <div style="margin-bottom: 15px; padding: 10px; background-color: white; border-radius: 5px;">
                <h3 style="margin: 0; color: #4c1d95;">👤 {member['name']}</h3>
                <p style="margin: 5px 0; color: #1e1b4b;">
                    📅 Birthday: {member['birthday']}<br>
                    🏢 Department: {member['department']}
                </p>
            </div>
        """
    
    html += f"""
        </div>
        <p style="color: #666; font-size: 0.9em;">
            Sent on: {today} ({time_of_day} reminder)
        </p>
    </body>
    </html>
    """
    return html

def check_and_send_birthday_reminders(force_send=False):
    try:
        # Get all necessary data
        members = get_youth_members()
        recipients = get_email_recipients()
        departments = get_departments()
        dept_mapping = {dept['id']: dept['name'] for dept in departments}
        
        if not members or not recipients:
            return "No members or recipients found.", False
            
        recipient_emails = [r['email'] for r in recipients]
        today = datetime.now()
        current_hour = today.hour
        
        # Initialize lists for different notification types
        today_birthdays = []
        tomorrow_birthdays = []
        two_days_birthdays = []
        three_days_birthdays = []
        
        for member in members:
            if member.get('birthday'):
                # Convert DD/MM to datetime
                day, month = member['birthday'].split('/')
                bday_this_year = datetime(today.year, int(month), int(day))
                
                # If birthday has passed this year, look at next year
                if bday_this_year < today:
                    bday_this_year = datetime(today.year + 1, int(month), int(day))
                
                # Calculate days until birthday
                days_until = (bday_this_year.date() - today.date()).days
                
                # Get department name
                department = dept_mapping.get(member['department_id'], 'No Department')
                
                member_info = {
                    'name': member['full_name'],
                    'birthday': member['birthday'],
                    'department': department,
                    'days_until': days_until
                }
                
                # Categorize based on days until birthday
                if days_until == 0:
                    today_birthdays.append(member_info)
                elif days_until == 1:
                    tomorrow_birthdays.append(member_info)
                elif days_until == 2:
                    two_days_birthdays.append(member_info)
                elif days_until == 3:
                    three_days_birthdays.append(member_info)
        
        # Check if there are any upcoming birthdays
        has_upcoming_birthdays = (
            today_birthdays or tomorrow_birthdays or 
            two_days_birthdays or three_days_birthdays
        )
        
        if not has_upcoming_birthdays:
            return "No upcoming birthdays in the next 3 days", True
        
        # Morning reminder time: 9 AM (9:00)
        # Afternoon reminder time: 2 PM (14:00)
        is_morning_time = 8 <= current_hour < 10
        is_afternoon_time = 13 <= current_hour < 15
        
        # For testing, force send if requested
        if force_send:
            is_morning_time = True  # Use morning format for test
        
        notifications_sent = False
        
        if force_send or is_morning_time or is_afternoon_time:
            time_of_day = "morning" if (force_send or is_morning_time) else "afternoon"
            
            # Format and send emails based on timing
            if three_days_birthdays:
                # Birthdays in 3 days
                body = format_birthday_email(three_days_birthdays, 3, time_of_day)
                send_birthday_email(
                    recipient_emails, 
                    "🎈 Birthdays in 3 Days!", 
                    body
                )
                notifications_sent = True
            
            if two_days_birthdays:
                # Birthdays in 2 days
                body = format_birthday_email(two_days_birthdays, 2, time_of_day)
                send_birthday_email(
                    recipient_emails, 
                    "🎈 Birthdays in 2 Days!", 
                    body
                )
                notifications_sent = True
            
            if tomorrow_birthdays:
                # Tomorrow's birthdays
                body = format_birthday_email(tomorrow_birthdays, 1, time_of_day)
                send_birthday_email(
                    recipient_emails, 
                    "🎈 Birthday Tomorrow!", 
                    body
                )
                notifications_sent = True
            
            if today_birthdays:
                # Today's birthdays
                body = format_birthday_email(today_birthdays, 0, time_of_day)
                send_birthday_email(
                    recipient_emails, 
                    "🎂 Birthday Today!", 
                    body
                )
                notifications_sent = True
            
            if notifications_sent:
                summary = []
                if three_days_birthdays:
                    summary.append(f"{len(three_days_birthdays)} in 3 days")
                if two_days_birthdays:
                    summary.append(f"{len(two_days_birthdays)} in 2 days")
                if tomorrow_birthdays:
                    summary.append(f"{len(tomorrow_birthdays)} tomorrow")
                if today_birthdays:
                    summary.append(f"{len(today_birthdays)} today")
                    
                return f"Birthday reminders sent for: {', '.join(summary)}", True
        else:
            return "Reminders will be sent at 9 AM and 2 PM", True
            
    except Exception as e:
        return f"Error checking birthdays: {str(e)}", False 