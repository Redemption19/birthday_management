import streamlit as st
from utils.email_service import check_and_send_birthday_reminders
from utils.database import init_connection

def main():
    # Initialize database connection
    init_connection()
    
    # Check and send birthday reminders
    check_and_send_birthday_reminders()

if __name__ == "__main__":
    main()