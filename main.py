import streamlit as st
from utils.auth import init_auth, check_auth, logout, try_login, try_reset_password, is_valid_email
from utils.database import init_connection, check_users_exist, get_youth_members, get_contributions, get_departments, get_monthly_birthdays
from utils.auth import check_authentication
from datetime import datetime, timedelta
from utils.email_service import check_and_send_birthday_reminders

# Initialize authentication
init_auth()

# Initialize scheduler state
if 'last_email_check' not in st.session_state:
    st.session_state.last_email_check = None
if 'last_email_status' not in st.session_state:
    st.session_state.last_email_status = None

# Run birthday reminder check if authenticated
if st.session_state.authenticated:
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    # Check if it's time to send reminders (9 AM or 2 PM)
    if current_hour in [9, 14] and 0 <= current_minute < 5:
        # Only send if we haven't sent in the last 4 minutes
        if (st.session_state.last_email_check is None or 
            current_time - st.session_state.last_email_check > timedelta(minutes=4)):
            try:
                message, success = check_and_send_birthday_reminders()
                st.session_state.last_email_check = current_time
                st.session_state.last_email_status = f"{'✅' if success else '❌'} {message}"
            except Exception as e:
                st.session_state.last_email_status = f"❌ Error: {str(e)}"

# Page config
st.set_page_config(
    page_title="Empowerment Youth Management System",
    page_icon="⛪",
    layout="wide"
)

# Custom CSS with improved styling
st.markdown("""
    <style>
        /* Main header styling */
        .main-title {
            color: #1E3A8A;
            text-align: center;
            padding: 1rem;
            margin-bottom: 2rem;
            font-size: 2.5rem;
        }
        
        /* Greeting text styling */
        .greeting-text {
            color: #4B5563;
            font-size: 1.2rem;
            margin-bottom: 2rem;
            font-style: italic;
        }
        
        /* Card container styling */
        .card-container {
            display: flex;
            justify-content: space-between;
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        /* Individual card styling */
        .custom-card {
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            width: 100%;
        }
        
        /* Quick Actions card */
        .quick-actions {
            background-color: #2D1D12;
            border-left: 4px solid #EA580C;
        }
        .quick-actions h3 {
            color: #EA580C;
            margin-bottom: 1rem;
        }
        
        /* System Features card */
        .system-features {
            background-color: #1E1B4B;
            border-left: 4px solid #4F46E5;
        }
        .system-features h3 {
            color: #818CF8;
            margin-bottom: 1rem;
        }
        
        /* Help & Support card */
        .help-support {
            background-color: #064E3B;
            border-left: 4px solid #059669;
        }
        .help-support h3 {
            color: #34D399;
            margin-bottom: 1rem;
        }
        
        /* Card text styling */
        .card-text {
            color: #E5E7EB;
            font-size: 1rem;
            line-height: 1.8;
        }
        
        /* System Overview section */
        .system-overview {
            background-color: #1a1a2e;  /* Dark blue background */
            padding: 2rem;
            border-radius: 10px;
            margin-top: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        .system-overview h2 {
            color: #818CF8;  /* Light blue text */
            margin-bottom: 2rem;
        }
        
        .metric-container {
            text-align: center;
            background-color: #252547;  /* Slightly lighter blue */
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #4F46E5;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #E5E7EB;  /* Light gray text */
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            color: #9CA3AF;  /* Muted gray text */
            font-size: 1rem;
        }
        
        /* Footer styling */
        .footer {
            text-align: center;
            margin-top: 3rem;
            padding: 1rem;
            background-color: #1a1a2e;
            border-radius: 10px;
            color: #9CA3AF;
        }
    </style>
""", unsafe_allow_html=True)

