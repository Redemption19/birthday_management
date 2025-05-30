from supabase import create_client
import streamlit as st
import pandas as pd
from datetime import datetime

def init_connection():
    """Initialize Supabase connection with token refresh"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        # Create client with service role key for admin access
        supabase = create_client(url, key)
        
        # Add debug logging
        print("Database connection initialized")
        
        return supabase
    except Exception as e:
        print(f"Connection error details: {str(e)}")
        st.error(f"Connection error: {str(e)}")
        return None

@st.cache_data(ttl=5, show_spinner=False)
def get_youth_members():
    """Get all youth members with their department info"""
    try:
        supabase = init_connection()
        if not supabase:
            return []
            
        print("Fetching youth members...")
        
        # Use simpler query first to debug
        response = supabase.from_("youth_members").select("*").execute()
        print(f"Raw response: {response}")  # Debug print
        
        if response.data:
            print(f"Fetched {len(response.data)} members")
            return response.data
        else:
            print("No members found in response")
            return []
            
    except Exception as e:
        print(f"Error fetching members: {str(e)}")
        return []

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
    """Get all contributions with member info"""
    try:
        supabase = init_connection()
        if not supabase:
            return []
            
        # Debug print
        print("Fetching contributions...")
        
        # Updated query with proper joins
        query = supabase.table("contributions")\
            .select(
                "id, amount, contribution_type, payment_date, week_number, month, year, member_id, youth_members!inner(full_name)"
            )
        
        if member_id:
            query = query.eq("member_id", member_id)
            
        response = query.execute()
        print(f"Fetched {len(response.data)} contributions")  # Debug log
        return response.data
    except Exception as e:
        print(f"Error fetching contributions: {str(e)}")
        return []

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
    """Get all departments"""
    try:
        supabase = init_connection()
        if not supabase:
            return []
            
        print("Fetching departments...")
        
        # Simple query first
        response = supabase.from_("departments").select("*").execute()
        print(f"Raw departments response: {response}")  # Debug print
        
        if response.data:
            print(f"Fetched {len(response.data)} departments")
            return response.data
        else:
            print("No departments found in response")
            return []
            
    except Exception as e:
        print(f"Error fetching departments: {str(e)}")
        return []

@st.cache_data(ttl=5, show_spinner=False)
def get_monthly_birthdays(month):
    """Get birthdays for a specific month"""
    try:
        supabase = init_connection()
        if not supabase:
            return []
            
        # Convert month to two digits
        month_str = f"{month:02d}"
        
        # Updated query with proper format
        response = supabase.table("youth_members")\
            .select("*, departments!inner(*)")\
            .ilike("birthday", f"%/{month_str}")\
            .execute()
            
        return response.data
    except Exception as e:
        print(f"Error fetching birthdays: {str(e)}")
        return []

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

def add_email_recipient(email):
    """Add new email recipient"""
    try:
        supabase = init_connection()
        response = supabase.table('email_recipients').insert({
            'email': email
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error adding email recipient: {str(e)}")
        return False

def get_email_recipients():
    """Get all email recipients"""
    try:
        supabase = init_connection()
        response = supabase.table('email_recipients').select('*').execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching email recipients: {str(e)}")
        return []

def delete_email_recipient(email):
    """Delete email recipient"""
    try:
        supabase = init_connection()
        response = supabase.table('email_recipients').delete().eq('email', email).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting email recipient: {str(e)}")
        return False 