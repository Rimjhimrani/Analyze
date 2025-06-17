import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import io
import base64
from matplotlib.figure import Figure
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="PFEP-Based Inventory Analysis System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .status-excess {
        border-left-color: #007bff !important;
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    }
    .status-short {
        border-left-color: #dc3545 !important;
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
    }
    .status-normal {
        border-left-color: #28a745 !important;
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
    }
    .status-total {
        border-left-color: #6c757d !important;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    }
    .admin-section {
        background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        border: 2px solid #ffd54f;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .user-section {
        background: linear-gradient(135deg, #e1f5fe 0%, #b3e5fc 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        border: 2px solid #4fc3f7;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .pfep-info {
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
        padding: 1rem;
        border-radius: 0.8rem;
        border: 2px solid #81c784;
        margin: 1rem 0;
    }
    .error-box {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        padding: 1rem;
        border-radius: 0.8rem;
        border: 2px solid #e57373;
        margin: 1rem 0;
    }
    .graph-description {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #495057;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-section {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 1rem;
        border-radius: 0.8rem;
        border: 2px solid #ffcd39;
        margin: 1rem 0;
    }
    .success-section {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        padding: 1rem;
        border-radius: 0.8rem;
        border: 2px solid #28a745;
        margin: 1rem 0;
    }
    .sidebar .element-container {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

class EnhancedPFEPInventoryAnalyzer:
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
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = []
        if 'pfep_upload_time' not in st.session_state:
            st.session_state.pfep_upload_time = None
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                'default_tolerance': 30,
                'chart_theme': 'plotly',
                'auto_refresh': False
            }
    
    def authenticate_user(self):
        """Enhanced authentication system with better UX"""
        st.sidebar.markdown("### 🔐 Authentication")
        
        if st.session_state.user_role is None:
            role = st.sidebar.selectbox(
                "Select Role", 
                ["Select Role", "Admin", "User"],
                help="Choose your role to access appropriate features"
            )
            
            if role == "Admin":
                with st.sidebar.container():
                    st.markdown("**Admin Login**")
                    password = st.text_input("Admin Password", type="password", key="admin_pass")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔑 Login", key="admin_login"):
                            if password == "Agilomatrix@1234":
                                st.session_state.user_role = "Admin"
                                st.success("✅ Admin authenticated!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid password")
                    with col2:
                        if st.button("🏠 Demo", key="admin_demo"):
                            st.session_state.user_role = "Admin"
                            st.info("🎮 Demo mode activated!")
                            st.rerun()
            
            elif role == "User":
                if st.sidebar.button("👤 Enter as User", key="user_login"):
                    st.session_state.user_role = "User"
                    st.sidebar.success("✅ User access granted!")
                    st.rerun()
        else:
            # User info and logout
            st.sidebar.success(f"✅ **{st.session_state.user_role}** logged in")
            
            # User preferences (for Admin only)
            if st.session_state.user_role == "Admin":
                with st.sidebar.expander("⚙️ Preferences"):
                    st.session_state.user_preferences['default_tolerance'] = st.selectbox(
                        "Default Tolerance", [10, 20, 30, 40, 50], 
                        index=2, key="pref_tolerance"
                    )
                    st.session_state.user_preferences['chart_theme'] = st.selectbox(
                        "Chart Theme", ['plotly', 'plotly_white', 'plotly_dark'],
                        key="pref_theme"
                    )
            
            if st.sidebar.button("🚪 Logout", key="logout_btn"):
                # Clear all session data
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    
    def safe_float_convert(self, value):
        """Enhanced safe float conversion with better error handling"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        
        try:
            str_value = str(value).strip()
            # Remove common formatting
            str_value = str_value.replace(',', '').replace(' ', '').replace('₹', '').replace('$', '')
            
            if str_value.endswith('%'):
                str_value = str_value[:-1]
            
            # Handle negative values in parentheses
            if str_value.startswith('(') and str_value.endswith(')'):
                str_value = '-' + str_value[1:-1]
            
            return float(str_value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert '{value}' to float: {e}")
            return 0.0
    
    def safe_int_convert(self, value):
        """Enhanced safe int conversion"""
        return int(self.safe_float_convert(value))
    
    def load_sample_pfep_data(self):
        """Load enhanced sample PFEP master data"""
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
        
        st.session_state.pfep_upload_time = datetime.now()
        return pfep_data
    
    def load_sample_current_inventory(self):
        """Load enhanced sample current inventory data with more realistic variances"""
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
        
        return [{'Part_No': row[0], 'Description': row[1], 
                'Current_QTY': self.safe_float_convert(row[2]), 
                'Stock_Value': self.safe_int_convert(row[3])} for row in current_sample]
    
    def validate_file_format(self, df, file_type="unknown"):
        """Validate uploaded file format and provide feedback"""
        if df is None or df.empty:
            return False, "File is empty or could not be read"
        
        if df.shape[0] == 0:
            return False, "No data rows found in file"
        
        if df.shape[1] < 2:
            return False, "File must have at least 2 columns"
        
        # Check for common issues
        issues = []
        
        # Check for completely empty columns
        empty_cols = df.columns[df.isnull().all()].tolist()
        if empty_cols:
            issues.append(f"Empty columns found: {empty_cols}")
        
        # Check data quality
        if df.isnull().sum().sum() > (df.shape[0] * df.shape[1] * 0.5):
            issues.append("More than 50% of data is missing")
        
        if issues:
            return False, "Data quality issues: " + "; ".join(issues)
        
        return True, "File format validated successfully"
    
    def standardize_pfep_data(self, df):
        """Enhanced PFEP data standardization with better error handling"""
        if df is None or df.empty:
            return []
        
        # Validate file
        is_valid, message = self.validate_file_format(df, "PFEP")
        if not is_valid:
            st.error(f"❌ PFEP File Validation Error: {message}")
            return []
        
        # Column mapping with more variations
        column_mappings = {
            'part_no': ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code', 'part no', 'partno'],
            'description': ['description', 'item_description', 'part_description', 'desc', 'part description', 'material_description', 'item desc'],
            'rm_qty': ['rm_in_qty', 'rm_qty', 'required_qty', 'norm_qty', 'target_qty', 'rm', 'ri_in_qty', 'rm in qty'],
            'vendor_code': ['vendor_code', 'vendor_id', 'supplier_code', 'supplier_id', 'vendor id'],
            'vendor_name': ['vendor_name', 'vendor', 'supplier_name', 'supplier', 'vendor name'],
            'city': ['city', 'vendor_city', 'supplier_city', 'location'],
            'state': ['state', 'vendor_state', 'supplier_state', 'region']
        }
        
        # Normalize column names
        normalized_columns = {col.lower().strip().replace(' ', '_').replace('-', '_'): col for col in df.columns}
        
        # Find best matching columns
        def find_best_column(possible_names):
            for name in possible_names:
                normalized_name = name.lower().strip().replace(' ', '_').replace('-', '_')
                if normalized_name in normalized_columns:
                    return normalized_columns[normalized_name]
            return None
        
        mapped_columns = {}
        for key, possible_names in column_mappings.items():
            mapped_columns[key] = find_best_column(possible_names)
        
        # Check required columns
        missing_required = []
        if not mapped_columns['part_no']:
            missing_required.append('Part Number')
        if not mapped_columns['rm_qty']:
            missing_required.append('RM IN QTY')
        
        if missing_required:
            st.error(f"❌ Required columns not found: {', '.join(missing_required)}")
            return []
        
        # Process data
        standardized_data = []
        skipped_rows = 0
        
        for idx, record in df.iterrows():
            try:
                part_no = str(record.get(mapped_columns['part_no'], '')).strip()
                rm_qty = self.safe_float_convert(record.get(mapped_columns['rm_qty'], 0))
                
                if part_no and part_no.lower() not in ['nan', '', 'null'] and rm_qty >= 0:
                    item = {
                        'Part_No': part_no,
                        'Description': str(record.get(mapped_columns['description'], '')).strip() if mapped_columns['description'] else '',
                        'RM_IN_QTY': rm_qty,
                        'Vendor_Code': str(record.get(mapped_columns['vendor_code'], '')).strip() if mapped_columns['vendor_code'] else '',
                        'Vendor_Name': str(record.get(mapped_columns['vendor_name'], '')).strip() if mapped_columns['vendor_name'] else '',
                        'City': str(record.get(mapped_columns['city'], '')).strip() if mapped_columns['city'] else '',
                        'State': str(record.get(mapped_columns['state'], '')).strip() if mapped_columns['state'] else ''
                    }
                    standardized_data.append(item)
                else:
                    skipped_rows += 1
                    
            except Exception as e:
                skipped_rows += 1
                logger.warning(f"Error processing row {idx}: {e}")
        
        if skipped_rows > 0:
            st.warning(f"⚠️ Skipped {skipped_rows} rows due to data issues")
        
        st.session_state.pfep_upload_time = datetime.now()
        return standardized_data
    
    def standardize_current_inventory(self, df):
        """Enhanced current inventory standardization"""
        if df is None or df.empty:
            return []
        
        # Validate file
        is_valid, message = self.validate_file_format(df, "Current Inventory")
        if not is_valid:
            st.error(f"❌ Current Inventory File Validation Error: {message}")
            return []
        
        # Column mapping
        column_mappings = {
            'part_no': ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code', 'part no', 'partno'],
            'description': ['description', 'item_description', 'part_description', 'desc', 'part description', 'material_description'],
            'current_qty': ['current_qty', 'qty', 'quantity', 'stock_qty', 'on_hand_qty', 'current quantity', 'current qty'],
            'stock_value': ['stock_value', 'value', 'amount', 'cost', 'inventory_value', 'total_value', 'stock value']
        }
        
        # Normalize and find columns
        normalized_columns = {col.lower().strip().replace(' ', '_').replace('-', '_'): col for col in df.columns}
        
        def find_best_column(possible_names):
            for name in possible_names:
                normalized_name = name.lower().strip().replace(' ', '_').replace('-', '_')
                if normalized_name in normalized_columns:
                    return normalized_columns[normalized_name]
            return None
        
        mapped_columns = {}
        for key, possible_names in column_mappings.items():
            mapped_columns[key] = find_best_column(possible_names)
        
        # Check required columns
        missing_required = []
        if not mapped_columns['part_no']:
            missing_required.append('Part Number')
        if not mapped_columns['current_qty']:
            missing_required.append('Current QTY')
        
        if missing_required:
            st.error(f"❌ Required columns not found: {', '.join(missing_required)}")
            return []
        
        # Process data
        standardized_data = []
        skipped_rows = 0
        
        for idx, record in df.iterrows():
            try:
                part_no = str(record.get(mapped_columns['part_no'], '')).strip()
                current_qty = self.safe_float_convert(record.get(mapped_columns['current_qty'], 0))
                
                if part_no and part_no.lower() not in ['nan', '', 'null'] and current_qty >= 0:
                    item = {
                        'Part_No': part_no,
                        'Description': str(record.get(mapped_columns['description'], '')).strip() if mapped_columns['description'] else '',
                        'Current_QTY': current_qty,
                        'Stock_Value': self.safe_int_convert(record.get(mapped_columns['stock_value'], 0)) if mapped_columns['stock_value'] else 0
                    }
                    standardized_data.append(item)
                else:
                    skipped_rows += 1
                    
            except Exception as e:
                skipped_rows += 1
                logger.warning(f"Error processing row {idx}: {e}")
        
        if skipped_rows > 0:
            st.warning(f"⚠️ Skipped {skipped_rows} rows due to data issues")
        
        return standardized_data
    
    def match_inventory_data(self, pfep_data, current_data):
        """Enhanced matching algorithm with fuzzy matching option"""
        matched_data = []
        unmatched_parts = []
        
        # Create comprehensive lookup
        pfep_lookup = {}
        pfep_by_part_no = {}
        
        for pfep_item in pfep_data:
            part_no = pfep_item['Part_No'].upper().strip()
            desc = pfep_item['Description'].upper().strip()
            
            # Exact match key
            exact_key = (part_no, desc)
            pfep_lookup[exact_key] = pfep_item
            
            # Part number only lookup
            pfep_by_part_no[part_no] = pfep_item
        
        # Match current inventory
        match_stats = {'exact': 0, 'part_only': 0, 'no_match': 0}
        
        for current_item in current_data:
            current_part_no = current_item['Part_No'].upper().strip()
            current_desc = current_item['Description'].upper().strip()
            
            pfep_match = None
            match_type = None
            
            # Try exact match first
            exact_key = (current_part_no, current_desc)
            if exact_key in pfep_lookup:
                pfep_match = pfep_lookup[exact_key]
                match_type = 'exact'
                match_stats['exact'] += 1
            
            # Try part number only match
            elif current_part_no in pfep_by_part_no:
                pfep_match = pfep_by_part_no[current_part_no]
                match_type = 'part_only'
                match_stats['part_only'] += 1
            
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
                    'State': pfep_match['State'],
                    'Match_Type': match_type
                }
                matched_data.append(matched_item)
            else:
                unmatched_parts.append(current_item)
                match_stats['no_match'] += 1
        
        return matched_data, unmatched_parts, match_stats
    
    def calculate_variance(self, current_qty, rm_qty):
        """Enhanced variance calculation with additional metrics"""
        if rm_qty == 0:
            return {'percent': 0, 'absolute': 0, 'ratio': 1}
        
        variance_percent = ((current_qty - rm_qty) / rm_qty) * 100
        variance_absolute = current_qty - rm_qty
        variance_ratio = current_qty / rm_qty if rm_qty != 0 else 1
        
        return {
            'percent': variance_percent,
            'absolute': variance_absolute,
            'ratio': variance_ratio
        }
    
    def determine_status(self, variance_percent, tolerance=30):
        """Enhanced status determination with severity levels"""
        abs_variance = abs(variance_percent)
        
        if abs_variance <= tolerance:
            return 'Within Norms'
        elif variance_percent > tolerance:
            if variance_percent >= tolerance * 2:
                return 'Excess Inventory'  # Could add severity levels here
            return 'Excess Inventory'
        else:
            if abs_variance >= tolerance * 2:
                return 'Short Inventory'  # Could add severity levels here
            return 'Short Inventory'
    
    def process_matched_data(self, matched_data, tolerance):
        """Enhanced data processing with additional analytics"""
        processed_data = []
        summary_data = {
            'Within Norms': {'count': 0, 'value': 0, 'qty_variance': 0},
            'Excess Inventory': {'count': 0, 'value': 0, 'qty_variance': 0},
            'Short Inventory': {'count': 0, 'value': 0, 'qty_variance': 0}
        }
        
        total_rm_qty = sum(item['RM_IN_QTY'] for item in matched_data)
        total_current_qty = sum(item['Current_QTY'] for item in matched_data)
        
        for item in matched_data:
            current_qty = item['Current_QTY']
            rm_qty = item['RM_IN_QTY']
            stock_value = item['Stock_Value']
            
            # Calculate enhanced variance
            variance = self.calculate_variance(current_qty, rm_qty)
            
            # Determine status
            status = self.determine_status(variance['percent'], tolerance)
            
            # Store processed data
            processed_item = {
                'Part_No': item['Part_No'],
                'Description': item['Description'],
                'Current_QTY': current_qty,
                'RM_IN_QTY': rm_qty,
                'Variance_Percent': variance['percent'],
                'Variance_Absolute': variance['absolute'],
                'Variance_Ratio': variance['ratio'],
                'Status': status,
                'Stock_Value': stock_value,
                'Vendor_Code': item['Vendor_Code'],
                'Vendor_Name': item['Vendor_Name'],
                'City': item['City'],
                'State': item['State'],
                'Match_Type': item.get('Match_Type', 'unknown')
            }
            processed_data.append(processed_item)
            
            # Update summary statistics
            summary_data[status]['count'] += 1
            summary_data[status]['value'] += stock_value
            summary_data[status]['qty_variance'] += variance['absolute']
        
        # Calculate overall metrics
        overall_metrics = {
            'total_parts': len(processed_data),
            'total_rm_qty': total_rm_qty,
            'total_current_qty': total_current_qty,
            'overall_variance_percent': ((total_current_qty - total_rm_qty) / total_rm_qty * 100) if total_rm_qty > 0 else 0,
            'total_stock_value': sum(item['Stock_Value'] for item in processed_data),
            'avg_variance': sum(item['Variance_Percent'] for item in processed_data) / len(processed_data) if processed_data else 0
        }
        
        return processed_data, summary_data, overall_metrics
    
    def generate_detailed_report(self, processed_data, summary_data, overall_metrics):
        """Generate comprehensive analysis report"""
        report = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'summary': {
                'total_parts_analyzed': overall_metrics['total_parts'],
                'total_stock_value': overall_metrics['total_stock_value'],
                'overall_variance_percent': overall_metrics['overall_variance_percent'],
                'average_variance': overall_metrics['avg_variance']
            },
            'status_breakdown': {},
            'vendor_analysis': {},
            'location_analysis': {},
            'top_issues': {
                'highest_excess': [],
                'highest_shortage': [],
                'highest_value_variance': []
            }
        }
        
        # Status breakdown
        for status, data in summary_data.items():
            report['status_breakdown'][status] = {
                'count': data['count'],
                'percentage': (data['count'] / overall_metrics['total_parts'] * 100) if overall_metrics['total_parts'] > 0 else 0,
                'total_value': data['value'],
                'avg_variance': data['qty_variance'] / data['count'] if data['count'] > 0 else 0
            }
        
        # Vendor analysis
        vendor_stats = {}
        for item in processed_data:
            vendor = item['Vendor_Name'] or item['Vendor_Code']
            if vendor not in vendor_stats:
                vendor_stats[vendor] = {
                    'total_parts': 0,
                    'total_value': 0,
                    'statuses': {'Within Norms': 0, 'Excess Inventory': 0, 'Short Inventory': 0}
                }
            
            vendor_stats[vendor]['total_parts'] += 1
            vendor_stats[vendor]['total_value'] += item['Stock_Value']
            vendor_stats[vendor]['statuses'][item['Status']] += 1
        
        report['vendor_analysis'] = vendor_stats
        
        # Location analysis
        location_stats = {}
        for item in processed_data:
            location = f"{item['City']}, {item['State']}" if item['City'] and item['State'] else "Unknown"
            if location not in location_stats:
                location_stats[location] = {
                    'total_parts': 0,
                    'total_value': 0,
                    'statuses': {'Within Norms': 0, 'Excess Inventory': 0, 'Short Inventory': 0}
                }
            
            location_stats[location]['total_parts'] += 1
            location_stats[location]['total_value'] += item['Stock_Value']
            location_stats[location]['statuses'][item['Status']] += 1
        
        report['location_analysis'] = location_stats
        
        # Top issues
        sorted_data = sorted(processed_data, key=lambda x: x['Variance_Percent'], reverse=True)
        
        # Highest excess (positive variance)
        excess_items = [item for item in sorted_data if item['Variance_Percent'] > 0][:10]
        report['top_issues']['highest_excess'] = excess_items
        
        # Highest shortage (negative variance)
        shortage_items = sorted([item for item in processed_data if item['Variance_Percent'] < 0], 
                               key=lambda x: x['Variance_Percent'])[:10]
        report['top_issues']['highest_shortage'] = shortage_items
        
        # Highest value variance
        value_variance_items = sorted(processed_data, 
                                    key=lambda x: abs(x['Variance_Absolute'] * x['Stock_Value']), 
                                    reverse=True)[:10]
        report['top_issues']['highest_value_variance'] = value_variance_items
        
        return report
    
    def create_enhanced_visualizations(self, processed_data, summary_data, overall_metrics):
        """Create comprehensive visualizations with Plotly"""
        
        # 1. Status Distribution Pie Chart
        fig_status = px.pie(
            values=[data['count'] for data in summary_data.values()],
            names=list(summary_data.keys()),
            title="Inventory Status Distribution",
            color_discrete_map=self.status_colors,
            hole=0.4
        )
        fig_status.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        )
        fig_status.update_layout(
            template=st.session_state.user_preferences.get('chart_theme', 'plotly'),
            height=400,
            showlegend=True
        )
        
        # 2. Variance Distribution Histogram
        fig_variance = px.histogram(
            x=[item['Variance_Percent'] for item in processed_data],
            nbins=30,
            title="Variance Distribution",
            labels={'x': 'Variance Percentage', 'y': 'Count'},
            color_discrete_sequence=['#1f77b4']
        )
        fig_variance.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Target")
        fig_variance.update_layout(
            template=st.session_state.user_preferences.get('chart_theme', 'plotly'),
            height=400
        )
        
        # 3. Vendor Analysis Bar Chart
        vendor_data = {}
        for item in processed_data:
            vendor = item['Vendor_Name'] or item['Vendor_Code'] or 'Unknown'
            if vendor not in vendor_data:
                vendor_data[vendor] = {'Within Norms': 0, 'Excess Inventory': 0, 'Short Inventory': 0}
            vendor_data[vendor][item['Status']] += 1
        
        vendors = list(vendor_data.keys())[:10]  # Top 10 vendors
        fig_vendor = go.Figure()
        
        for status in ['Within Norms', 'Excess Inventory', 'Short Inventory']:
            fig_vendor.add_trace(go.Bar(
                name=status,
                x=vendors,
                y=[vendor_data[vendor][status] for vendor in vendors],
                marker_color=self.status_colors[status]
            ))
        
        fig_vendor.update_layout(
            title="Inventory Status by Vendor (Top 10)",
            xaxis_title="Vendor",
            yaxis_title="Count",
            barmode='stack',
            template=st.session_state.user_preferences.get('chart_theme', 'plotly'),
            height=500
        )
        
        # 4. Value vs Variance Scatter
        fig_scatter = px.scatter(
            x=[item['Variance_Percent'] for item in processed_data],
            y=[item['Stock_Value'] for item in processed_data],
            color=[item['Status'] for item in processed_data],
            title="Stock Value vs Variance Percentage",
            labels={'x': 'Variance Percentage', 'y': 'Stock Value'},
            color_discrete_map=self.status_colors,
            hover_data=['Part_No', 'Description']
        )
        fig_scatter.add_vline(x=0, line_dash="dash", line_color="gray", annotation_text="Target")
        fig_scatter.update_layout(
            template=st.session_state.user_preferences.get('chart_theme', 'plotly'),
            height=500
        )
        
        # 5. Location Analysis
        location_data = {}
        for item in processed_data:
            location = item['State'] or 'Unknown'
            if location not in location_data:
                location_data[location] = {'Within Norms': 0, 'Excess Inventory': 0, 'Short Inventory': 0}
            location_data[location][item['Status']] += 1
        
        locations = list(location_data.keys())
        fig_location = go.Figure()
        
        for status in ['Within Norms', 'Excess Inventory', 'Short Inventory']:
            fig_location.add_trace(go.Bar(
                name=status,
                x=locations,
                y=[location_data[location][status] for location in locations],
                marker_color=self.status_colors[status]
            ))
        
        fig_location.update_layout(
            title="Inventory Status by State",
            xaxis_title="State",
            yaxis_title="Count",
            barmode='stack',
            template=st.session_state.user_preferences.get('chart_theme', 'plotly'),
            height=400
        )
        
        return {
            'status_distribution': fig_status,
            'variance_histogram': fig_variance,
            'vendor_analysis': fig_vendor,
            'value_variance_scatter': fig_scatter,
            'location_analysis': fig_location
        }
    
    def display_enhanced_metrics(self, summary_data, overall_metrics):
        """Display enhanced metrics cards"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card status-total">
                <h3>📊 Total Parts</h3>
                <h2>{overall_metrics['total_parts']:,}</h2>
                <p>Analyzed Items</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card status-normal">
                <h3>✅ Within Norms</h3>
                <h2>{summary_data['Within Norms']['count']:,}</h2>
                <p>{(summary_data['Within Norms']['count']/overall_metrics['total_parts']*100):.1f}% of total</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card status-excess">
                <h3>📈 Excess</h3>
                <h2>{summary_data['Excess Inventory']['count']:,}</h2>
                <p>{(summary_data['Excess Inventory']['count']/overall_metrics['total_parts']*100):.1f}% of total</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card status-short">
                <h3>📉 Short</h3>
                <h2>{summary_data['Short Inventory']['count']:,}</h2>
                <p>{(summary_data['Short Inventory']['count']/overall_metrics['total_parts']*100):.1f}% of total</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Additional metrics row
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💰 Total Value</h3>
                <h2>₹{overall_metrics['total_stock_value']:,.0f}</h2>
                <p>Stock Value</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col6:
            variance_color = "status-excess" if overall_metrics['overall_variance_percent'] > 0 else "status-short"
            st.markdown(f"""
            <div class="metric-card {variance_color}">
                <h3>📊 Overall Variance</h3>
                <h2>{overall_metrics['overall_variance_percent']:+.1f}%</h2>
                <p>From Target</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col7:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📋 Target Qty</h3>
                <h2>{overall_metrics['total_rm_qty']:,.0f}</h2>
                <p>PFEP Target</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col8:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📦 Current Qty</h3>
                <h2>{overall_metrics['total_current_qty']:,.0f}</h2>
                <p>Actual Stock</p>
            </div>
            """, unsafe_allow_html=True)
    
    def display_data_table(self, processed_data, show_filters=True):
        """Display enhanced data table with filtering options"""
        if not processed_data:
            st.warning("⚠️ No data available to display")
            return
        
        df = pd.DataFrame(processed_data)
        
        if show_filters:
            st.markdown("### 🔍 Filter Options")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=df['Status'].unique(),
                    default=df['Status'].unique(),
                    key="status_filter"
                )
            
            with col2:
                vendor_filter = st.multiselect(
                    "Filter by Vendor",
                    options=df['Vendor_Name'].unique(),
                    default=df['Vendor_Name'].unique(),
                    key="vendor_filter"
                )
            
            with col3:
                variance_range = st.slider(
                    "Variance Range (%)",
                    min_value=float(df['Variance_Percent'].min()),
                    max_value=float(df['Variance_Percent'].max()),
                    value=(float(df['Variance_Percent'].min()), float(df['Variance_Percent'].max())),
                    key="variance_range"
                )
            
            # Apply filters
            filtered_df = df[
                (df['Status'].isin(status_filter)) &
                (df['Vendor_Name'].isin(vendor_filter)) &
                (df['Variance_Percent'] >= variance_range[0]) &
                (df['Variance_Percent'] <= variance_range[1])
            ]
        else:
            filtered_df = df
        
        # Format display columns
        display_df = filtered_df.copy()
        display_df['Variance_Percent'] = display_df['Variance_Percent'].round(2)
        display_df['Stock_Value'] = display_df['Stock_Value'].apply(lambda x: f"₹{x:,.0f}")
        display_df['Current_QTY'] = display_df['Current_QTY'].round(2)
        display_df['RM_IN_QTY'] = display_df['RM_IN_QTY'].round(2)
        
        # Color code the status
        def highlight_status(row):
            if row['Status'] == 'Excess Inventory':
                return ['background-color: #cce5ff'] * len(row)
            elif row['Status'] == 'Short Inventory':
                return ['background-color: #ffcccc'] * len(row)
            elif row['Status'] == 'Within Norms':
                return ['background-color: #ccffcc'] * len(row)
            else:
                return [''] * len(row)
        
        st.markdown(f"### 📋 Detailed Analysis Results ({len(filtered_df)} items)")
        
        # Display summary of filtered data
        if show_filters and len(filtered_df) != len(df):
            st.info(f"Showing {len(filtered_df)} of {len(df)} total items")
        
        # Display the styled dataframe
        styled_df = display_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Export options
        if st.session_state.user_role == "Admin":
            col1, col2 = st.columns(2)
            with col1:
                csv_data = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=f"pfep_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_csv"
                )
            
            with col2:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='PFEP Analysis')
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"pfep_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel"
                )
    
    def run_analysis(self):
        """Main analysis workflow"""
        st.markdown('<div class="main-header">🏭 PFEP-Based Inventory Analysis System</div>', unsafe_allow_html=True)
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.info("👋 Please select your role and login to continue")
            return
        
        # Main application
        if st.session_state.user_role == "Admin":
            self.admin_interface()
        else:
            self.user_interface()
    
    def admin_interface(self):
        """Enhanced Admin interface with full functionality"""
        st.markdown('<div class="admin-section"><h2>🔧 Admin Dashboard</h2></div>', unsafe_allow_html=True)
        
        # Sidebar options
        st.sidebar.markdown("### 📋 Admin Options")
        
        # Data management
        with st.sidebar.expander("📁 Data Management", expanded=True):
            if st.button("🔄 Load Sample Data", key="load_sample"):
                st.session_state.pfep_data = self.load_sample_pfep_data()
                st.session_state.current_data = self.load_sample_current_inventory()
                st.success("✅ Sample data loaded successfully!")
                st.rerun()
            
            if st.button("🗑️ Clear All Data", key="clear_data"):
                st.session_state.pfep_data = None
                st.session_state.current_data = None
                st.session_state.matched_data = None
                st.success("✅ All data cleared!")
                st.rerun()
        
        # File upload section
        st.markdown("### 📤 File Upload")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📋 PFEP Master Data")
            pfep_file = st.file_uploader(
                "Upload PFEP File",
                type=['xlsx', 'csv', 'xls'],
                key="pfep_upload",
                help="Upload your PFEP master data file"
            )
            
            if pfep_file is not None:
                try:
                    if pfep_file.name.endswith('.csv'):
                        df = pd.read_csv(pfep_file)
                    else:
                        df = pd.read_excel(pfep_file)
                    
                    st.session_state.pfep_data = self.standardize_pfep_data(df)
                    if st.session_state.pfep_data:
                        st.success(f"✅ PFEP data loaded: {len(st.session_state.pfep_data)} items")
                        
                        # Show preview
                        with st.expander("👀 Preview PFEP Data"):
                            preview_df = pd.DataFrame(st.session_state.pfep_data[:5])
                            st.dataframe(preview_df, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Error loading PFEP file: {str(e)}")
        
        with col2:
            st.markdown("#### 📦 Current Inventory")
            inventory_file = st.file_uploader(
                "Upload Current Inventory",
                type=['xlsx', 'csv', 'xls'],
                key="inventory_upload",
                help="Upload your current inventory data file"
            )
            
            if inventory_file is not None:
                try:
                    if inventory_file.name.endswith('.csv'):
                        df = pd.read_csv(inventory_file)
                    else:
                        df = pd.read_excel(inventory_file)
                    
                    st.session_state.current_data = self.standardize_current_inventory(df)
                    if st.session_state.current_data:
                        st.success(f"✅ Inventory data loaded: {len(st.session_state.current_data)} items")
                        
                        # Show preview
                        with st.expander("👀 Preview Inventory Data"):
                            preview_df = pd.DataFrame(st.session_state.current_data[:5])
                            st.dataframe(preview_df, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Error loading inventory file: {str(e)}")
        
        # Analysis section
        if st.session_state.pfep_data and st.session_state.current_data:
            st.markdown("### ⚙️ Analysis Configuration")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                tolerance = st.selectbox(
                    "Tolerance Level (%)",
                    [10, 20, 30, 40, 50],
                    index=2,
                    key="tolerance_select",
                    help="Acceptable variance percentage"
                )
            
            with col2:
                if st.button("🔍 Run Analysis", key="run_analysis", type="primary"):
                    with st.spinner("🔄 Processing data..."):
                        # Match data
                        matched_data, unmatched_parts, match_stats = self.match_inventory_data(
                            st.session_state.pfep_data, 
                            st.session_state.current_data
                        )
                        
                        if matched_data:
                            # Process matched data
                            processed_data, summary_data, overall_metrics = self.process_matched_data(
                                matched_data, tolerance
                            )
                            
                            # Store results
                            st.session_state.matched_data = {
                                'processed_data': processed_data,
                                'summary_data': summary_data,
                                'overall_metrics': overall_metrics,
                                'unmatched_parts': unmatched_parts,
                                'match_stats': match_stats,
                                'tolerance': tolerance,
                                'analysis_time': datetime.now()
                            }
                            
                            st.success("✅ Analysis completed successfully!")
                            st.rerun()
                        else:
                            st.error("❌ No matching data found!")
            
            with col3:
                if st.session_state.matched_data:
                    st.success(f"✅ Last analysis: {st.session_state.matched_data['analysis_time'].strftime('%H:%M:%S')}")
        
        # Display results
        if st.session_state.matched_data:
            self.display_analysis_results()
        else:
            st.info("📊 Upload PFEP and Current Inventory files to begin analysis")
    
    def user_interface(self):
        """Enhanced User interface with limited functionality"""
        st.markdown('<div class="user-section"><h2>👤 User Dashboard</h2></div>', unsafe_allow_html=True)
        
        # Load sample data automatically for users
        if not st.session_state.pfep_data:
            st.session_state.pfep_data = self.load_sample_pfep_data()
            st.session_state.current_data = self.load_sample_current_inventory()
        
        # Analysis section
        st.markdown("### ⚙️ Analysis Configuration")
        tolerance = st.selectbox(
            "Tolerance Level (%)",
            [10, 20, 30, 40, 50],
            index=2,
            key="user_tolerance",
            help="Acceptable variance percentage"
        )
        
        if st.button("🔍 Run Analysis", key="user_analysis", type="primary"):
            with st.spinner("🔄 Processing data..."):
                # Match and process data
                matched_data, unmatched_parts, match_stats = self.match_inventory_data(
                    st.session_state.pfep_data, 
                    st.session_state.current_data
                )
                
                if matched_data:
                    processed_data, summary_data, overall_metrics = self.process_matched_data(
                        matched_data, tolerance
                    )
                    
                    st.session_state.matched_data = {
                        'processed_data': processed_data,
                        'summary_data': summary_data,
                        'overall_metrics': overall_metrics,
                        'unmatched_parts': unmatched_parts,
                        'match_stats': match_stats,
                        'tolerance': tolerance,
                        'analysis_time': datetime.now()
                    }
                    
                    st.success("✅ Analysis completed successfully!")
                    st.rerun()
        
        # Display results
        if st.session_state.matched_data:
            self.display_analysis_results(user_mode=True)
        else:
            st.info("📊 Click 'Run Analysis' to view sample data analysis")
    
    def display_analysis_results(self, user_mode=False):
        """Display comprehensive analysis results"""
        data = st.session_state.matched_data
        
        # Analysis info
        st.markdown("### 📊 Analysis Results")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"🕒 Analysis Time: {data['analysis_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            st.info(f"🎯 Tolerance: ±{data['tolerance']}%")
        with col3:
            st.info(f"🔗 Matched: {len(data['processed_data'])} items")
        
        # Metrics
        self.display_enhanced_metrics(data['summary_data'], data['overall_metrics'])
        
        # Charts
        st.markdown("### 📈 Visual Analysis")
        charts = self.create_enhanced_visualizations(
            data['processed_data'], 
            data['summary_data'], 
            data['overall_metrics']
        )
        
        # Display charts in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Status Distribution", 
            "📈 Variance Analysis", 
            "🏭 Vendor Analysis", 
            "💰 Value Analysis",
            "📍 Location Analysis"
        ])
        
        with tab1:
            st.markdown('<div class="graph-description">Distribution of inventory status across all analyzed parts</div>', unsafe_allow_html=True)
            st.plotly_chart(charts['status_distribution'], use_container_width=True)
        
        with tab2:
            st.markdown('<div class="graph-description">Histogram showing the distribution of variance percentages</div>', unsafe_allow_html=True)
            st.plotly_chart(charts['variance_histogram'], use_container_width=True)
        
        with tab3:
            st.markdown('<div class="graph-description">Inventory status breakdown by vendor</div>', unsafe_allow_html=True)
            st.plotly_chart(charts['vendor_analysis'], use_container_width=True)
        
        with tab4:
            st.markdown('<div class="graph-description">Relationship between stock value and variance percentage</div>', unsafe_allow_html=True)
            st.plotly_chart(charts['value_variance_scatter'], use_container_width=True)
        
        with tab5:
            st.markdown('<div class="graph-description">Inventory status distribution by geographic location</div>', unsafe_allow_html=True)
            st.plotly_chart(charts['location_analysis'], use_container_width=True)
        
        # Detailed data table
        show_filters = not user_mode  # Hide filters for users
        self.display_data_table(data['processed_data'], show_filters=show_filters)
        
        # Unmatched items (Admin only)
        if not user_mode and data['unmatched_parts']:
            with st.expander(f"⚠️ Unmatched Items ({len(data['unmatched_parts'])})"):
                unmatched_df = pd.DataFrame(data['unmatched_parts'])
                st.dataframe(unmatched_df, use_container_width=True)
        
        # Match statistics
        if not user_mode:
            with st.expander("📊 Matching Statistics"):
                match_stats = data['match_stats']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Exact Matches", match_stats.get('exact', 0))
                with col2:
                    st.metric("Fuzzy Matches", match_stats.get('fuzzy', 0))
                with col3:
                    st.metric("Total Processed", match_stats.get('total', 0))
                
                # Match rate
                total_parts = len(st.session_state.pfep_data) if st.session_state.pfep_data else 0
                match_rate = (match_stats.get('total', 0) / total_parts * 100) if total_parts > 0 else 0
                st.progress(match_rate / 100)
                st.write(f"Match Rate: {match_rate:.1f}%")

# Main execution
if __name__ == "__main__":
    try:
        analyzer = PFEPInventoryAnalyzer()
        analyzer.run_analysis()
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        st.info("Please refresh the page and try again.")
