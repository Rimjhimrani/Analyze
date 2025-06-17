import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
import io
import base64
from matplotlib.figure import Figure
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib

# Set page config
st.set_page_config(
    page_title="PFEP-Based Inventory Analysis System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .status-excess {
        border-left-color: #007bff !important;
    }
    .status-short {
        border-left-color: #dc3545 !important;
    }
    .status-normal {
        border-left-color: #28a745 !important;
    }
    .status-total {
        border-left-color: #6c757d !important;
    }
    .admin-section {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    .user-section {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
    }
    .pfep-info {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
    .graph-description {
        background-color: #f8f9fa;
        padding: 0.8rem;
        border-radius: 0.3rem;
        border-left: 3px solid #007bff;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #495057;
    }
</style>
""", unsafe_allow_html=True)

class PFEPInventoryAnalyzer:
    def __init__(self):
        self.status_colors = {
            'Within Norms': '#28a745',      # Green
            'Excess Inventory': '#007bff',   # Blue
            'Short Inventory': '#dc3545'     # Red
        }
        
        # Initialize session states
        if 'pfep_data' not in st.session_state:
            st.session_state.pfep_data = None
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
        if 'matched_data' not in st.session_state:
            st.session_state.matched_data = None
    
    def authenticate_user(self):
        """Simple authentication system"""
        st.sidebar.header("🔐 Authentication")
        
        if st.session_state.user_role is None:
            role = st.sidebar.selectbox("Select Role", ["Select Role", "Admin", "User"])
            
            if role == "Admin":
                password = st.sidebar.text_input("Admin Password", type="password")
                if password == "Agilomatrix@1234":  # Simple password - replace with secure authentication
                    st.session_state.user_role = "Admin"
                    st.sidebar.success("✅ Admin authenticated!")
                    st.rerun()
                elif password:
                    st.sidebar.error("❌ Invalid admin password")
            
            elif role == "User":
                st.session_state.user_role = "User"
                st.sidebar.success("✅ User access granted!")
                st.rerun()
        else:
            st.sidebar.success(f"✅ Logged in as: {st.session_state.user_role}")
            if st.sidebar.button("🚪 Logout"):
                st.session_state.user_role = None
                st.session_state.pfep_data = None
                st.session_state.matched_data = None
                st.rerun()
    
    def safe_float_convert(self, value):
        """Safely convert string to float, handling commas and other formatting"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '').replace(' ', '')
        
        if str_value.endswith('%'):
            str_value = str_value[:-1]
        
        try:
            return float(str_value)
        except (ValueError, TypeError):
            return 0.0
    
    def safe_int_convert(self, value):
        """Safely convert string to int, handling commas and other formatting"""
        if pd.isna(value) or value == '' or value is None:
            return 0
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '').replace(' ', '')
        
        try:
            return int(float(str_value))
        except (ValueError, TypeError):
            return 0
    
    def load_sample_pfep_data(self):
        """Load sample PFEP master data for demonstration"""
        pfep_sample = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", 4.000, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AC0303020105", "RAIN GUTTER PROFILE", 6.000, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", 10.000, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AC0203020077", "Bulb beading LV battery flap", 3.000, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["AC0303020104", "L- PROFILE JAM PILLAR", 20.000, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", 30, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["AA0115120001", "HVPDU ms", 12, "V004", "Vendor_D", "Bangalore", "Karnataka"],
            ["AA0119020017", "REAR TURN INDICATOR", 40, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["AA0119020019", "REVERSING LAMP", 20, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["AA0822010800", "SIDE DISPLAY BOARD", 50, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["BB0101010001", "ENGINE OIL FILTER", 45, "V005", "Vendor_E", "Pune", "Maharashtra"],
            ["BB0202020002", "BRAKE PAD SET", 25, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["CC0303030003", "CLUTCH DISC", 12, "V004", "Vendor_D", "Bangalore", "Karnataka"],
            ["DD0404040004", "SPARK PLUG", 35, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["EE0505050005", "AIR FILTER", 28, "V002", "Vendor_B", "Delhi", "Delhi"],
            ["FF0606060006", "FUEL FILTER", 50, "V005", "Vendor_E", "Pune", "Maharashtra"],
            ["GG0707070007", "TRANSMISSION OIL", 35, "V003", "Vendor_C", "Chennai", "Tamil Nadu"],
            ["HH0808080008", "COOLANT", 30, "V004", "Vendor_D", "Bangalore", "Karnataka"],
            ["II0909090009", "BRAKE FLUID", 12, "V001", "Vendor_A", "Mumbai", "Maharashtra"],
            ["JJ1010101010", "WINDSHIELD WASHER", 25, "V002", "Vendor_B", "Delhi", "Delhi"]
        ]
        
        pfep_data = []
        for row in pfep_sample:
            pfep_data.append({
                'Part_No': row[0],
                'Description': row[1],
                'RM_IN_QTY': self.safe_float_convert(row[2]),
                'Vendor_Code': row[3],
                'Vendor_Name': row[4],
                'City': row[5],
                'State': row[6]
            })
        
        return pfep_data
    
    def load_sample_current_inventory(self):
        """Load sample current inventory data for demonstration"""
        current_sample = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", 5.230, 496],
            ["AC0303020105", "RAIN GUTTER PROFILE", 8.360, 1984],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", 12.500, 2356],
            ["AC0203020077", "Bulb beading LV battery flap", 3.500, 248],
            ["AC0303020104", "L- PROFILE JAM PILLAR", 15.940, 992],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", 25, 1248],
            ["AA0115120001", "HVPDU ms", 18, 1888],
            ["AA0119020017", "REAR TURN INDICATOR", 35, 1512],
            ["AA0119020019", "REVERSING LAMP", 28, 1152],
            ["AA0822010800", "SIDE DISPLAY BOARD", 42, 2496],
            ["BB0101010001", "ENGINE OIL FILTER", 65, 1300],
            ["BB0202020002", "BRAKE PAD SET", 22, 880],
            ["CC0303030003", "CLUTCH DISC", 8, 640],
            ["DD0404040004", "SPARK PLUG", 45, 450],
            ["EE0505050005", "AIR FILTER", 30, 600],
            ["FF0606060006", "FUEL FILTER", 55, 1100],
            ["GG0707070007", "TRANSMISSION OIL", 40, 800],
            ["HH0808080008", "COOLANT", 22, 660],
            ["II0909090009", "BRAKE FLUID", 15, 300],
            ["JJ1010101010", "WINDSHIELD WASHER", 33, 495]
        ]
        
        current_data = []
        for row in current_sample:
            current_data.append({
                'Part_No': row[0],
                'Description': row[1],
                'Current_QTY': self.safe_float_convert(row[2]),
                'Stock_Value': self.safe_int_convert(row[3])
            })
        
        return current_data
    
    def standardize_pfep_data(self, df):
        """Standardize PFEP master data"""
        if df is None or df.empty:
            return []
        
        # Find required columns (case insensitive)
        part_columns = ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code']
        desc_columns = ['description', 'item_description', 'part_description', 'desc', 'part description', 'material_description']
        rm_columns = ['rm_in_qty', 'rm_qty', 'required_qty', 'norm_qty', 'target_qty', 'rm', 'ri_in_qty']
        vendor_code_columns = ['vendor_code', 'vendor_id', 'supplier_code', 'supplier_id']
        vendor_name_columns = ['vendor_name', 'vendor', 'supplier_name', 'supplier']
        city_columns = ['city', 'vendor_city', 'supplier_city']
        state_columns = ['state', 'vendor_state', 'supplier_state']
        
        # Get column names (case insensitive)
        available_columns = {k.lower().replace(' ', '_'): k for k in df.columns}
        
        # Find the best matching columns
        def find_column(column_list):
            for col_name in column_list:
                if col_name in available_columns:
                    return available_columns[col_name]
            return None
        
        part_col = find_column(part_columns)
        desc_col = find_column(desc_columns)
        rm_col = find_column(rm_columns)
        vendor_code_col = find_column(vendor_code_columns)
        vendor_name_col = find_column(vendor_name_columns)
        city_col = find_column(city_columns)
        state_col = find_column(state_columns)
        
        if not part_col:
            st.error("Part Number column not found in PFEP file")
            return []
        
        if not rm_col:
            st.error("RM IN QTY column not found in PFEP file")
            return []
        
        # Process each record
        standardized_data = []
        for _, record in df.iterrows():
            try:
                part_no = str(record.get(part_col, '')).strip()
                rm_qty = self.safe_float_convert(record.get(rm_col, 0))
                
                if part_no and part_no.lower() != 'nan' and rm_qty >= 0:
                    item = {
                        'Part_No': part_no,
                        'Description': str(record.get(desc_col, '')).strip() if desc_col else '',
                        'RM_IN_QTY': rm_qty,
                        'Vendor_Code': str(record.get(vendor_code_col, '')).strip() if vendor_code_col else '',
                        'Vendor_Name': str(record.get(vendor_name_col, '')).strip() if vendor_name_col else '',
                        'City': str(record.get(city_col, '')).strip() if city_col else '',
                        'State': str(record.get(state_col, '')).strip() if state_col else ''
                    }
                    standardized_data.append(item)
                    
            except Exception as e:
                continue
        
        return standardized_data
    
    def standardize_current_inventory(self, df):
        """Standardize current inventory data"""
        if df is None or df.empty:
            return []
        
        # Find required columns (case insensitive)
        part_columns = ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code']
        desc_columns = ['description', 'item_description', 'part_description', 'desc', 'part description', 'material_description']
        qty_columns = ['current_qty', 'qty', 'quantity', 'stock_qty', 'on_hand_qty']
        value_columns = ['stock_value', 'value', 'amount', 'cost', 'inventory_value']
        
        # Get column names (case insensitive)
        available_columns = {k.lower().replace(' ', '_'): k for k in df.columns}
        
        # Find the best matching columns
        def find_column(column_list):
            for col_name in column_list:
                if col_name in available_columns:
                    return available_columns[col_name]
            return None
        
        part_col = find_column(part_columns)
        desc_col = find_column(desc_columns)
        qty_col = find_column(qty_columns)
        value_col = find_column(value_columns)
        
        if not part_col:
            st.error("Part Number column not found in Current Inventory file")
            return []
        
        if not qty_col:
            st.error("Current QTY column not found in Current Inventory file")
            return []
        
        # Process each record
        standardized_data = []
        for _, record in df.iterrows():
            try:
                part_no = str(record.get(part_col, '')).strip()
                current_qty = self.safe_float_convert(record.get(qty_col, 0))
                
                if part_no and part_no.lower() != 'nan' and current_qty >= 0:
                    item = {
                        'Part_No': part_no,
                        'Description': str(record.get(desc_col, '')).strip() if desc_col else '',
                        'Current_QTY': current_qty,
                        'Stock_Value': self.safe_int_convert(record.get(value_col, 0)) if value_col else 0
                    }
                    standardized_data.append(item)
                    
            except Exception as e:
                continue
        
        return standardized_data
    
    def match_inventory_data(self, pfep_data, current_data):
        """Match current inventory with PFEP master data"""
        matched_data = []
        unmatched_parts = []
        
        # Create lookup dictionary for PFEP data
        pfep_lookup = {}
        for pfep_item in pfep_data:
            key = (pfep_item['Part_No'].upper(), pfep_item['Description'].upper())
            pfep_lookup[key] = pfep_item
        
        # Match current inventory with PFEP
        for current_item in current_data:
            part_key = (current_item['Part_No'].upper(), current_item['Description'].upper())
            part_key_no_desc = (current_item['Part_No'].upper(), "")
            
            pfep_match = None
            
            # Try exact match first (Part No + Description)
            if part_key in pfep_lookup:
                pfep_match = pfep_lookup[part_key]
            else:
                # Try Part No only match
                for pfep_key, pfep_item in pfep_lookup.items():
                    if pfep_key[0] == current_item['Part_No'].upper():
                        pfep_match = pfep_item
                        break
            
            if pfep_match:
                matched_item = {
                    'Part_No': current_item['Part_No'],
                    'Description': current_item['Description'] or pfep_match['Description'],
                    'Current_QTY': current_item['Current_QTY'],
                    'RM_IN_QTY': pfep_match['RM_IN_QTY'],
                    'Stock_Value': current_item['Stock_Value'],
                    'Vendor_Code': pfep_match['Vendor_Code'],
                    'Vendor_Name': pfep_match['Vendor_Name'],
                    'City': pfep_match['City'],
                    'State': pfep_match['State']
                }
                matched_data.append(matched_item)
            else:
                unmatched_parts.append(current_item)
        
        return matched_data, unmatched_parts
    
    def calculate_variance(self, current_qty, rm_qty):
        """Calculate variance percentage and absolute value"""
        if rm_qty == 0:
            return 0, 0
        
        variance_percent = ((current_qty - rm_qty) / rm_qty) * 100
        variance_value = current_qty - rm_qty
        return variance_percent, variance_value
    
    def determine_status(self, variance_percent, tolerance):
        """Determine inventory status based on variance and tolerance"""
        if abs(variance_percent) <= tolerance:
            return 'Within Norms'
        elif variance_percent > tolerance:
            return 'Excess Inventory'
        else:
            return 'Short Inventory'
    
    def process_matched_data(self, matched_data, tolerance):
        """Process matched data and calculate analysis"""
        processed_data = []
        summary_data = {
            'Within Norms': {'count': 0, 'value': 0},
            'Excess Inventory': {'count': 0, 'value': 0},
            'Short Inventory': {'count': 0, 'value': 0}
        }
        
        for item in matched_data:
            current_qty = item['Current_QTY']
            rm_qty = item['RM_IN_QTY']
            stock_value = item['Stock_Value']
            
            # Calculate variance
            variance_percent, variance_value = self.calculate_variance(current_qty, rm_qty)
            
            # Determine status
            status = self.determine_status(variance_percent, tolerance)
            
            # Store processed data
            processed_item = {
                'Part_No': item['Part_No'],
                'Description': item['Description'],
                'Current_QTY': current_qty,
                'RM_IN_QTY': rm_qty,
                'Variance_%': variance_percent,
                'Variance_Value': variance_value,
                'Status': status,
                'Stock_Value': stock_value,
                'Vendor_Code': item['Vendor_Code'],
                'Vendor_Name': item['Vendor_Name'],
                'City': item['City'],
                'State': item['State']
            }
            processed_data.append(processed_item)
            
            # Update summary
            summary_data[status]['count'] += 1
            summary_data[status]['value'] += stock_value
        
        return processed_data, summary_data
    
    def get_vendor_summary(self, processed_data):
        """Get summary data by vendor"""
        vendor_summary = {}
        
        for item in processed_data:
            vendor = item['Vendor_Name']
            if vendor not in vendor_summary:
                vendor_summary[vendor] = {
                    'vendor_code': item['Vendor_Code'],
                    'city': item['City'],
                    'state': item['State'],
                    'total_parts': 0,
                    'total_current_qty': 0,
                    'total_rm_qty': 0,
                    'total_value': 0,
                    'short_parts': 0,
                    'excess_parts': 0,
                    'normal_parts': 0,
                    'short_value': 0,
                    'excess_value': 0,
                    'normal_value': 0
                }
            
            vendor_summary[vendor]['total_parts'] += 1
            vendor_summary[vendor]['total_current_qty'] += item['Current_QTY']
            vendor_summary[vendor]['total_rm_qty'] += item['RM_IN_QTY']
            vendor_summary[vendor]['total_value'] += item['Stock_Value']
            
            if item['Status'] == 'Short Inventory':
                vendor_summary[vendor]['short_parts'] += 1
                vendor_summary[vendor]['short_value'] += item['Stock_Value']
            elif item['Status'] == 'Excess Inventory':
                vendor_summary[vendor]['excess_parts'] += 1
                vendor_summary[vendor]['excess_value'] += item['Stock_Value']
            else:
                vendor_summary[vendor]['normal_parts'] += 1
                vendor_summary[vendor]['normal_value'] += item['Stock_Value']
        
        return vendor_summary
    
    def admin_interface(self):
        """Admin interface for PFEP management"""
        st.markdown('<div class="admin-section">🔑 <strong>Admin Panel</strong> - PFEP Master Data Management</div>', unsafe_allow_html=True)
        
        st.subheader("📋 PFEP Master Data Management")
        
        # PFEP file upload
        uploaded_pfep = st.file_uploader(
            "Upload PFEP Master File",
            type=['csv', 'xlsx', 'xls'],
            help="Upload PFEP file with columns: Part No, Description, RM IN QTY, Vendor Code, Vendor Name, City, State",
            key="pfep_upload"
        )
        
        if uploaded_pfep is not None:
            try:
                if uploaded_pfep.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_pfep)
                else:
                    df = pd.read_excel(uploaded_pfep)
                
                pfep_data = self.standardize_pfep_data(df)
                
                if pfep_data:
                    st.session_state.pfep_data = pfep_data
                    st.success(f"✅ PFEP Master Data loaded successfully! {len(pfep_data)} parts found.")
                    
                    # Display PFEP summary
                    st.subheader("📊 PFEP Master Data Summary")
                    pfep_df = pd.DataFrame(pfep_data)
                    st.dataframe(pfep_df.head(10), use_container_width=True)
                    
                    if len(pfep_data) > 10:
                        st.info(f"Showing first 10 rows. Total rows: {len(pfep_data)}")
                else:
                    st.error("❌ No valid PFEP data found in uploaded file")
            
            except Exception as e:
                st.error(f"❌ Error loading PFEP file: {str(e)}")
        
        elif st.session_state.pfep_data is None:
            if st.button("📋 Load Sample PFEP Data (for demonstration)"):
                st.session_state.pfep_data = self.load_sample_pfep_data()
                st.success("✅ Sample PFEP data loaded!")
                st.rerun()
        
        # Display current PFEP status
        if st.session_state.pfep_data:
            st.markdown('<div class="pfep-info">✅ <strong>PFEP Master Data Status:</strong> Active with {} parts</div>'.format(len(st.session_state.pfep_data)), unsafe_allow_html=True)
            
            # PFEP Statistics
            vendors = set(item['Vendor_Name'] for item in st.session_state.pfep_data if item['Vendor_Name'])
            cities = set(item['City'] for item in st.session_state.pfep_data if item['City'])
            states = set(item['State'] for item in st.session_state.pfep_data if item['State'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Parts", len(st.session_state.pfep_data))
            with col2:
                st.metric("Unique Vendors", len(vendors))
            with col3:
                st.metric("Cities", len(cities))
            with col4:
                st.metric("States", len(states))
    
    def user_interface(self):
        """User interface for inventory analysis"""
        st.markdown('<div class="user-section">👤 <strong>User Panel</strong> - Current Inventory Analysis</div>', unsafe_allow_html=True)
        
        # Check if PFEP data is available
        if st.session_state.pfep_data is None:
            st.markdown('<div class="error-box">❌ <strong>PFEP Master Data Required:</strong> Admin must upload PFEP master data first before inventory analysis can be performed.</div>', unsafe_allow_html=True)
            return
        
        st.markdown('<div class="pfep-info">✅ <strong>PFEP Master Data Available:</strong> {} parts loaded</div>'.format(len(st.session_state.pfep_data)), unsafe_allow_html=True)
        
        # Tolerance setting
        tolerance = st.selectbox(
            "Select Tolerance Zone (+/-)",
            options=[10, 20, 30, 40, 50],
            index=2,  # Default to 30%
            format_func=lambda x: f"{x}%"
        )
        
        # Current inventory upload
        uploaded_current = st.file_uploader(
            "Upload Current Inventory File",
            type=['csv', 'xlsx', 'xls'],
            help="Upload current inventory file with columns: Part No, Description, Current QTY, Stock Value",
            key="current_upload"
        )
        
        current_data = None
        
        if uploaded_current is not None:
            try:
                if uploaded_current.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_current)
                else:
                    df = pd.read_excel(uploaded_current)
                
                current_data = self.standardize_current_inventory(df)
                
                if current_data:
                    st.success(f"✅ Current inventory loaded successfully! {len(current_data)} parts found.")
                else:
                    st.error("❌ No valid current inventory data found in uploaded file")
            
            except Exception as e:
                st.error(f"❌ Error loading current inventory file: {str(e)}")
        else:
            if st.button("📋 Load Sample Current Inventory (for demonstration)"):
                current_data = self.load_sample_current_inventory()
                st.success("✅ Sample current inventory loaded!")
        
        # Perform matching and analysis
        if current_data:
            matched_data, unmatched_parts = self.match_inventory_data(st.session_state.pfep_data, current_data)
            
            if matched_data:
                st.session_state.matched_data = matched_data
                
                # Display matching summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Total Current Parts", len(current_data))
                with col2:
                    st.metric("✅ Matched Parts", len(matched_data))
                with col3:
                    st.metric("❌ Unmatched Parts", len(unmatched_parts))
                
                if unmatched_parts:
                    with st.expander("🔍 View Unmatched Parts"):
                        unmatched_df = pd.DataFrame(unmatched_parts)
                        st.dataframe(unmatched_df, use_container_width=True)
                        st.warning("These parts were  not found in PFEP master data and will be excluded from analysis.")
                
                # Process matched data for analysis
                processed_data, summary_data = self.process_matched_data(matched_data, tolerance)
                
                # Display analysis results
                st.subheader("📊 Inventory Analysis Results")
                
                # Summary cards
                total_parts = len(processed_data)
                total_value = sum(item['Stock_Value'] for item in processed_data)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f'''
                    <div class="metric-card status-total">
                        <h3>Total Parts</h3>
                        <h2>{total_parts}</h2>
                        <p>Value: ₹{total_value:,.0f}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with col2:
                    normal_count = summary_data['Within Norms']['count']
                    normal_value = summary_data['Within Norms']['value']
                    st.markdown(f'''
                    <div class="metric-card status-normal">
                        <h3>Within Norms</h3>
                        <h2>{normal_count}</h2>
                        <p>Value: ₹{normal_value:,.0f}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with col3:
                    excess_count = summary_data['Excess Inventory']['count']
                    excess_value = summary_data['Excess Inventory']['value']
                    st.markdown(f'''
                    <div class="metric-card status-excess">
                        <h3>Excess Inventory</h3>
                        <h2>{excess_count}</h2>
                        <p>Value: ₹{excess_value:,.0f}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                with col4:
                    short_count = summary_data['Short Inventory']['count']
                    short_value = summary_data['Short Inventory']['value']
                    st.markdown(f'''
                    <div class="metric-card status-short">
                        <h3>Short Inventory</h3>
                        <h2>{short_count}</h2>
                        <p>Value: ₹{short_value:,.0f}</p>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # Generate and display charts
                self.display_charts(processed_data, summary_data)
                
                # Detailed analysis table
                st.subheader("📋 Detailed Analysis")
                
                # Filter options
                col1, col2, col3 = st.columns(3)
                with col1:
                    status_filter = st.selectbox(
                        "Filter by Status",
                        options=['All'] + list(self.status_colors.keys())
                    )
                
                with col2:
                    vendors = sorted(set(item['Vendor_Name'] for item in processed_data if item['Vendor_Name']))
                    vendor_filter = st.selectbox(
                        "Filter by Vendor",
                        options=['All'] + vendors
                    )
                
                with col3:
                    sort_by = st.selectbox(
                        "Sort by",
                        options=['Part_No', 'Variance_%', 'Stock_Value', 'Current_QTY']
                    )
                
                # Apply filters
                filtered_data = processed_data.copy()
                
                if status_filter != 'All':
                    filtered_data = [item for item in filtered_data if item['Status'] == status_filter]
                
                if vendor_filter != 'All':
                    filtered_data = [item for item in filtered_data if item['Vendor_Name'] == vendor_filter]
                
                # Sort data
                if sort_by == 'Variance_%':
                    filtered_data = sorted(filtered_data, key=lambda x: abs(x['Variance_%']), reverse=True)
                else:
                    filtered_data = sorted(filtered_data, key=lambda x: x[sort_by], reverse=True)
                
                # Display filtered data
                if filtered_data:
                    df_display = pd.DataFrame(filtered_data)
                    
                    # Format columns for better display
                    df_display['Variance_%'] = df_display['Variance_%'].apply(lambda x: f"{x:.1f}%")
                    df_display['Current_QTY'] = df_display['Current_QTY'].apply(lambda x: f"{x:.2f}")
                    df_display['RM_IN_QTY'] = df_display['RM_IN_QTY'].apply(lambda x: f"{x:.2f}")
                    df_display['Stock_Value'] = df_display['Stock_Value'].apply(lambda x: f"₹{x:,.0f}")
                    
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        column_config={
                            "Status": st.column_config.TextColumn(
                                width="small"
                            )
                        }
                    )
                    
                    # Export functionality
                    if st.button("📥 Export Analysis to Excel"):
                        self.export_to_excel(processed_data)
                
                else:
                    st.info("No data matches the selected filters.")
                
                # Vendor-wise summary
                self.display_vendor_summary(processed_data)
    
    def display_charts(self, processed_data, summary_data):
        """Display various charts for inventory analysis"""
        st.subheader("📈 Visual Analytics")
        
        # Status distribution chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="graph-description">📊 <strong>Inventory Status Distribution</strong><br>Shows the count and value distribution across different inventory statuses</div>', unsafe_allow_html=True)
            
            # Pie chart for status distribution by count
            labels = list(summary_data.keys())
            counts = [summary_data[status]['count'] for status in labels]
            colors = [self.status_colors[status] for status in labels]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=counts,
                hole=.3,
                marker_colors=colors,
                textinfo='label+percent+value',
                textposition='auto'
            )])
            
            fig.update_layout(
                title="Status Distribution (Count)",
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown('<div class="graph-description">💰 <strong>Value Distribution by Status</strong><br>Shows the monetary value distribution across different inventory statuses</div>', unsafe_allow_html=True)
            
            # Bar chart for value distribution
            values = [summary_data[status]['value'] for status in labels]
            
            fig = go.Figure(data=[go.Bar(
                x=labels,
                y=values,
                marker_color=colors,
                text=[f"₹{v:,.0f}" for v in values],
                textposition='auto'
            )])
            
            fig.update_layout(
                title="Value Distribution by Status",
                xaxis_title="Status",
                yaxis_title="Value (₹)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Variance analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="graph-description">📊 <strong>Variance Distribution</strong><br>Histogram showing the distribution of variance percentages across all parts</div>', unsafe_allow_html=True)
            
            variances = [item['Variance_%'] for item in processed_data]
            
            fig = go.Figure(data=[go.Histogram(
                x=variances,
                nbinsx=20,
                marker_color='lightblue',
                opacity=0.7
            )])
            
            fig.update_layout(
                title="Variance Distribution",
                xaxis_title="Variance (%)",
                yaxis_title="Frequency",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown('<div class="graph-description">🎯 <strong>Top 10 High Variance Parts</strong><br>Parts with highest absolute variance (positive or negative)</div>', unsafe_allow_html=True)
            
            # Top variance parts
            sorted_by_variance = sorted(processed_data, key=lambda x: abs(x['Variance_%']), reverse=True)[:10]
            
            part_names = [item['Part_No'][:15] + "..." if len(item['Part_No']) > 15 else item['Part_No'] for item in sorted_by_variance]
            variance_values = [item['Variance_%'] for item in sorted_by_variance]
            colors_var = ['red' if v < 0 else 'blue' if v > 0 else 'green' for v in variance_values]
            
            fig = go.Figure(data=[go.Bar(
                x=variance_values,
                y=part_names,
                orientation='h',
                marker_color=colors_var,
                text=[f"{v:.1f}%" for v in variance_values],
                textposition='auto'
            )])
            
            fig.update_layout(
                title="Top 10 High Variance Parts",
                xaxis_title="Variance (%)",
                yaxis_title="Part Number",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Vendor-wise analysis
        vendor_summary = self.get_vendor_summary(processed_data)
        
        if len(vendor_summary) > 1:
            st.markdown('<div class="graph-description">🏭 <strong>Vendor Performance Analysis</strong><br>Comparison of inventory status across different vendors</div>', unsafe_allow_html=True)
            
            vendors = list(vendor_summary.keys())
            short_counts = [vendor_summary[v]['short_parts'] for v in vendors]
            excess_counts = [vendor_summary[v]['excess_parts'] for v in vendors]
            normal_counts = [vendor_summary[v]['normal_parts'] for v in vendors]
            
            fig = go.Figure(data=[
                go.Bar(name='Short Inventory', x=vendors, y=short_counts, marker_color='#dc3545'),
                go.Bar(name='Excess Inventory', x=vendors, y=excess_counts, marker_color='#007bff'),
                go.Bar(name='Within Norms', x=vendors, y=normal_counts, marker_color='#28a745')
            ])
            
            fig.update_layout(
                title="Vendor-wise Inventory Status",
                xaxis_title="Vendor",
                yaxis_title="Number of Parts",
                barmode='stack',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def display_vendor_summary(self, processed_data):
        """Display vendor-wise summary"""
        st.subheader("🏭 Vendor-wise Analysis")
        
        vendor_summary = self.get_vendor_summary(processed_data)
        
        if vendor_summary:
            # Create vendor summary dataframe
            vendor_df_data = []
            for vendor, data in vendor_summary.items():
                vendor_df_data.append({
                    'Vendor_Name': vendor,
                    'Vendor_Code': data['vendor_code'],
                    'City': data['city'],
                    'State': data['state'],
                    'Total_Parts': data['total_parts'],
                    'Short_Parts': data['short_parts'],
                    'Excess_Parts': data['excess_parts'],
                    'Normal_Parts': data['normal_parts'],
                    'Total_Value': data['total_value'],
                    'Short_Value': data['short_value'],
                    'Excess_Value': data['excess_value'],
                    'Normal_Value': data['normal_value']
                })
            
            vendor_df = pd.DataFrame(vendor_df_data)
            
            # Format values for display
            vendor_df['Total_Value'] = vendor_df['Total_Value'].apply(lambda x: f"₹{x:,.0f}")
            vendor_df['Short_Value'] = vendor_df['Short_Value'].apply(lambda x: f"₹{x:,.0f}")
            vendor_df['Excess_Value'] = vendor_df['Excess_Value'].apply(lambda x: f"₹{x:,.0f}")
            vendor_df['Normal_Value'] = vendor_df['Normal_Value'].apply(lambda x: f"₹{x:,.0f}")
            
            st.dataframe(vendor_df, use_container_width=True)
    
    def export_to_excel(self, processed_data):
        """Export analysis results to Excel"""
        try:
            # Create Excel file in memory
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Main analysis sheet
                df = pd.DataFrame(processed_data)
                df.to_excel(writer, sheet_name='Inventory_Analysis', index=False)
                
                # Vendor summary sheet
                vendor_summary = self.get_vendor_summary(processed_data)
                vendor_df_data = []
                for vendor, data in vendor_summary.items():
                    vendor_df_data.append({
                        'Vendor_Name': vendor,
                        'Vendor_Code': data['vendor_code'],
                        'City': data['city'],
                        'State': data['state'],
                        'Total_Parts': data['total_parts'],
                        'Short_Parts': data['short_parts'],
                        'Excess_Parts': data['excess_parts'],
                        'Normal_Parts': data['normal_parts'],
                        'Total_Value': data['total_value'],
                        'Short_Value': data['short_value'],
                        'Excess_Value': data['excess_value'],
                        'Normal_Value': data['normal_value']
                    })
                
                vendor_df = pd.DataFrame(vendor_df_data)
                vendor_df.to_excel(writer, sheet_name='Vendor_Summary', index=False)
            
            # Download button
            output.seek(0)
            st.download_button(
                label="📥 Download Excel Report",
                data=output.getvalue(),
                file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success("✅ Excel report generated successfully!")
            
        except Exception as e:
            st.error(f"❌ Error generating Excel report: {str(e)}")
    
    def run(self):
        """Main application runner"""
        # Header
        st.markdown('<h1 class="main-header">📊 PFEP-Based Inventory Analysis System</h1>', unsafe_allow_html=True)
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.info("👆 Please authenticate using the sidebar to access the system.")
            
            # System information
            st.subheader("ℹ️ System Information")
            st.markdown("""
            **PFEP-Based Inventory Analysis System** helps organizations analyze their current inventory against PFEP (Plan for Every Part) norms.
            
            **Features:**
            - 🔐 **Role-based Access**: Admin and User roles with different permissions
            - 📋 **PFEP Master Data Management**: Admin can upload and manage PFEP master data
            - 📊 **Inventory Analysis**: Users can analyze current inventory against PFEP norms
            - 📈 **Visual Analytics**: Interactive charts and graphs for better insights
            - 🏭 **Vendor Analysis**: Vendor-wise performance tracking
            - 📥 **Export Functionality**: Export analysis results to Excel
            
            **Roles:**
            - **Admin**: Manage PFEP master data, full system access
            - **User**: Perform inventory analysis using existing PFEP data
            
            **File Formats Supported:** CSV, Excel (.xlsx, .xls)
            """)
            
            return
        
        # Main interface based on role
        if st.session_state.user_role == "Admin":
            self.admin_interface()
            
            # Separator
            st.markdown("---")
            
            # Admin can also access user interface
            self.user_interface()
            
        elif st.session_state.user_role == "User":
            self.user_interface()

# Initialize and run the application
if __name__ == "__main__":
    analyzer = PFEPInventoryAnalyzer()
    analyzer.run()
