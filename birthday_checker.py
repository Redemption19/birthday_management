import streamlit as st
from utils.email_service import check_upcoming_birthdays
from utils.database import init_connection

def main():
    # Initialize database connection
    init_connection()
    
    # Check and send birthday reminders
    check_upcoming_birthdays()

if __name__ == "__main__":
    main() 