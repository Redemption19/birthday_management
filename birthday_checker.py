import streamlit as st
from utils.email_service import check_and_send_birthday_reminders
from utils.database import init_connection

def main():
    # Initialize database connection
    init_connection()
    
    # Check and send birthday reminders
    result_message, success = check_and_send_birthday_reminders()
    if success:
        st.success(result_message)
    else:
        st.error(result_message)

if __name__ == "__main__":
    main()