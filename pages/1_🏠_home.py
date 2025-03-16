import streamlit as st
from utils.database import init_connection, get_youth_members, get_contributions, get_monthly_birthdays, get_departments
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import calendar
from utils.auth import is_admin

# Define custom color scheme
CUSTOM_COLORS = ['#F13C59', '#BE61CA', '#633EBB']
CUSTOM_COLORSCALE = [[0, '#F13C59'], [0.5, '#BE61CA'], [1, '#633EBB']]

st.title("Dashboard")

# # Add this near the top of your file, after the imports
# st.sidebar.write("Debug Information:")
# st.sidebar.write("Authentication Status:", st.session_state.get('authenticated', False))
# st.sidebar.write("User Role:", st.session_state.get('user_role', 'none'))
# st.sidebar.write("Is Admin:", is_admin())

# Initialize connection and get data
supabase = init_connection()
current_month = datetime.now().month
current_month_birthdays = get_monthly_birthdays(current_month)
all_members = get_youth_members()
all_contributions = get_contributions()

# Get departments for mapping
departments = get_departments()
dept_mapping = {dept['id']: dept['name'] for dept in departments}

# Create columns for different metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Youth Members", len(all_members))
    
with col2:
    st.metric("This Month's Birthdays", len(current_month_birthdays))
    
with col3:
    if all_members:
        contributors = len(set(c['member_id'] for c in all_contributions))
        collection_rate = (contributors / len(all_members)) * 100
        st.metric("Contribution Collection Rate", f"{collection_rate:.1f}%")
    else:
        st.metric("Contribution Collection Rate", "0%")

# Create two columns for charts
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Department Distribution Pie Chart
    st.subheader("Members by Department")
    if all_members:
        df = pd.DataFrame(all_members)
        dept_counts = df['department_id'].apply(lambda x: dept_mapping.get(x, 'No Department')).value_counts()
        fig = px.pie(
            values=dept_counts.values,
            names=dept_counts.index,
            hole=0.3,
            color_discrete_sequence=CUSTOM_COLORS
        )
        fig.update_traces(textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No member data available")

with chart_col2:
    # Monthly Contribution Trends
    st.subheader("Monthly Contribution Trends")
    if all_contributions:
        contrib_df = pd.DataFrame(all_contributions)
        contrib_df['month'] = pd.to_datetime(contrib_df['payment_date']).dt.strftime('%B %Y')
        monthly_totals = contrib_df.groupby('month')['amount'].sum().reset_index()
        fig = px.bar(
            monthly_totals,
            x='month',
            y='amount',
            title='Total Contributions by Month',
            labels={'amount': 'Amount (GH₵)', 'month': 'Month'},
            color_discrete_sequence=['#BE61CA']
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_gridcolor='rgba(128,128,128,0.1)',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No contribution data available")

# Birthday Analysis
st.subheader(f"Birthdays in {datetime.now().strftime('%B')}")
if current_month_birthdays:
    birthday_df = pd.DataFrame(current_month_birthdays)
    
    # Create birthday distribution bar chart
    birthday_counts = birthday_df['birthday'].apply(lambda x: int(x.split('/')[0])).value_counts().sort_index()
    
    # Get month length
    month_length = calendar.monthrange(datetime.now().year, current_month)[1]
    
    # Create a complete date range for the month
    all_days = pd.Series(range(1, month_length + 1))
    birthday_counts = birthday_counts.reindex(all_days).fillna(0)
    
    fig = px.bar(
        x=birthday_counts.index,
        y=birthday_counts.values,
        title="Birthday Distribution",
        labels={'x': 'Day of Month', 'y': 'Number of Birthdays'},
        color_discrete_sequence=['#F13C59']
    )
    fig.update_xaxes(tickmode='linear', dtick=1)
    fig.update_layout(
        bargap=0.2,
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_gridcolor='rgba(128,128,128,0.1)',
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Birthday list
    st.subheader("Birthday List")
    if is_admin():
        if current_month_birthdays:
            display_df = birthday_df[['full_name', 'birthday']]
            display_df.columns = ['Name', 'Birthday']
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No birthdays this month")
    else:
        st.warning("⚠️ Detailed birthday information is only visible to administrators.")

# Recent Contributions with Trend
st.subheader("Recent Contributions")
if all_contributions:
    recent_df = pd.DataFrame(all_contributions[-10:])  # Last 10 contributions
    recent_df['member_name'] = recent_df['youth_members'].apply(lambda x: x['full_name'])
    
    # Line chart for contribution trends
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(recent_df['payment_date']),
        y=recent_df['amount'].cumsum(),
        mode='lines+markers',
        name='Cumulative Amount',
        line=dict(color='#633EBB', width=3),
        marker=dict(color='#BE61CA', size=8)
    ))
    fig.update_layout(
        title='Contribution Trend (Last 10 Contributions)',
        xaxis_title='Date',
        yaxis_title='Cumulative Amount (GH₵)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_gridcolor='rgba(128,128,128,0.1)',
        xaxis_gridcolor='rgba(128,128,128,0.1)'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent contributions table - only visible to admins
    if is_admin():
        display_df = recent_df[['member_name', 'amount', 'contribution_type', 'payment_date']]
        display_df.columns = ['Member', 'Amount (GH₵)', 'Type', 'Date']
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("⚠️ Detailed contribution records are only visible to administrators.")
else:
    st.info("No recent contributions")

# Recent Activities
st.subheader("Recent Activities")
# Add recent activities table 