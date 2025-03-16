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
    get_contributions,
    get_email_recipients,
    add_email_recipient,
    delete_email_recipient
)
import pandas as pd
from datetime import datetime, timedelta
import re
import io
import time

# Initialize authentication
init_auth()

# Check authentication before showing ANY content
if not check_auth():
    st.error("Please log in to access the admin panel")
    st.stop()

# Only show the admin panel content if authenticated
st.title("Admin Panel")

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

# Add logout button in sidebar
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

# Admin sections - reorder the tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Member Management",
    "Contribution Management",
    "Department Management",
    "User Management",
    "Birthday Notifications"  # New tab
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
    departments = get_departments()  # Get departments for mapping

    if members:
        # Create department mapping dictionary
        dept_mapping = {dept['id']: dept['name'] for dept in departments}
        
        # Convert to DataFrame and map departments
        df = pd.DataFrame(members)
        # Map department_id to department name using the mapping
        df['department'] = df['department_id'].map(dept_mapping)
        
        # Create display DataFrame with selected columns
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

with tab4:  # New last tab for User Management
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

# Add the new Birthday Notifications tab
with tab5:
    st.header("Birthday Notification Settings")
    
    # Email Recipients Management
    st.subheader("📧 Manage Notification Recipients")
    
    # Create columns for the email management
    col1, col2 = st.columns(2)

    with col1:
        # Add new email recipient
        with st.form("add_email_recipient"):
            new_email = st.text_input("Add Email Recipient")
            submit = st.form_submit_button("Add Recipient")
            
            if submit and new_email:
                # Validate email format
                if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                    st.error("Please enter a valid email address!")
                else:
                    # Get existing recipients
                    recipients = get_email_recipients()
                    existing_emails = [r['email'] for r in recipients]
                    
                    # Check if email already exists
                    if new_email in existing_emails:
                        st.error("This email is already in the list!")
                    else:
                        # Add new email to database
                        try:
                            if add_email_recipient(new_email):
                                st.success(f"Added {new_email} to recipients!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error adding recipient: {str(e)}")

    with col2:
        # Display and manage existing recipients
        st.subheader("Current Recipients")
        recipients = get_email_recipients()
        
        if recipients:
            for recipient in recipients:
                col_email, col_delete = st.columns([3, 1])
                with col_email:
                    st.text(recipient['email'])
                with col_delete:
                    if st.button("🗑️", key=f"delete_{recipient['email']}"):
                        try:
                            if delete_email_recipient(recipient['email']):
                                st.success(f"Removed {recipient['email']} from recipients!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error removing recipient: {str(e)}")
        else:
            st.info("No recipients configured yet.")

    # Email Testing and Birthday Checks
    st.markdown("---")
    st.subheader("🧪 Test Birthday Email System")
    
    test_col1, test_col2 = st.columns(2)
    
    with test_col1:
        if st.button("📧 Send Test Birthday Email"):
            try:
                # Get email recipients
                recipients = get_email_recipients()
                if not recipients:
                    st.error("Please add at least one email recipient first!")
                else:
                    # Get a sample member and departments for testing
                    members = get_youth_members()
                    departments = get_departments()
                    dept_mapping = {dept['id']: dept['name'] for dept in departments}
                    
                    if members:
                        test_member = members[0]  # Use the first member for testing
                        # Get department name from mapping
                        department_name = dept_mapping.get(test_member['department_id'], 'No Department')
                        
                        # Format the test email
                        test_body = f"""
                        <html>
                        <body style="font-family: Arial, sans-serif;">
                            <h2>🎂 Birthday Notification Test</h2>
                            <p>This is a test email from your Birthday Reminder System.</p>
                            <p>The following member would be notified if it were their birthday:</p>
                            <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px; margin: 10px 0;">
                                <p><strong>Name:</strong> {test_member['full_name']}</p>
                                <p><strong>Birthday:</strong> {test_member['birthday']}</p>
                                <p><strong>Department:</strong> {department_name}</p>
                            </div>
                            <p>If you received this email, your notification system is working correctly! 🎉</p>
                            <p>Best regards,<br>Birthday Reminder System</p>
                        </body>
                        </html>
                        """
                        
                        from utils.email_service import send_birthday_email
                        recipient_emails = [r['email'] for r in recipients]
                        
                        success = send_birthday_email(
                            recipients=recipient_emails,
                            subject="🎉 Birthday Reminder System - Test Email",
                            body=test_body
                        )
                        
                        if success:
                            st.success("Test email sent successfully! ✅")
                            st.info(f"Email sent to: {', '.join(recipient_emails)}")
                        else:
                            st.error("Failed to send test email")
                    else:
                        st.error("No members found in the database for testing")
            except Exception as e:
                st.error(f"Error sending test email: {str(e)}")

    with test_col2:
        if st.button("🔍 Check Email Configuration"):
            try:
                # Display current email settings
                st.info("Checking email configuration...")
                
                # Check SMTP settings
                smtp_server = st.secrets["email"]["smtp_server"]
                smtp_port = st.secrets["email"]["smtp_port"]
                sender_email = st.secrets["email"]["sender_email"]
                
                st.write("📧 SMTP Configuration:")
                st.write(f"- Server: {smtp_server}")
                st.write(f"- Port: {smtp_port}")
                st.write(f"- Sender: {sender_email}")
                
                # Check recipients
                recipients = get_email_recipients()
                if recipients:
                    st.write("📫 Configured Recipients:")
                    for recipient in recipients:
                        st.write(f"- {recipient['email']}")
                else:
                    st.warning("No email recipients configured")
                
            except Exception as e:
                st.error(f"Error checking email configuration: {str(e)}")

    # Upcoming Birthdays Display
    st.markdown("---")
    st.subheader("📅 Upcoming Birthdays")
    
    # Add this CSS and JavaScript at the beginning of the Upcoming Birthdays section
    st.markdown("""
        <style>
        .countdown-container {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            justify-content: flex-end;
        }
        .countdown-box {
            background-color: white;
            color: #1e1b4b;
            padding: 0.5rem;
            border-radius: 0.5rem;
            min-width: 2.5rem;
            text-align: center;
            font-weight: bold;
            font-size: 1.2rem;
        }
        .countdown-separator {
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
        }
        .countdown-label {
            color: #c7d2fe;
            font-size: 0.8rem;
            text-align: center;
            margin-top: 0.25rem;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        members = get_youth_members()
        departments = get_departments()
        dept_mapping = {dept['id']: dept['name'] for dept in departments}
        
        if members:
            today = datetime.now()
            upcoming_birthdays = []
            
            for member in members:
                if member.get('birthday'):
                    # Convert DD/MM to datetime for comparison
                    day, month = member['birthday'].split('/')
                    bday_this_year = datetime(today.year, int(month), int(day))
                    
                    # If birthday has passed this year, look at next year
                    if bday_this_year < today:
                        bday_this_year = datetime(today.year + 1, int(month), int(day))
                    
                    # Calculate days until birthday
                    days_until = (bday_this_year.date() - today.date()).days
                    
                    if 0 <= days_until <= 30:
                        # Calculate weeks and remaining days
                        weeks = days_until // 7
                        remaining_days = days_until % 7
                        
                        upcoming_birthdays.append({
                            'name': member['full_name'],
                            'birthday': member['birthday'],
                            'days_until': days_until,
                            'weeks': weeks,
                            'remaining_days': remaining_days,
                            'department': dept_mapping.get(member['department_id'], 'No Department')
                        })
            
            if upcoming_birthdays:
                # Sort by days until birthday
                upcoming_birthdays.sort(key=lambda x: x['days_until'])
                
                # Create two columns for the birthday cards
                left_col, right_col = st.columns(2)
                
                # Split birthdays into two lists
                total_birthdays = len(upcoming_birthdays)
                mid_point = (total_birthdays + 1) // 2
                
                # Process left column
                with left_col:
                    for idx, birthday in enumerate(upcoming_birthdays[:mid_point]):
                        # Calculate target date
                        day, month = birthday['birthday'].split('/')
                        target_date = datetime.now().replace(month=int(month), day=int(day))
                        
                        # If birthday has passed this year, look at next year
                        if target_date.date() < datetime.now().date():
                            target_date = target_date.replace(year=target_date.year + 1)
                        
                        # Calculate time remaining
                        days = (target_date.date() - datetime.now().date()).days
                        
                        # Get the day name
                        day_name = target_date.strftime("%A")
                        
                        st.markdown(
                            f"""
                            <div style="padding: 1.5rem; border-radius: 0.75rem; margin: 0.75rem 0; 
                                    background-color: #1e1b4b; border: 1px solid #312e81; color: white;">
                                <div style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">
                                    🎈 {birthday['name']}
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <div style="flex: 1;">
                                        <div style="color: #c7d2fe; margin: 0.25rem 0;">
                                            Birthday: {birthday['birthday']} <span style="color: #cf173d; font-weight: bold; font-style: italic;">({day_name})</span>
                                        </div>
                                        <div style="color: #c7d2fe; margin: 0.25rem 0;">
                                            Department: {birthday['department']}
                                        </div>
                                        <div style="color: #6366f1; font-size: 0.875rem; margin-top: 0.25rem;">
                                            Total: {days} {'day' if days == 1 else 'days'}
                                        </div>
                                    </div>
                                    <div style="text-align: right; padding-left: 1rem;">
                                        <div class="countdown-container">
                                            <div>
                                                <div class="countdown-box">{str(days).zfill(2)}</div>
                                                <div class="countdown-label">Days</div>
                                            </div>
                                            <div class="countdown-separator">:</div>
                                            <div>
                                                <div class="countdown-box">00</div>
                                                <div class="countdown-label">Hrs</div>
                                            </div>
                                            <div class="countdown-separator">:</div>
                                            <div>
                                                <div class="countdown-box">00</div>
                                                <div class="countdown-label">Mins</div>
                                            </div>
                                            <div class="countdown-separator">:</div>
                                            <div>
                                                <div class="countdown-box">00</div>
                                                <div class="countdown-label">Sec</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                
                # Process right column
                with right_col:
                    for idx, birthday in enumerate(upcoming_birthdays[mid_point:]):
                        # Calculate target date
                        day, month = birthday['birthday'].split('/')
                        target_date = datetime.now().replace(month=int(month), day=int(day))
                        
                        # If birthday has passed this year, look at next year
                        if target_date.date() < datetime.now().date():
                            target_date = target_date.replace(year=target_date.year + 1)
                        
                        # Calculate time remaining
                        days = (target_date.date() - datetime.now().date()).days
                        
                        # Get the day name
                        day_name = target_date.strftime("%A")
                        
                        st.markdown(
                            f"""
                            <div style="padding: 1.5rem; border-radius: 0.75rem; margin: 0.75rem 0; 
                                    background-color: #1e1b4b; border: 1px solid #312e81; color: white;">
                                <div style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">
                                    🎈 {birthday['name']}
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <div style="flex: 1;">
                                        <div style="color: #c7d2fe; margin: 0.25rem 0;">
                                            Birthday: {birthday['birthday']} <span style="color: #A78BFA; font-weight: bold; font-style: italic;">({day_name})</span>
                                        </div>
                                        <div style="color: #c7d2fe; margin: 0.25rem 0;">
                                            Department: {birthday['department']}
                                        </div>
                                        <div style="color: #6366f1; font-size: 0.875rem; margin-top: 0.25rem;">
                                            Total: {days} {'day' if days == 1 else 'days'}
                                        </div>
                                    </div>
                                    <div style="text-align: right; padding-left: 1rem;">
                                        <div class="countdown-container">
                                            <div>
                                                <div class="countdown-box">{str(days).zfill(2)}</div>
                                                <div class="countdown-label">Days</div>
                                            </div>
                                            <div class="countdown-separator">:</div>
                                            <div>
                                                <div class="countdown-box">00</div>
                                                <div class="countdown-label">Hrs</div>
                                            </div>
                                            <div class="countdown-separator">:</div>
                                            <div>
                                                <div class="countdown-box">00</div>
                                                <div class="countdown-label">Mins</div>
                                            </div>
                                            <div class="countdown-separator">:</div>
                                            <div>
                                                <div class="countdown-box">00</div>
                                                <div class="countdown-label">Sec</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.info("No upcoming birthdays in the next 30 days")
        else:
            st.info("No members found in the database")
    except Exception as e:
        st.error(f"Error displaying upcoming birthdays: {str(e)}")

    # Add this in the test section
    with test_col1:
        st.markdown("### Test Reminder Schedule")
        if st.button("🔄 Test Reminder Schedule"):
            try:
                from utils.email_service import check_and_send_birthday_reminders
                message, success = check_and_send_birthday_reminders()
                
                if success:
                    st.success(message)
                    # Show what would be sent
                    members = get_youth_members()
                    today = datetime.now()
                    
                    st.write("📅 Reminder Schedule Preview:")
                    for member in members:
                        if member.get('birthday'):
                            day, month = member['birthday'].split('/')
                            bday_this_year = datetime(today.year, int(month), int(day))
                            if bday_this_year < today:
                                bday_this_year = datetime(today.year + 1, int(month), int(day))
                            
                            days_until = (bday_this_year.date() - today.date()).days
                            
                            if 0 <= days_until <= 3:
                                st.info(f"""
                                    {member['full_name']} - {member['birthday']}
                                    - Days until birthday: {days_until}
                                    - Will send reminders:
                                        • Morning (9 AM)
                                        • Afternoon (2 PM)
                                """)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error testing reminder schedule: {str(e)}")

    # Add this after your existing birthday notifications section
    st.markdown("---")
    st.subheader("🔄 Automation Monitor")

    monitor_col1, monitor_col2 = st.columns(2)

    with monitor_col1:
        st.markdown("### 📊 System Status")
        
        # Check current time and next run times
        current_time = datetime.now()
        next_morning = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        next_afternoon = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        
        if current_time > next_morning:
            next_morning += timedelta(days=1)
        if current_time > next_afternoon:
            next_afternoon += timedelta(days=1)
        
        next_run = next_morning if next_morning < next_afternoon else next_afternoon
        
        # Display automation status
        st.markdown("""
            <style>
            .status-box {
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 0.5rem 0;
                background-color: #1e1b4b;
                border: 1px solid #312e81;
            }
            .time-info {
                color: #c7d2fe;
                margin: 0.5rem 0;
            }
            </style>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="status-box">
                <div class="time-info">
                    🕒 Current Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                <div class="time-info">
                    ⏰ Next Morning Check: {next_morning.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                <div class="time-info">
                    ⏰ Next Afternoon Check: {next_afternoon.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with monitor_col2:
        st.markdown("### 📝 Recent Activity")
        
        # Show last check time and status
        if 'last_email_check' in st.session_state and st.session_state.last_email_check:
            st.info(f"Last Check: {st.session_state.last_email_check.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.warning("No checks recorded yet")
            
        if 'last_email_status' in st.session_state and st.session_state.last_email_status:
            if "✅" in st.session_state.last_email_status:
                st.success(st.session_state.last_email_status)
            else:
                st.error(st.session_state.last_email_status)
        
        # Add a manual test button
        if st.button("🧪 Run Test Check Now"):
            try:
                from utils.email_service import check_and_send_birthday_reminders
                message, success = check_and_send_birthday_reminders()
                
                # Update session state
                st.session_state.last_email_check = datetime.now()
                st.session_state.last_email_status = f"{'✅' if success else '❌'} {message}"
                
                if success:
                    st.success(f"Test completed: {message}")
                else:
                    st.error(f"Test failed: {message}")
                    
                # Show upcoming birthdays that would trigger notifications
                members = get_youth_members()
                today = datetime.now()
                upcoming = []
                
                for member in members:
                    if member.get('birthday'):
                        day, month = member['birthday'].split('/')
                        bday_this_year = datetime(today.year, int(month), int(day))
                        if bday_this_year < today:
                            bday_this_year = datetime(today.year + 1, int(month), int(day))
                        
                        days_until = (bday_this_year.date() - today.date()).days
                        if 0 <= days_until <= 3:
                            upcoming.append({
                                'name': member['full_name'],
                                'birthday': member['birthday'],
                                'days': days_until
                            })
                
                if upcoming:
                    st.markdown("#### Upcoming Birthdays That Will Trigger Notifications:")
                    for person in sorted(upcoming, key=lambda x: x['days']):
                        st.info(f"""
                            👤 {person['name']}
                            📅 Birthday: {person['birthday']}
                            ⏳ {'Today!' if person['days'] == 0 else f'In {person["days"]} days'}
                        """)
                else:
                    st.info("No upcoming birthdays in the next 3 days")
                    
            except Exception as e:
                st.error(f"Error running test: {str(e)}")

    # Add verification checklist
    st.markdown("---")
    st.markdown("### ✅ System Verification Checklist")
    
    # Check email configuration
    email_config_ok = all(key in st.secrets.get("email", {}) 
                         for key in ["smtp_server", "smtp_port", "sender_email", "sender_password"])
    
    # Check if we have recipients
    recipients = get_email_recipients()
    has_recipients = bool(recipients)
    
    # Check if we have members with birthdays
    members = get_youth_members()
    has_members = bool(members)
    has_birthdays = False
    if members:
        has_birthdays = any(member.get('birthday') for member in members)
    
    checklist_items = {
        "Email Configuration": {
            "status": email_config_ok,
            "message": "Email settings properly configured" if email_config_ok else "Missing email configuration"
        },
        "Email Recipients": {
            "status": has_recipients,
            "message": f"{len(recipients)} recipient(s) configured" if has_recipients else "No email recipients added"
        },
        "Member Data": {
            "status": has_members,
            "message": f"{len(members)} member(s) in database" if has_members else "No members in database"
        },
        "Birthday Data": {
            "status": has_birthdays,
            "message": "Members with birthdays found" if has_birthdays else "No birthday data available"
        }
    }
    
    for item, details in checklist_items.items():
        if details["status"]:
            st.success(f"✅ {item}: {details['message']}")
        else:
            st.error(f"❌ {item}: {details['message']}")

    # Add help information
    st.markdown("---")
    st.markdown("### ℹ️ How Automation Works")
    st.info("""
        The birthday reminder system:
        1. Checks for birthdays twice daily (9 AM and 2 PM)
        2. Sends reminders for birthdays today through 3 days ahead
        3. Requires the application to be running
        4. Uses Gmail SMTP for sending emails
        5. Prevents duplicate notifications
        
        To ensure it's working:
        - Keep the application running
        - Check the status monitor above
        - Verify all checklist items are green
        - Use the test button to verify email delivery
    """)


# # Add auto-refresh to the page
# st.markdown(
#     """
#     <meta http-equiv="refresh" content="1">
#     """,
#     unsafe_allow_html=True
# ) 