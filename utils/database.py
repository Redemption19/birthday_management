from supabase import create_client
import streamlit as st
import pandas as pd
from datetime import datetime

def init_connection():
    """Initialize Supabase connection with token refresh"""
    try:
        supabase = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
        
        # Check if we have a session
        if 'user' in st.session_state:
            try:
                # Try to get user (will fail if token expired)
                user = supabase.auth.get_user()
            except:
                # Token expired, try to refresh
                try:
                    refresh_response = supabase.auth.refresh_session()
                    if refresh_response.user:
                        st.session_state['user'] = refresh_response.user
                    else:
                        # If refresh fails, clear session and redirect to login
                        del st.session_state['user']
                        st.rerun()
                except:
                    # If refresh fails, clear session and redirect to login
                    del st.session_state['user']
                    st.rerun()
        
        return supabase
    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return None

# Add TTL (Time To Live) to cache and enable clearing
@st.cache_data(ttl=5, show_spinner=False)
def get_youth_members():
    supabase = init_connection()
    response = supabase.table("youth_members")\
        .select("*, departments(name)")\
        .execute()
    return response.data

def add_youth_member(full_name, birthday, department_id, phone_number=None, email=None):
    """Add a new youth member"""
    try:
        supabase = init_connection()
        data = {
            "full_name": full_name,
            "birthday": birthday,
            "department_id": department_id,
            "phone_number": phone_number,
            "email": email
        }
        
        result = supabase.table("youth_members").insert(data).execute()
        
        # Clear caches immediately
        st.cache_data.clear()
        st.cache_resource.clear()
        
        return True if result.data else False
    except Exception as e:
        print(f"Add member error: {str(e)}")  # For debugging
        return False

@st.cache_data(ttl=5, show_spinner=False)
def get_contributions(member_id=None):
    supabase = init_connection()
    query = supabase.table("contributions")\
        .select("*, youth_members(full_name)")
    if member_id:
        query = query.eq("member_id", member_id)
    return query.execute().data

def add_contribution(member_id, amount, contribution_type, payment_date, week_number=None):
    supabase = init_connection()
    date_obj = datetime.strptime(payment_date, '%Y-%m-%d')
    return supabase.table("contributions").insert({
        "member_id": member_id,
        "amount": amount,
        "contribution_type": contribution_type,
        "payment_date": payment_date,
        "week_number": week_number,
        "month": date_obj.month,
        "year": date_obj.year
    }).execute()

@st.cache_data(ttl=5, show_spinner=False)
def get_departments():
    supabase = init_connection()
    response = supabase.table("departments").select("*").execute()
    return response.data

@st.cache_data(ttl=5, show_spinner=False)
def get_monthly_birthdays(month):
    supabase = init_connection()
    # Convert month to two digits (e.g., 3 -> "03")
    month_str = f"{month:02d}"
    response = supabase.table("youth_members")\
        .select("*")\
        .ilike("birthday", f"%/{month_str}")\
        .execute()
    return response.data

def update_youth_member(member_id, full_name, birthday, department_id, phone_number=None, email=None):
    """Update an existing youth member"""
    try:
        supabase = init_connection()
        result = supabase.table("youth_members").update({
            "full_name": full_name,
            "birthday": birthday,
            "department_id": department_id,
            "phone_number": phone_number,
            "email": email,
            "updated_at": datetime.now().isoformat()
        }).eq("id", member_id).execute()
        
        # Clear all caches immediately
        st.cache_data.clear()
        st.cache_resource.clear()
        
        return True
    except Exception as e:
        print(f"Update error: {str(e)}")
        return False

# Clear all cached data after modifications
def clear_cache():
    st.cache_data.clear()

# Update delete functions to clear cache
def delete_youth_member(member_id):
    """Delete a youth member"""
    try:
        supabase = init_connection()
        
        # First delete all contributions
        supabase.table("contributions")\
            .delete()\
            .eq("member_id", member_id)\
            .execute()
            
        # Then delete the member
        supabase.table("youth_members")\
            .delete()\
            .eq("id", member_id)\
            .execute()
            
        # Clear all caches immediately
        st.cache_data.clear()
        st.cache_resource.clear()
        
        return True
    except Exception as e:
        print(f"Delete error: {str(e)}")
        return False

def add_department(name, description=None):
    """Add a new department"""
    supabase = init_connection()
    return supabase.table("departments").insert({
        "name": name,
        "description": description
    }).execute()

def update_department(dept_id, name, description=None):
    """Update an existing department"""
    supabase = init_connection()
    return supabase.table("departments").update({
        "name": name,
        "description": description
    }).eq("id", dept_id).execute()

def delete_department(dept_id):
    """Delete a department"""
    supabase = init_connection()
    # First update any members in this department to have no department
    supabase.table("youth_members").update({
        "department_id": None
    }).eq("department_id", dept_id).execute()
    # Then delete the department
    result = supabase.table("departments").delete().eq("id", dept_id).execute()
    clear_cache()  # Clear cache after deletion
    return result

@st.cache_data(ttl=60)  # Cache for 60 seconds
def check_users_exist():
    """Check if any users exist in the system"""
    supabase = init_connection()
    try:
        response = supabase.from_('users').select('id').limit(1).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking users table: {str(e)}")
        return True  # Assume users exist if we can't check 