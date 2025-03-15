import streamlit as st
from datetime import datetime
from utils.email_service import check_and_send_birthday_reminders

def run_scheduled_tasks():
    """Run scheduled tasks for birthday reminders"""
    current_hour = datetime.now().hour
    
    # Check if it's time to send reminders (9 AM or 2 PM)
    if current_hour in [9, 14]:  # 9 AM and 2 PM
        try:
            message, success = check_and_send_birthday_reminders()
            if success:
                st.session_state.last_check = datetime.now()
                st.session_state.last_status = f"Success: {message}"
            else:
                st.session_state.last_status = f"Failed: {message}"
        except Exception as e:
            st.session_state.last_status = f"Error: {str(e)}" 