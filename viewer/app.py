import streamlit as st
import requests
import pandas as pd

# API Base URL
try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
except:
    # Default to localhost if secrets not configured
    API_BASE_URL = "http://localhost:5000"

# Page configuration
st.set_page_config(
    page_title="ExpenseEye Viewer",
    page_icon="💰",
    layout="wide"
)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = None

# App title
st.title("💰 ExpenseEye Analytics Viewer")
st.markdown("---")

# Upload Section
st.header("📤 Upload Bank Statement")

# Privacy notice
st.info("🔒 Privacy-first: Your file is processed temporarily and deleted automatically.")

# File uploader
uploaded_file = st.file_uploader(
    "Upload your bank statement (CSV)",
    type=['csv'],
    help="Upload a CSV file with your bank transactions"
)

# Analyze button
if st.button("Analyze", type="primary", disabled=(uploaded_file is None)):
    with st.spinner("Uploading and processing..."):
        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)
            
            # Prepare multipart form data
            files = {'file': uploaded_file}
            
            # Call upload API
            response = requests.post(
                f"{API_BASE_URL}/upload",
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Store session_id
                    st.session_state['session_id'] = data['session_id']
                    
                    # Show success message with mapping info
                    st.success(f"✅ Uploaded successfully! Loaded {data['transactions_loaded']} transactions.")
                    
                    # Show detected format info
                    if 'mapping_info' in data:
                        mapping = data['mapping_info']
                        with st.expander("📋 Detected CSV Format", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Date Column:** `{mapping.get('date_column', 'N/A')}`")
                                st.write(f"**Description Column:** `{mapping.get('description_column', 'N/A')}`")
                            with col2:
                                st.write(f"**Amount Pattern:** `{mapping.get('amount_pattern', 'N/A')}`")
                                if mapping.get('rows_skipped', 0) > 0:
                                    st.warning(f"⚠️ Skipped {mapping['rows_skipped']} invalid rows")
                else:
                    st.error(f"Upload failed: {data.get('error', 'Unknown error')}")
            else:
                # Try to get error message from response
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', f'Status {response.status_code}')
                    st.error(f"❌ Upload failed: {error_msg}")
                except:
                    st.error(f"❌ Upload failed with status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API. Make sure the backend is running.")
        except requests.exceptions.Timeout:
            st.error("❌ Upload request timed out")
        except Exception as e:
            st.error(f"❌ Upload error: {str(e)}")

st.markdown("---")

# Subscriptions Section
st.header("📅 Recurring Subscriptions")

# Only call API if session_id exists
if st.session_state.get('session_id'):
    try:
        # Call subscriptions API with session_id
        response = requests.get(
            f"{API_BASE_URL}/subscriptions",
            params={'session_id': st.session_state['session_id']},
            timeout=60
        )
        
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
        elif response.status_code == 400:
            st.error("Session expired or invalid. Please upload your file again.")
            st.session_state['session_id'] = None
        else:
            st.error(f"API Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure the backend is running.")
    except requests.exceptions.Timeout:
        st.error("❌ API request timed out")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
else:
    st.info("👆 Please upload a CSV file to view analytics")

st.markdown("---")

# Overspending Section
st.header("📊 Overspending Analysis")

# Only call API if session_id exists
if st.session_state.get('session_id'):
    try:
        # Call overspending API with session_id
        response = requests.get(
            f"{API_BASE_URL}/overspending",
            params={'session_id': st.session_state['session_id']},
            timeout=60
        )
        
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
        elif response.status_code == 400:
            st.error("Session expired or invalid. Please upload your file again.")
            st.session_state['session_id'] = None
        else:
            st.error(f"API Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure the backend is running.")
    except requests.exceptions.Timeout:
        st.error("❌ API request timed out")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
else:
    st.info("👆 Please upload a CSV file to view analytics")

# Footer
st.markdown("---")
st.caption("ExpenseEye Analytics Viewer - Privacy-first analytics with ephemeral storage")
