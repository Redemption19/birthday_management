import streamlit as st
from utils.database import init_connection, get_departments, get_youth_members, get_contributions
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Define custom color scheme
CUSTOM_COLORS = ['#FF7300', '#9B3192', '#57167E', '#007ED6']
CUSTOM_COLORSCALE = [[0, '#FF7300'], [0.33, '#9B3192'], [0.66, '#57167E'], [1, '#007ED6']]

st.title("Department Management")

# Get all data
departments = get_departments()
members = get_youth_members()
contributions = get_contributions()

# Convert to DataFrame and handle department names safely
members_df = pd.DataFrame(members)
try:
    # Try the original method first
    members_df['department_name'] = members_df['departments'].apply(lambda x: x['name'] if x else 'No Department')
except (KeyError, TypeError):
    try:
        # Try alternate column name
        members_df['department_name'] = members_df['department'].apply(lambda x: x['name'] if x else 'No Department')
    except (KeyError, TypeError):
        # If both fail, set default
        members_df['department_name'] = 'No Department'
        print("Warning: No department information found in members data")

contrib_df = pd.DataFrame(contributions) if contributions else pd.DataFrame()

# Search and Filter Section
st.subheader("Search & Filter")
search_col1, search_col2 = st.columns([2, 1])

with search_col1:
    search_query = st.text_input("Search by name, phone, or email", "")

with search_col2:
    department = st.selectbox(
        "Select Department",
        ["All Departments"] + [dept['name'] for dept in departments]
    )

# Filter the DataFrame based on search query and department
filtered_df = members_df.copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df['full_name'].str.contains(search_query, case=False, na=False) |
        filtered_df['phone_number'].str.contains(search_query, case=False, na=False) |
        filtered_df['email'].str.contains(search_query, case=False, na=False)
    ]

if department != "All Departments":
    filtered_df = filtered_df[filtered_df['department_name'] == department]

# Overview metrics based on filtered data
st.subheader("Department Overview")
total_members = len(filtered_df)
total_departments = len(departments)
avg_members = total_members / total_departments if total_departments > 0 else 0

metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
with metrics_col1:
    st.metric("Filtered Members", total_members)
with metrics_col2:
    st.metric("Total Departments", total_departments)
with metrics_col3:
    st.metric("Average Members per Department", f"{avg_members:.1f}")

# Department Statistics with Visualizations
st.subheader("Department Statistics")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Member distribution pie chart
    dept_stats = filtered_df['department_name'].value_counts()
    if not dept_stats.empty:
        fig = px.pie(
            values=dept_stats.values,
            names=dept_stats.index,
            title='Member Distribution by Department',
            hole=0.3,
            color_discrete_sequence=CUSTOM_COLORS
        )
        fig.update_traces(textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for pie chart")

with chart_col2:
    # Department size comparison
    if not dept_stats.empty:
        df_bar = pd.DataFrame({
            'Department': dept_stats.index,
            'Members': dept_stats.values
        })
        fig = px.bar(
            df_bar,
            x='Department',
            y='Members',
            title='Department Size Comparison',
            color_discrete_sequence=['#9B3192']
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_gridcolor='rgba(128,128,128,0.1)'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for bar chart")

# Department-specific analysis
if department != "All Departments":
    st.subheader(f"{department} Department Analysis")
    dept_members = filtered_df[filtered_df['department_name'] == department]
    
    if not dept_members.empty:
        # Birthday distribution within department
        st.subheader("Birthday Distribution")
        birthday_months = dept_members['birthday'].apply(lambda x: datetime.strptime(x, '%d/%m').month)
        month_counts = birthday_months.value_counts().sort_index()
        month_names = [datetime(2024, m, 1).strftime('%B') for m in month_counts.index]
        
        fig = px.bar(
            x=month_names,
            y=month_counts.values,
            title=f'Birthday Distribution in {department}',
            labels={'x': 'Month', 'y': 'Number of Members'},
            color_discrete_sequence=['#FF7300']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_gridcolor='rgba(128,128,128,0.1)'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Contribution analysis if data exists
        if not contrib_df.empty:
            st.subheader("Contribution Analysis")
            
            # Get department members' contributions
            dept_member_ids = dept_members['id'].tolist()
            dept_contributions = contrib_df[contrib_df['member_id'].isin(dept_member_ids)]
            
            if not dept_contributions.empty:
                # Monthly contribution trends
                dept_contributions['month'] = pd.to_datetime(dept_contributions['payment_date']).dt.strftime('%B %Y')
                monthly_totals = dept_contributions.groupby('month')['amount'].sum().reset_index()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=monthly_totals['month'],
                    y=monthly_totals['amount'],
                    mode='lines+markers',
                    name='Monthly Total',
                    line=dict(color='#57167E', width=3),
                    marker=dict(color='#9B3192', size=8)
                ))
                fig.update_layout(
                    title=f'Monthly Contribution Trends - {department}',
                    xaxis_title='Month',
                    yaxis_title='Amount (GH₵)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_gridcolor='rgba(128,128,128,0.1)'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Contribution type breakdown
                type_totals = dept_contributions.groupby('contribution_type')['amount'].sum()
                fig = px.pie(
                    values=type_totals.values,
                    names=type_totals.index,
                    title='Contribution Type Distribution',
                    hole=0.3,
                    color_discrete_sequence=CUSTOM_COLORS
                )
                fig.update_traces(textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
                
                # Contribution metrics
                total_contrib = dept_contributions['amount'].sum()
                avg_contrib = total_contrib / len(dept_members)
                contrib_rate = (dept_contributions['member_id'].nunique() / len(dept_members)) * 100
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric("Total Contributions", f"GH₵{total_contrib:,.2f}")
                with metric_col2:
                    st.metric("Average per Member", f"GH₵{avg_contrib:,.2f}")
                with metric_col3:
                    st.metric("Contribution Rate", f"{contrib_rate:.1f}%")
            else:
                st.info("No contributions recorded for this department")
        
        # Member list with enhanced display
        st.subheader("Department Members")
        display_df = dept_members[['full_name', 'birthday', 'phone_number', 'email']]
        display_df.columns = ['Name', 'Birthday', 'Phone', 'Email']
        st.dataframe(display_df, use_container_width=True)
        
        # Export option
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Export Department Members",
            data=csv,
            file_name=f"{department}_members.csv",
            mime="text/csv"
        )
    else:
        st.info(f"No members found in {department} department")
else:
    # Overall department comparison
    st.subheader("Department Comparison")
    
    if not contrib_df.empty:
        # Contribution comparison across departments
        dept_contributions = pd.merge(
            contrib_df,
            filtered_df[['id', 'department_name']],
            left_on='member_id',
            right_on='id'
        )
        
        dept_totals = dept_contributions.groupby('department_name')['amount'].sum().reset_index()
        fig = px.bar(
            dept_totals,
            x='department_name',
            y='amount',
            title='Total Contributions by Department',
            labels={'amount': 'Amount (GH₵)', 'department_name': 'Department'},
            color_discrete_sequence=['#007ED6']
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_gridcolor='rgba(128,128,128,0.1)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Display filtered members
    st.subheader("Filtered Members")
    display_df = filtered_df[['full_name', 'department_name', 'birthday', 'phone_number']]
    display_df.columns = ['Name', 'Department', 'Birthday', 'Phone']
    st.dataframe(display_df, use_container_width=True) 