# Add user info and logout in sidebar if authenticated
if st.session_state.authenticated:
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-info">
                <h3>User Information</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # Display user email and role
        st.info(f"📧 {st.session_state.user.email}")
        st.markdown(f"""
            <div class="role-badge">
                {st.session_state.user.role if hasattr(st.session_state.user, 'role') else 'User'}
            </div>
        """, unsafe_allow_html=True)
        
        # Add birthday reminder status
        st.markdown("---")
        st.markdown("#### 🎂 Birthday Reminders")
        st.markdown("""
            Scheduled times:
            - 🌅 9:00 AM
            - 🌇 2:00 PM
        """)
        
        if st.session_state.last_email_check:
            st.markdown("**Last Check:**")
            st.info(st.session_state.last_email_check.strftime("%Y-%m-%d %H:%M:%S"))
            
        if st.session_state.last_email_status:
            st.markdown("**Status:**")
            if "✅" in st.session_state.last_email_status:
                st.success(st.session_state.last_email_status)
            elif "❌" in st.session_state.last_email_status:
                st.error(st.session_state.last_email_status)
            else:
                st.info(st.session_state.last_email_status)
        
        # Add some space before logout button
        st.write("")
        if st.button("🚪 Logout", type="secondary"):
            logout()
            st.rerun()

# Check authentication before showing content
check_auth()

# Initialize database connection
supabase = init_connection()

# Check if any users exist and show initial admin creation if none
users_exist = False
try:
    # Try to get users from Supabase auth
    response = supabase.auth.admin.list_users()
    users = response.users if hasattr(response, 'users') else []
    users_exist = len(users) > 0
except Exception as e:
    # If we can't check users (likely due to permissions), assume users exist
    users_exist = True
    print(f"Error checking users: {str(e)}")

