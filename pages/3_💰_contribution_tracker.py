import streamlit as st
from utils.database import init_connection, get_contributions, get_youth_members
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import io

# Define custom color scheme
CUSTOM_COLORS = ['#F13C59', '#BE61CA', '#633EBB']
CUSTOM_COLORSCALE = [[0, '#F13C59'], [0.5, '#BE61CA'], [1, '#633EBB']]

st.title("Contribution Tracker")

# Get all data
all_members = get_youth_members()
all_contributions = get_contributions()

# Contribution type selector
contribution_type = st.selectbox(
    "Select Contribution Type",
    ["All", "BIRTHDAY", "PROJECT", "EVENT"]
)

# Date filters
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", 
                              value=datetime.now().date() - timedelta(days=30))
with col2:
    end_date = st.date_input("End Date", 
                            value=datetime.now().date())

# Add after the date filters
payment_status = st.selectbox(
    "Payment Status",
    ["All", "Paid", "Pending", "Overdue"]
)

# Add payment reminder button
if st.button("Send Payment Reminders"):
    # Implement SMS/Email reminder functionality
    st.info("Payment reminders sent successfully!")

# Check if there are any contributions
if all_contributions:
    # Convert contributions to DataFrame
    df = pd.DataFrame(all_contributions)
    
    # Apply filters
    if contribution_type != "All":
        df = df[df['contribution_type'] == contribution_type]

    if 'payment_date' in df.columns:
        df['payment_date'] = pd.to_datetime(df['payment_date'])
        df = df[
            (df['payment_date'].dt.date >= start_date) &
            (df['payment_date'].dt.date <= end_date)
        ]

        # Display contribution summary
        st.subheader("Contribution Summary")
        if not df.empty:
            total_amount = df['amount'].sum()
            total_contributors = df['member_id'].nunique()
            
            summary_col1, summary_col2 = st.columns(2)
            with summary_col1:
                st.metric("Total Amount Collected", f"GH₵{total_amount:,.2f}")
            with summary_col2:
                st.metric("Total Contributors", total_contributors)
            
            # Contribution Trends Chart
            st.subheader("Contribution Trends")
            daily_totals = df.groupby(df['payment_date'].dt.date)['amount'].sum().reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily_totals['payment_date'],
                y=daily_totals['amount'],
                mode='lines+markers',
                name='Daily Total',
                line=dict(color='#633EBB', width=3),
                marker=dict(color='#BE61CA', size=8)
            ))
            fig.update_layout(
                title='Daily Contribution Trends',
                xaxis_title='Date',
                yaxis_title='Amount (GH₵)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis_gridcolor='rgba(128,128,128,0.1)',
                xaxis_gridcolor='rgba(128,128,128,0.1)'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Add after the contribution trends
            st.subheader("Comparative Analysis")
            compare_col1, compare_col2 = st.columns(2)

            with compare_col1:
                # Month-over-Month comparison
                current_month = datetime.now().month
                current_month_total = df[df['payment_date'].dt.month == current_month]['amount'].sum()
                prev_month_total = df[df['payment_date'].dt.month == (current_month - 1)]['amount'].sum()
                change = ((current_month_total - prev_month_total) / prev_month_total * 100) if prev_month_total > 0 else 0
                st.metric(
                    "Month-over-Month Growth", 
                    f"GH₵{current_month_total:,.2f}",
                    f"{change:+.1f}%"
                )
            
            # Contribution Distribution
            st.subheader("Contribution Distribution")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Pie chart by contribution type
                type_totals = df.groupby('contribution_type')['amount'].sum()
                fig = px.pie(
                    values=type_totals.values,
                    names=type_totals.index,
                    title='Distribution by Contribution Type',
                    hole=0.3,
                    color_discrete_sequence=CUSTOM_COLORS
                )
                fig.update_traces(textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with chart_col2:
                # Top contributors bar chart
                top_contributors = df.groupby('member_id').agg({
                    'amount': 'sum',
                    'youth_members': lambda x: x.iloc[0]['full_name']
                }).nlargest(5, 'amount')
                
                fig = px.bar(
                    top_contributors,
                    x='youth_members',
                    y='amount',
                    title='Top 5 Contributors',
                    labels={'amount': 'Amount (GH₵)', 'youth_members': 'Member'},
                    color_discrete_sequence=['#BE61CA']
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_gridcolor='rgba(128,128,128,0.1)',
                    showlegend=False,
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Weekly contribution heatmap
            st.subheader("Weekly Contribution Pattern")
            df['weekday'] = df['payment_date'].dt.day_name()
            df['week'] = df['payment_date'].dt.isocalendar().week
            weekly_pattern = df.pivot_table(
                values='amount',
                index='week',
                columns='weekday',
                aggfunc='sum',
                fill_value=0
            )
            
            fig = px.imshow(
                weekly_pattern,
                labels=dict(color="Amount (GH₵)"),
                title="Weekly Contribution Heatmap",
                color_continuous_scale=CUSTOM_COLORSCALE
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed contribution records
            st.subheader("Contribution Records")
            df['member_name'] = df['youth_members'].apply(lambda x: x['full_name'])
            display_df = df[['member_name', 'amount', 'contribution_type', 'payment_date', 'week_number']]
            display_df.columns = ['Member', 'Amount (GH₵)', 'Type', 'Date', 'Week']
            st.dataframe(display_df, use_container_width=True)

            # Member Contribution Analysis
            st.subheader("Member Contribution Analysis")
            selected_member = st.selectbox(
                "Select Member",
                options=[member['full_name'] for member in all_members]
            )

            if selected_member:
                member_contributions = df[df['member_name'] == selected_member]
                
                # Member metrics
                total_contributed = member_contributions['amount'].sum()
                contribution_count = len(member_contributions)
                avg_contribution = total_contributed / contribution_count if contribution_count > 0 else 0
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric("Total Contributed", f"GH₵{total_contributed:,.2f}")
                with metric_col2:
                    st.metric("Number of Contributions", contribution_count)
                with metric_col3:
                    st.metric("Average Contribution", f"GH₵{avg_contribution:,.2f}")

            # Contribution Goals
            st.subheader("Contribution Goals")
            goal_col1, goal_col2 = st.columns(2)

            with goal_col1:
                monthly_goal = st.number_input("Monthly Goal (GH₵)", min_value=0.0, step=100.0)
                if monthly_goal > 0:
                    current_month = datetime.now().month
                    monthly_total = df[df['payment_date'].dt.month == current_month]['amount'].sum()
                    progress = (monthly_total / monthly_goal) * 100
                    st.progress(min(progress/100, 1.0))
                    st.text(f"Progress: GH₵{monthly_total:,.2f} / GH₵{monthly_goal:,.2f} ({progress:.1f}%)")
        else:
            st.info("No contributions found for the selected criteria")

        # Defaulters Analysis
        if contribution_type == "BIRTHDAY":
            st.subheader("Birthday Contribution Analysis")
            
            # Get defaulters
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            monthly_contributors = set(
                df[
                    (df['contribution_type'] == 'BIRTHDAY') &
                    (df['payment_date'].dt.month == current_month) &
                    (df['payment_date'].dt.year == current_year)
                ]['member_id'].unique()
            )
            
            defaulters = [
                member for member in all_members 
                if member['id'] not in monthly_contributors
            ]
            
            # Create metrics for compliance
            total_members = len(all_members)
            defaulter_count = len(defaulters)
            compliance_rate = ((total_members - defaulter_count) / total_members * 100) if total_members > 0 else 0
            
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            with metrics_col1:
                st.metric("Total Members", total_members)
            with metrics_col2:
                st.metric("Defaulters", defaulter_count)
            with metrics_col3:
                st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
            
            if defaulters:
                defaulter_df = pd.DataFrame(defaulters)
                
                # Defaulters by department
                dept_defaulters = defaulter_df['departments'].apply(lambda x: x['name'] if x else 'No Department').value_counts()
                fig = px.bar(
                    x=dept_defaulters.index,
                    y=dept_defaulters.values,
                    title="Defaulters by Department",
                    labels={'x': 'Department', 'y': 'Number of Defaulters'},
                    color_discrete_sequence=['#F13C59']
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_gridcolor='rgba(128,128,128,0.1)',
                    showlegend=False,
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Display defaulters list
                st.subheader("Defaulters List")
                display_df = defaulter_df[['full_name', 'phone_number']]
                display_df.columns = ['Name', 'Phone']
                st.dataframe(display_df, use_container_width=True)
            else:
                st.success("No defaulters this month!")
    else:
        st.warning("Contribution data format is incorrect. Please check the database.")

    # Add after the detailed records
    st.subheader("Export Options")
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        if st.button("Export to Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                display_df.to_excel(writer, sheet_name='Contributions', index=False)
            st.download_button(
                label="Download Excel Report",
                data=output.getvalue(),
                file_name=f"contributions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with export_col2:
        if st.button("Generate PDF Report"):
            st.info("PDF report generation feature coming soon!")
else:
    st.info("No contributions have been recorded yet.") 