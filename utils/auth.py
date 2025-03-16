import streamlit as st
from utils.database import init_connection
import re
import time

def init_auth():
    """Initialize authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    if 'access_token' not in st.session_state:
        st.session_state['access_token'] = None
    if 'refresh_token' not in st.session_state:
        st.session_state['refresh_token'] = None

def check_auth():
    """Check if user is authenticated"""
    # If already authenticated, return True
    if st.session_state.authenticated:
        return True
    # If not authenticated, just return False and let main.py handle the login form
    return False

def show_login():
    """Show login form"""
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            try_login(email, password)

def try_login(email, password):
    """Attempt to login user"""
    try:
        supabase = init_connection()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        # Update session state
        st.session_state.authenticated = True
        st.session_state['user'] = response.user
        st.session_state['access_token'] = response.session.access_token
        st.session_state['refresh_token'] = response.session.refresh_token
        st.session_state.user_role = 'admin'  # Set this for admin users
        st.success("Login successful!")
        time.sleep(0.5)
        st.rerun()
        return True
    except Exception as e:
        st.error("Invalid credentials")
        return False

def logout():
    """Logout user"""
    supabase = init_connection()
    try:
        supabase.auth.sign_out()
        st.session_state['authenticated'] = False
        st.session_state['user'] = None
        st.success("Logged out successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Logout failed: {str(e)}")

def check_authentication():
    """
    Check if user is authenticated. For now, returns True for development.
    TODO: Implement proper Supabase authentication
    """
    # For development, always return True
    # In production, implement proper authentication
    return True

def login():
    """
    Handle user login
    TODO: Implement proper Supabase authentication
    """
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # TODO: Implement actual authentication logic
            if username == "admin" and password == "password":
                st.session_state["authenticated"] = True
                st.session_state.user_role = 'admin'  # Set this for admin users
                return True
            else:
                st.error("Invalid credentials")
                return False
    return False

def logout():
    """
    Handle user logout
    """
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    """
    Validate password strength
    - At least 8 characters
    - Contains uppercase and lowercase
    - Contains numbers
    - Contains special characters
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def try_reset_password(email):
    """Send password reset email"""
    supabase = init_connection()
    try:
        # Using the correct Supabase method for password reset
        response = supabase.auth.reset_password_for_email(email)
        st.success("Password reset link has been sent to your email!")
        return True
    except Exception as e:
        st.error(f"Failed to send reset email: {str(e)}")
        return False

def validate_new_password(password, confirm_password):
    """Validate new password during reset"""
    if password != confirm_password:
        return False, "Passwords do not match"
    
    is_valid, message = is_valid_password(password)
    return is_valid, message

def refresh_token():
    """Refresh the access token"""
    supabase = init_connection()
    try:
        if st.session_state.get('refresh_token'):
            response = supabase.auth.refresh_session()
            st.session_state['access_token'] = response.session.access_token
            return True
    except Exception as e:
        st.error("Session expired. Please login again.")
        logout()
        return False

def is_admin():
    """
    Check if the current user has admin privileges.
    Returns True if the user is an admin, False otherwise.
    """
    # Check if user is authenticated and has admin role
    is_authenticated = st.session_state.get('authenticated', False)
    user_role = st.session_state.get('user_role', 'none')
    return is_authenticated and user_role == 'admin' 