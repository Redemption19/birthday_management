import streamlit as st
from utils.auth import init_auth, check_auth
from utils.database import (
    init_connection, 
    get_youth_members, 
    get_departments,
    add_youth_member,
    add_contribution,
    update_youth_member,
    delete_youth_member,
    add_department,
    update_department,
    delete_department,
    get_contributions
)
import pandas as pd
from datetime import datetime
import re
import io
import time

# Initialize authentication
init_auth()

# Check authentication before showing content
check_auth()

# Add this at the start of your admin panel, run once, then remove it
if st.sidebar.checkbox("Create Initial Admin"):
    with st.form("create_admin"):
        admin_email = st.text_input("Admin Email")
        admin_password = st.text_input("Password", type="password")
        
        if st.form_submit_button("Create Admin"):
            supabase = init_connection()
            try:
                response = supabase.auth.sign_up({
                    "email": admin_email,
                    "password": admin_password
                })
                st.success(f"Admin account created! Email: {admin_email}")
            except Exception as e:
                st.error(f"Error creating admin: {str(e)}")

st.title("Admin Panel")

# Admin sections
tab1, tab2, tab3 = st.tabs([
    "Member Management",
    "Contribution Management",
    "Department Management"
])

with tab1:
    # Search and Filter Section
    st.subheader("Search & Filter Members")
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        search_query = st.text_input("Search by name, phone, or email")
    with search_col2:
        departments = get_departments()
        dept_options = {dept['name']: dept['id'] for dept in departments}
        filter_department = st.selectbox(
            "Filter by Department",
            options=["All Departments"] + list(dept_options.keys())
        )

    # Bulk Import/Export Section
    st.subheader("Bulk Import/Export")
    exp_col1, exp_col2 = st.columns(2)
    
    with exp_col1:
        # Export functionality
        members = get_youth_members()
        if members:
            df = pd.DataFrame(members)
            df['department'] = df['department_id'].apply(lambda x: dept_options.get(x, 'No Department'))
            export_df = df[['full_name', 'birthday', 'department', 'phone_number', 'email']]
            export_df.columns = ['Name', 'Birthday', 'Department', 'Phone', 'Email']
            
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Export Members to CSV",
                data=csv,
                file_name="youth_members.csv",
                mime="text/csv"
            )
    
    with exp_col2:
        # Import functionality
        uploaded_file = st.file_uploader("Import Members from CSV", type=['csv'])
        if uploaded_file is not None:
            try:
                import_df = pd.read_csv(uploaded_file)
                if st.button("Process Import"):
                    with st.spinner("Importing members..."):
                        for _, row in import_df.iterrows():
                            dept_id = next(
                                (v for k, v in dept_options.items() if k == row['Department']),
                                list(dept_options.values())[0]
                            )
                            try:
                                add_youth_member(
                                    full_name=row['Name'],
                                    birthday=row['Birthday'],
                                    department_id=dept_id,
                                    phone_number=row.get('Phone'),
                                    email=row.get('Email')
                                )
                            except Exception as e:
                                st.error(f"Error importing {row['Name']}: {str(e)}")
                        st.success("Import completed!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error reading CSV: {str(e)}")
    
    # Create two columns for Add and Edit/Delete
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add New Member")
        with st.form("add_member_form"):
            # Member details
            full_name = st.text_input("Full Name")
            birthday = st.text_input("Birthday (DD/MM)", max_chars=5, help="Format: DD/MM (e.g., 05/12)")
            department = st.selectbox("Department", options=list(dept_options.keys()))
            phone = st.text_input("Phone Number (Optional)")
            email = st.text_input("Email (Optional)")
            
            submit_member = st.form_submit_button("Add Member")
            
            if submit_member:
                if not full_name or not birthday or not department:
                    st.error("Please fill in all required fields")
                elif not re.match(r'^\d{2}/\d{2}$', birthday):
                    st.error("Birthday must be in DD/MM format")
                else:
                    try:
                        success = add_youth_member(
                            full_name=full_name,
                            birthday=birthday,
                            department_id=dept_options[department],
                            phone_number=phone,
                            email=email
                        )
                        
                        if success:
                            st.success(f"Successfully added {full_name}")
                            # Clear caches
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            time.sleep(0.5)  # Small delay to ensure database sync
                            st.rerun()
                        else:
                            st.error("Failed to add member. Please try again.")
                    except Exception as e:
                        st.error(f"Error adding member: {str(e)}")
    
    with col2:
        st.subheader("Edit/Delete Member")
        members = get_youth_members()
        if members:
            # Filter members based on search and department
            filtered_members = members
            if search_query:
                search_query = search_query.lower()
                filtered_members = [
                    m for m in members
                    if search_query in m['full_name'].lower()
                    or (m.get('phone_number') and search_query in m['phone_number'])
                    or (m.get('email') and search_query in m['email'].lower())
                ]
            
            if filter_department != "All Departments":
                filtered_members = [
                    m for m in filtered_members
                    if m['department_id'] == dept_options[filter_department]
                ]
            
            if filtered_members:
                member_options = {m['full_name']: m['id'] for m in filtered_members}
                selected_member_name = st.selectbox(
                    "Select Member to Edit/Delete",
                    options=list(member_options.keys())
                )
                
                selected_member = next(
                    (m for m in filtered_members if m['id'] == member_options[selected_member_name]),
                    None
                )
                
                # Initialize delete confirmation state
                if 'show_member_delete_confirm' not in st.session_state:
                    st.session_state.show_member_delete_confirm = False
                
                if selected_member:
                    with st.form("edit_member_form"):
                        edit_name = st.text_input("Full Name", value=selected_member['full_name'])
                        edit_birthday = st.text_input(
                            "Birthday (DD/MM)",
                            value=selected_member['birthday'],
                            max_chars=5
                        )
                        
                        current_dept = next(
                            (k for k, v in dept_options.items() 
                             if v == selected_member['department_id']),
                            list(dept_options.keys())[0]
                        )
                        edit_department = st.selectbox(
                            "Department",
                            options=list(dept_options.keys()),
                            index=list(dept_options.keys()).index(current_dept)
                        )
                        
                        edit_phone = st.text_input(
                            "Phone Number",
                            value=selected_member.get('phone_number', '')
                        )
                        edit_email = st.text_input(
                            "Email",
                            value=selected_member.get('email', '')
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update Member")
                        with col2:
                            delete_button = st.form_submit_button("Delete Member", type="secondary")
                        
                        if update_button:
                            if not edit_name or not edit_birthday or not edit_department:
                                st.error("Please fill in all required fields")
                            elif not re.match(r'^\d{2}/\d{2}$', edit_birthday):
                                st.error("Birthday must be in DD/MM format")
                            else:
                                try:
                                    success = update_youth_member(
                                        member_id=selected_member['id'],
                                        full_name=edit_name,
                                        birthday=edit_birthday,
                                        department_id=dept_options[edit_department],
                                        phone_number=edit_phone,
                                        email=edit_email
                                    )
                                    
                                    if success:
                                        st.cache_data.clear()
                                        st.cache_resource.clear()
                                        st.success(f"Successfully updated {edit_name}")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("Failed to update member. Please try again.")
                                except Exception as e:
                                    st.error(f"Error updating member: {str(e)}")
                        
                        if delete_button:
                            st.session_state.show_member_delete_confirm = True
                    
                    # Show delete confirmation outside the form
                    if st.session_state.show_member_delete_confirm:
                        st.warning("⚠️ Are you sure you want to delete this member?")
                        st.write(f"Name: {selected_member['full_name']}")
                        st.write(f"Department: {current_dept}")
                        st.write(f"Birthday: {selected_member['birthday']}")
                        if selected_member.get('phone_number'):
                            st.write(f"Phone: {selected_member['phone_number']}")
                        if selected_member.get('email'):
                            st.write(f"Email: {selected_member['email']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Yes, Delete", type="primary"):
                                try:
                                    success = delete_youth_member(selected_member['id'])
                                    
                                    if success:
                                        st.session_state.show_member_delete_confirm = False
                                        st.cache_data.clear()
                                        st.cache_resource.clear()
                                        st.success(f"Successfully deleted {selected_member['full_name']}")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete member. Please try again.")
                                except Exception as e:
                                    st.error(f"Error deleting member: {str(e)}")
                        
                        with col2:
                            if st.button("No, Cancel"):
                                st.session_state.show_member_delete_confirm = False
                                st.rerun()
            else:
                st.info("No members found matching your search criteria")
        else:
            st.info("No members found in the database")
    
    # Display existing members
    st.subheader("Existing Members")
    # Get fresh data after any changes
    members = get_youth_members()
    if members:
        df = pd.DataFrame(members)
        df['department'] = df['department_id'].apply(lambda x: dept_options.get(x, 'No Department'))
        display_df = df[['full_name', 'birthday', 'department', 'phone_number', 'email']]
        display_df.columns = ['Name', 'Birthday', 'Department', 'Phone', 'Email']
        
        # Apply filters to display
        if search_query:
            display_df = display_df[
                display_df['Name'].str.contains(search_query, case=False) |
                display_df['Phone'].str.contains(search_query, case=False, na=False) |
                display_df['Email'].str.contains(search_query, case=False, na=False)
            ]
        
        if filter_department != "All Departments":
            display_df = display_df[display_df['Department'] == filter_department]
            
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No members found in the database")

with tab2:
    st.subheader("Contribution Management")
    
    # Create two columns for Add and Edit/Delete
    contrib_col1, contrib_col2 = st.columns(2)
    
    with contrib_col1:
        st.subheader("Add New Contribution")
        with st.form("add_contribution_form"):
            # Get members for dropdown
            members = get_youth_members()
            member_options = {member['full_name']: member['id'] for member in members}
            selected_member = st.selectbox("Select Member", options=list(member_options.keys()))
            
            amount = st.number_input("Amount (GH₵)", min_value=0.0, step=5.0)
            
            contribution_type = st.selectbox(
                "Contribution Type",
                options=['BIRTHDAY', 'PROJECT', 'EVENT']
            )
            
            payment_date = st.date_input("Payment Date")
            
            week_number = None
            if contribution_type == 'BIRTHDAY':
                week_number = st.number_input("Week Number", min_value=1, max_value=4, step=1)
            
            submit_contribution = st.form_submit_button("Add Contribution")
            
            if submit_contribution:
                if not selected_member or amount <= 0:
                    st.error("Please fill in all required fields")
                else:
                    try:
                        # Add contribution to database
                        add_contribution(
                            member_id=member_options[selected_member],
                            amount=amount,
                            contribution_type=contribution_type,
                            payment_date=payment_date.strftime('%Y-%m-%d'),
                            week_number=week_number
                        )
                        st.success(f"Successfully added contribution for {selected_member}")
                    except Exception as e:
                        st.error(f"Error adding contribution: {str(e)}")
    
    with contrib_col2:
        st.subheader("Edit/Delete Contribution")
        contributions = get_contributions()
        if contributions:
            # Select contribution to manage
            selected_contrib = st.selectbox(
                "Select Contribution",
                options=[f"{c['youth_members']['full_name']} - GH₵{c['amount']} ({c['payment_date']})" 
                        for c in contributions]
            )
            
            if selected_contrib:
                # Get selected contribution
                selected_idx = [f"{c['youth_members']['full_name']} - GH₵{c['amount']} ({c['payment_date']})" 
                              for c in contributions].index(selected_contrib)
                selected_contribution = contributions[selected_idx]
                
                # Initialize delete confirmation state
                if 'show_delete_confirm' not in st.session_state:
                    st.session_state.show_delete_confirm = False
                
                with st.form("manage_contribution_form"):
                    edit_amount = st.number_input(
                        "Amount (GH₵)", 
                        min_value=0.0, 
                        value=float(selected_contribution['amount'])
                    )
                    edit_type = st.selectbox(
                        "Contribution Type",
                        options=['BIRTHDAY', 'PROJECT', 'EVENT'],
                        index=['BIRTHDAY', 'PROJECT', 'EVENT'].index(selected_contribution['contribution_type'])
                    )
                    edit_date = st.date_input(
                        "Payment Date",
                        value=datetime.strptime(selected_contribution['payment_date'], '%Y-%m-%d').date()
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        update_button = st.form_submit_button("Update")
                    with col2:
                        delete_button = st.form_submit_button("Delete", type="secondary")
                    
                    if update_button:
                        try:
                            supabase = init_connection()
                            result = supabase.table("contributions").update({
                                "amount": edit_amount,
                                "contribution_type": edit_type,
                                "payment_date": edit_date.strftime('%Y-%m-%d')
                            }).eq("id", selected_contribution['id']).execute()
                            
                            st.success("Contribution updated successfully!")
                            st.cache_data.clear()
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating contribution: {str(e)}")
                    
                    if delete_button:
                        st.session_state.show_delete_confirm = True
                
                # Show delete confirmation outside the form
                if st.session_state.show_delete_confirm:
                    st.warning("⚠️ Are you sure you want to delete this contribution?")
                    st.write(f"Member: {selected_contribution['youth_members']['full_name']}")
                    st.write(f"Amount: GH₵{selected_contribution['amount']}")
                    st.write(f"Date: {selected_contribution['payment_date']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, Delete", type="primary"):
                            try:
                                supabase = init_connection()
                                result = supabase.table("contributions")\
                                    .delete()\
                                    .eq("id", selected_contribution['id'])\
                                    .execute()
                                
                                st.session_state.show_delete_confirm = False
                                st.success("Contribution deleted successfully!")
                                st.cache_data.clear()
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting contribution: {str(e)}")
                    
                    with col2:
                        if st.button("No, Cancel"):
                            st.session_state.show_delete_confirm = False
                            st.rerun()
        else:
            st.info("No contributions found")
    
    # Display existing contributions
    st.subheader("Existing Contributions")
    if contributions:
        df = pd.DataFrame(contributions)
        df['member_name'] = df['youth_members'].apply(lambda x: x['full_name'])
        display_df = df[['member_name', 'amount', 'contribution_type', 'payment_date', 'week_number']]
        display_df.columns = ['Member', 'Amount (GH₵)', 'Type', 'Date', 'Week']
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No contributions found in the database")

with tab3:
    st.header("User Management")
    
    # Create new user section
    st.subheader("Create New User")
    with st.form("create_user"):
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.form_submit_button("Create User"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                supabase = init_connection()
                try:
                    response = supabase.auth.admin.create_user({
                        "email": new_email,
                        "password": new_password,
                        "email_confirm": True
                    })
                    st.success("User created successfully!")
                except Exception as e:
                    st.error(f"Error creating user: {str(e)}")

    st.header("Department Management")
    
    # Create two columns for add/edit
    dept_col1, dept_col2 = st.columns(2)
    
    with dept_col1:
        st.subheader("Add New Department")
        new_dept_name = st.text_input("Department Name")
        new_dept_desc = st.text_area("Description (optional)")
        
        if st.button("Add Department"):
            if new_dept_name:
                try:
                    add_department(new_dept_name, new_dept_desc)
                    st.success(f"Department '{new_dept_name}' added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding department: {str(e)}")
            else:
                st.warning("Please enter a department name")
    
    with dept_col2:
        st.subheader("Edit Department")
        departments = get_departments()
        if departments:
            dept_to_edit = st.selectbox(
                "Select Department to Edit",
                options=[dept['name'] for dept in departments],
                key="edit_dept"
            )
            
            # Get current department details
            selected_dept = next((dept for dept in departments if dept['name'] == dept_to_edit), None)
            if selected_dept:
                edit_name = st.text_input("New Name", value=selected_dept['name'])
                edit_desc = st.text_area("New Description", value=selected_dept.get('description', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Update Department"):
                        if edit_name:
                            try:
                                update_department(selected_dept['id'], edit_name, edit_desc)
                                st.success("Department updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating department: {str(e)}")
                        else:
                            st.warning("Department name cannot be empty")
                
                with col2:
                    if st.button("Delete Department", type="secondary"):
                        # Add confirmation
                        if st.checkbox("Confirm deletion"):
                            try:
                                delete_department(selected_dept['id'])
                                st.success("Department deleted successfully!")
                                # Clear any cached data
                                st.cache_data.clear()
                                # Use experimental rerun to refresh the page
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Error deleting department: {str(e)}")
        else:
            st.info("No departments found")
    
    # Display existing departments
    st.subheader("Existing Departments")
    if departments:
        dept_df = pd.DataFrame(departments)
        dept_df = dept_df[['name', 'description']]
        dept_df.columns = ['Department Name', 'Description']
        st.dataframe(dept_df, use_container_width=True)
    else:
        st.info("No departments have been created yet") 