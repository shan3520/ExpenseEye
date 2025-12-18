import streamlit as st
import requests
import pandas as pd

# API Base URL
API_BASE_URL = st.secrets.get(
    "API_BASE_URL",
    "https://smartspend-xneu.onrender.com"
)

# Page configuration
st.set_page_config(
    page_title="SmartSpend Viewer",
    page_icon="💰",
    layout="wide"
)

# App title
st.title("💰 SmartSpend Analytics Viewer")
st.markdown("---")

# Subscriptions Section
st.header("📅 Recurring Subscriptions")

try:
    # Call subscriptions API
    response = requests.get(f"{API_BASE_URL}/subscriptions", timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success") and data.get("count", 0) > 0:
            subscriptions = data["subscriptions"]
            
            # Convert to DataFrame for display
            df = pd.DataFrame(subscriptions)
            
            # Format amount column (make positive and add currency)
            if 'amount' in df.columns:
                df['amount'] = df['amount'].abs()
                df['amount'] = df['amount'].apply(lambda x: f"₹{x:.2f}")
            
            # Rename columns for better display
            column_mapping = {
                'description': 'Description',
                'amount': 'Amount',
                'frequency': 'Frequency',
                'avg_gap': 'Avg Gap (days)',
                'occurrences': 'Occurrences'
            }
            df = df.rename(columns=column_mapping)
            
            # Display table
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.success(f"Found {len(subscriptions)} recurring subscription(s)")
        else:
            st.info("No recurring subscriptions detected.")
    else:
        st.error(f"API Error: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to API. Make sure the backend is running on http://localhost:5000")
except requests.exceptions.Timeout:
    st.error("❌ API request timed out")
except Exception as e:
    st.error(f"❌ Error: {str(e)}")

st.markdown("---")

# Overspending Section
st.header("📊 Overspending Analysis")

try:
    # Call overspending API
    response = requests.get(f"{API_BASE_URL}/overspending", timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success"):
            summary = data.get("summary", {})
            months = data.get("months", [])
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Analyzed", summary.get("total_analyzed", 0))
            with col2:
                st.metric("Overspending Months", summary.get("overspending_count", 0))
            with col3:
                st.metric("Normal Months", summary.get("normal_count", 0))
            
            st.markdown("###")
            
            # Convert to DataFrame
            if months:
                df = pd.DataFrame(months)
                
                # Format numeric columns
                if 'spending' in df.columns:
                    df['spending'] = df['spending'].apply(lambda x: f"₹{x:.2f}")
                if 'avg_spending' in df.columns:
                    df['avg_spending'] = df['avg_spending'].apply(lambda x: f"₹{x:.2f}")
                if 'pct_deviation' in df.columns:
                    df['pct_deviation'] = df['pct_deviation'].apply(lambda x: f"{x:+.1f}%")
                if 'excess' in df.columns:
                    df['excess'] = df['excess'].apply(lambda x: f"₹{x:.2f}")
                
                # Rename columns
                column_mapping = {
                    'month': 'Month',
                    'spending': 'Spending',
                    'avg_spending': 'Historical Avg',
                    'pct_deviation': 'Deviation',
                    'status': 'Status',
                    'excess': 'Excess Amount'
                }
                df = df.rename(columns=column_mapping)
                
                # Drop std_spending column if present (internal detail)
                if 'std_spending' in df.columns:
                    df = df.drop(columns=['std_spending'])
                
                # Display table with color coding
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No overspending data available.")
        else:
            st.error("API returned unsuccessful response")
    else:
        st.error(f"API Error: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to API. Make sure the backend is running on http://localhost:5000")
except requests.exceptions.Timeout:
    st.error("❌ API request timed out")
except Exception as e:
    st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.caption("SmartSpend Analytics Viewer - Read-only interface for backend API")