# Show login form if not authenticated
if not st.session_state['authenticated']:
    st.title("Login")
    
    if not users_exist:
        st.warning("No users found. Please create an initial admin account.")
        
        with st.form("create_initial_admin"):
            admin_email = st.text_input("Admin Email")
            admin_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Create Admin Account"):
                if admin_password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    try:
                        response = supabase.auth.sign_up({
                            "email": admin_email,
                            "password": admin_password
                        })
                        st.success("Admin account created successfully! Please login.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating admin account: {str(e)}")
    else:
        # Add vertical space before cards
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Create two columns with equal width
        col1, col2 = st.columns(2)
        
        # Login Column
        with col1:
            st.markdown("""
                <div style="background-color: #1E1B4B; padding: 2rem; border-radius: 10px; border-left: 4px solid #4F46E5; margin-bottom: 1rem;">
                    <h3 style="color: #E5E7EB; margin-bottom: 1.5rem;">Login</h3>
                </div>
                <div style="height: 20px;"></div>  <!-- Spacing div -->
            """, unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if not email or not password:
                        st.error("Please fill in all fields")
                    elif not is_valid_email(email):
                        st.error("Please enter a valid email address")
                    else:
                        try_login(email, password)
        
        # Forgot Password Column
        with col2:
            st.markdown("""
                <div style="background-color: #1E1B4B; padding: 2rem; border-radius: 10px; border-left: 4px solid #4F46E5; margin-bottom: 1rem;">
                    <h3 style="color: #E5E7EB; margin-bottom: 1.5rem;">Forgot Password</h3>
                    <p style="color: #9CA3AF; margin-bottom: 1.5rem; font-size: 0.9rem;">
                        Enter your email address below and we'll send you instructions to reset your password.
                    </p>
                </div>
                <div style="height: 20px;"></div>  <!-- Spacing div -->
            """, unsafe_allow_html=True)
            
            with st.form("forgot_password_form", clear_on_submit=False):
                reset_email = st.text_input("Email Address", key="reset_email")
                reset_submit = st.form_submit_button("Send Reset Link", use_container_width=True)
                
                if reset_submit:
                    if not reset_email:
                        st.error("Please enter your email address")
                    elif not is_valid_email(reset_email):
                        st.error("Please enter a valid email address")
                    else:
                        try_reset_password(reset_email)
    
    st.stop()

# Main Dashboard Content
st.markdown('<h1 class="main-title">Empowerment Youth Management System</h1>', unsafe_allow_html=True)

# Greeting
current_hour = datetime.now().hour
greeting = "Good Morning" if current_hour < 12 else "Good Afternoon" if current_hour < 17 else "Good Evening"
st.markdown(f'<p class="greeting-text">{greeting}, {st.session_state["user"].email} 👋</p>', unsafe_allow_html=True)

# Dashboard Cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div class="custom-card quick-actions">
            <h3>Quick Actions</h3>
            <p class="card-text">
                ⚡ Add New Member<br>
                💰 Record Contribution<br>
                🎂 View Birthdays<br>
                👥 Manage Departments
            </p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="custom-card system-features">
            <h3>System Features</h3>
            <p class="card-text">
                👤 Member Management<br>
                📊 Contribution Tracking<br>
                🏢 Department Organization<br>
                🔔 Birthday Notifications
            </p>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="custom-card help-support">
            <h3>Help & Support</h3>
            <p class="card-text">
                📖 User Guide<br>
                📧 Contact Admin<br>
                🐛 Report Issues<br>
                🔄 System Updates
            </p>
        </div>
    """, unsafe_allow_html=True)

# Fetch data for System Overview
try:
    # Get all data
    all_members = get_youth_members()
    all_contributions = get_contributions()
    all_departments = get_departments()
    current_month = datetime.now().month
    monthly_birthdays = get_monthly_birthdays(current_month)
    
    # Calculate totals
    total_members = len(all_members) if all_members else 0
    total_contributions = sum(float(contrib['amount']) for contrib in all_contributions) if all_contributions else 0
    total_departments = len(all_departments) if all_departments else 0
    total_birthdays = len(monthly_birthdays) if monthly_birthdays else 0

    # Add this to your data fetching section
    upcoming_birthdays = []
    today = datetime.now()
    if all_members:
        for member in all_members:
            if member.get('birthday'):
                day, month = member['birthday'].split('/')
                bday_this_year = datetime(today.year, int(month), int(day))
                
                if bday_this_year < today:
                    bday_this_year = datetime(today.year + 1, int(month), int(day))
                
                days_until = (bday_this_year.date() - today.date()).days
                
                if 0 <= days_until <= 3:
                    upcoming_birthdays.append({
                        'name': member['full_name'],
                        'birthday': member['birthday'],
                        'days': days_until
                    })

except Exception as e:
    st.error(f"Error fetching data: {str(e)}")
    total_members = total_contributions = total_departments = total_birthdays = 0

# System Overview Section
st.markdown('<div class="system-overview">', unsafe_allow_html=True)
st.markdown('<h2>System Overview</h2>', unsafe_allow_html=True)

# Create metrics row with real data
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">👥 {total_members}</div>
            <div class="metric-label">Total Members</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">💰 ₵{total_contributions:,.2f}</div>
            <div class="metric-label">Total Contributions</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">🏢 {total_departments}</div>
            <div class="metric-label">Departments</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">🎂 {total_birthdays}</div>
            <div class="metric-label">Birthdays This Month</div>
        </div>
    """, unsafe_allow_html=True)

# Add this after your metrics columns
if upcoming_birthdays:
    st.markdown("---")
    st.markdown("### 🎂 Upcoming Birthdays")
    
    birthday_cols = st.columns(len(upcoming_birthdays))
    for idx, birthday in enumerate(sorted(upcoming_birthdays, key=lambda x: x['days'])):
        with birthday_cols[idx]:
            st.markdown(f"""
                <div class="metric-container" style="background-color: #4c1d95;">
                    <div class="metric-value">🎈 {birthday['name']}</div>
                    <div class="metric-label">
                        {birthday['birthday']}<br>
                        {'Today!' if birthday['days'] == 0 else f'In {birthday["days"]} days'}
                    </div>
                </div>
            """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
    <div class="footer">
        <p>© 2025 Empowerment Youth Management System. All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)