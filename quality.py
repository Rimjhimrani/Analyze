import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging
import pickle
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.graph-description {
    background-color: #f0f2f6;
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 20px;
    font-style: italic;
    border-left: 4px solid #1f77b4;
}

.metric-container {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.status-card {
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
}

.status-excess {
    background-color: #ffebee;
    border-left: 4px solid #f44336;
}

.status-short {
    background-color: #fff3e0;
    border-left: 4px solid #ff9800;
}

.status-normal {
    background-color: #e8f5e8;
    border-left: 4px solid #4caf50;
}

.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 5px;
    padding: 15px;
    margin: 10px 0;
}

.lock-button {
    background-color: #28a745;
    color: white;
    padding: 10px 20px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
}

.switch-user-button {
    background-color: #007bff;
    color: white;
    padding: 8px 16px;
    border-radius: 5px;
    border: none;
    font-weight: bold;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

class DataPersistence:
    """Handle data persistence across sessions"""
    
    @staticmethod
    def save_data_to_session_state(key, data):
        """Save data with timestamp to session state"""
        st.session_state[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'saved': True
        }
    
    @staticmethod
    def load_data_from_session_state(key):
        """Load data from session state if it exists"""
        if key in st.session_state and isinstance(st.session_state[key], dict):
            return st.session_state[key].get('data')
        return None
    
    @staticmethod
    def is_data_saved(key):
        """Check if data is saved"""
        if key in st.session_state and isinstance(st.session_state[key], dict):
            return st.session_state[key].get('saved', False)
        return False
    
    @staticmethod
    def get_data_timestamp(key):
        """Get data timestamp"""
        if key in st.session_state and isinstance(st.session_state[key], dict):
            return st.session_state[key].get('timestamp')
        return None

class InventoryAnalyzer:
    """Enhanced inventory analysis with comprehensive reporting"""
    
    def __init__(self):
        self.status_colors = {
            'Within Norms': '#4CAF50',    # Green
            'Excess Inventory': '#2196F3', # Blue
            'Short Inventory': '#F44336'   # Red
        }
    
    def analyze_inventory(self, pfep_data, current_inventory, tolerance=30):
        """Analyze ONLY inventory parts that exist in PFEP"""
        results = []
        # Create lookup dictionaries
        pfep_dict = {item['Part_No']: item for item in pfep_data}
        inventory_dict = {item['Part_No']: item for item in current_inventory}
        
        # ✅ Loop over inventory only
        for part_no, inventory_item in inventory_dict.items():
            pfep_item = pfep_dict.get(part_no)
            if not pfep_item:
                continue  # Skip inventory parts not found in PFEP
            current_qty = inventory_item.get('Current_QTY', 0)
            stock_value = inventory_item.get('Stock_Value', 0)
            rm_qty = pfep_item.get('RM_IN_QTY', 0)
            
            # Calculate variance
            # 
            if rm_qty > 0:
                variance_pct = ((current_qty - rm_qty) / rm_qty) * 100
            else:
                variance_pct = 0
            
            variance_value = current_qty - rm_qty
            
            # Determine status
            if abs(variance_pct) <= tolerance:
                status = 'Within Norms'
            elif variance_pct > tolerance:
                status = 'Excess Inventory'
            else:
                status = 'Short Inventory'
            
            result = {
                'Material': part_no,
                'Description': pfep_item.get('Description', ''),
                'QTY': current_qty,
                'RM IN QTY': rm_qty,
                'Stock_Value': stock_value,
                'Variance_%': variance_pct,
                'Variance_Value': variance_value,
                'Status': status,
                'Vendor': pfep_item.get('Vendor_Name', 'Unknown'),
                'Vendor_Code': pfep_item.get('Vendor_Code', ''),
                'City': pfep_item.get('City', ''),
                'State': pfep_item.get('State', '')
            }
            results.append(result)
        return results

class InventoryManagementSystem:
    """Main application class"""
    
    def __init__(self):
        self.analyzer = InventoryAnalyzer()
        self.persistence = DataPersistence()
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
        
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                'default_tolerance': 30,
                'chart_theme': 'plotly'
            }
        
        # Initialize persistent data keys
        self.persistent_keys = [
            'persistent_pfep_data',
            'persistent_pfep_locked',
            'persistent_inventory_data', 
            'persistent_inventory_locked',
            'persistent_analysis_results'
        ]
        
        # Initialize persistent data if not exists
        for key in self.persistent_keys:
            if key not in st.session_state:
                st.session_state[key] = None
    
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
    
    def authenticate_user(self):
        """Enhanced authentication system with better UX and user switching"""
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
            # User info and controls
            st.sidebar.success(f"✅ **{st.session_state.user_role}** logged in")
            
            # Display data status
            self.display_data_status()
            
            # User switching option for Admin
            if st.session_state.user_role == "Admin":
                # ✅ Show PFEP lock status
                pfep_locked = st.session_state.get("persistent_pfep_locked", False)
                st.sidebar.markdown(f"🔒 PFEP Locked: **{pfep_locked}**")
                # ✅ Always show switch role if PFEP is locked
                if pfep_locked:
                    st.sidebar.markdown("### 🔄 Switch Role")
                    if st.sidebar.button("👤 Switch to User View", key="switch_to_user"):
                        st.session_state.user_role = "User"
                        st.sidebar.success("✅ Switched to User view!")
                        st.rerun()
                else:
                    st.sidebar.info("ℹ️ PFEP is not locked. Lock PFEP to allow switching to User.")

            
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
            
            # Logout button
            st.sidebar.markdown("---")
            if st.sidebar.button("🚪 Logout", key="logout_btn"):
                # Only clear user session, not persistent data
                keys_to_keep = self.persistent_keys + ['user_preferences']
                session_copy = {k: v for k, v in st.session_state.items() if k in keys_to_keep}
                
                # Clear all session state
                st.session_state.clear()
                
                # Restore persistent data
                for k, v in session_copy.items():
                    st.session_state[k] = v
                
                st.rerun()
    
    def display_data_status(self):
        """Display current data loading status in sidebar"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Data Status")
        
        # Check persistent PFEP data
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        pfep_locked = st.session_state.get('persistent_pfep_locked', False)
        
        if pfep_data:
            pfep_count = len(pfep_data)
            lock_icon = "🔒" if pfep_locked else "🔓"
            st.sidebar.success(f"✅ PFEP Data: {pfep_count} parts {lock_icon}")
            timestamp = self.persistence.get_data_timestamp('persistent_pfep_data')
            if timestamp:
                st.sidebar.caption(f"Loaded: {timestamp.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.sidebar.error("❌ PFEP Data: Not loaded")
        
        # Check persistent inventory data
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        inventory_locked = st.session_state.get('persistent_inventory_locked', False)
        
        if inventory_data:
            inv_count = len(inventory_data)
            lock_icon = "🔒" if inventory_locked else "🔓"
            st.sidebar.success(f"✅ Inventory: {inv_count} parts {lock_icon}")
            timestamp = self.persistence.get_data_timestamp('persistent_inventory_data')
            if timestamp:
                st.sidebar.caption(f"Loaded: {timestamp.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.sidebar.error("❌ Inventory: Not loaded")
        
        # Analysis results status
        analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
        if analysis_data:
            st.sidebar.info(f"📈 Analysis: {len(analysis_data)} parts analyzed")
    
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
    
    def standardize_pfep_data(self, df):
        """Enhanced PFEP data standardization with better error handling"""
        if df is None or df.empty:
            return []
        
        # Column mapping with more variations
        column_mappings = {
            'part_no': ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code', 'part no', 'partno'],
            'description': ['description', 'item_description', 'part_description', 'desc', 'part description', 'material_description', 'item desc'],
            'rm_qty': ['rm_in_qty', 'rm_qty', 'required_qty', 'norm_qty', 'target_qty', 'rm', 'ri_in_qty', 'rm in qty'],
            'vendor_code': ['vendor_code', 'vendor_id', 'supplier_code', 'supplier_id', 'vendor id'],
            'vendor_name': ['vendor_name', 'vendor', 'supplier_name', 'supplier'],
            'city': ['city', 'location', 'place'],
            'state': ['state', 'region', 'province']
        }
        
        # Find matching columns
        df_columns = [col.lower().strip() for col in df.columns]
        mapped_columns = {}
        
        for key, variations in column_mappings.items():
            for variation in variations:
                if variation in df_columns:
                    original_col = df.columns[df_columns.index(variation)]
                    mapped_columns[key] = original_col
                    break
        
        if 'part_no' not in mapped_columns or 'rm_qty' not in mapped_columns:
            st.error("❌ Required columns not found. Please ensure your file has Part Number and RM Quantity columns.")
            return []
        
        standardized_data = []
        for _, row in df.iterrows():
            item = {
                'Part_No': str(row[mapped_columns['part_no']]).strip(),
                'Description': str(row.get(mapped_columns.get('description', ''), '')).strip(),
                'RM_IN_QTY': self.safe_float_convert(row[mapped_columns['rm_qty']]),
                'Vendor_Code': str(row.get(mapped_columns.get('vendor_code', ''), '')).strip(),
                'Vendor_Name': str(row.get(mapped_columns.get('vendor_name', ''), 'Unknown')).strip(),
                'City': str(row.get(mapped_columns.get('city', ''), '')).strip(),
                'State': str(row.get(mapped_columns.get('state', ''), '')).strip()
            }
            standardized_data.append(item)
        
        return standardized_data
    
    def standardize_current_inventory(self, df):
        """Standardize current inventory data"""
        if df is None or df.empty:
            return []
        
        column_mappings = {
            'part_no': ['part_no', 'part_number', 'material', 'material_code', 'item_code', 'code'],
            'description': ['description', 'item_description', 'part_description', 'desc'],
            'current_qty': ['current_qty', 'qty', 'quantity', 'stock_qty', 'available_qty'],
            'stock_value': ['stock_value', 'value', 'total_value', 'inventory_value']
        }
        
        df_columns = [col.lower().strip() for col in df.columns]
        mapped_columns = {}
        
        for key, variations in column_mappings.items():
            for variation in variations:
                if variation in df_columns:
                    original_col = df.columns[df_columns.index(variation)]
                    mapped_columns[key] = original_col
                    break
        
        if 'part_no' not in mapped_columns or 'current_qty' not in mapped_columns:
            st.error("❌ Required columns not found. Please ensure your file has Part Number and Current Quantity columns.")
            return []
        
        standardized_data = []
        for _, row in df.iterrows():
            item = {
                'Part_No': str(row[mapped_columns['part_no']]).strip(),
                'Description': str(row.get(mapped_columns.get('description', ''), '')).strip(),
                'Current_QTY': self.safe_float_convert(row[mapped_columns['current_qty']]),
                'Stock_Value': self.safe_int_convert(row.get(mapped_columns.get('stock_value', ''), 0))
            }
            standardized_data.append(item)
        
        return standardized_data
    
    def validate_inventory_against_pfep(self, inventory_data):
        """Validate inventory data against PFEP master data"""
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if not pfep_data:
            return {'is_valid': False, 'issues': ['No PFEP data available'], 'warnings': []}
        
        pfep_df = pd.DataFrame(pfep_data)
        inventory_df = pd.DataFrame(inventory_data)
        
        pfep_parts = set(pfep_df['Part_No'])
        inventory_parts = set(inventory_df['Part_No'])
        
        issues = []
        warnings = []
        
        # Check for missing parts in inventory
        missing_parts = pfep_parts - inventory_parts
        
        # Check for extra parts in inventory (not in PFEP)
        extra_parts = inventory_parts - pfep_parts
        
        # Check for data quality issues
        zero_qty_parts = inventory_df[inventory_df['Current_QTY'] == 0]['Part_No'].tolist()
        if zero_qty_parts:
            warnings.append(f"Parts with zero quantity: {len(zero_qty_parts)} parts")
        
        is_valid = len(issues) == 0
        
        return {
            'is_valid': is_valid,
            'issues': issues,
            'warnings': warnings,
            'pfep_parts_count': len(pfep_parts),
            'inventory_parts_count': len(inventory_parts),
            'matching_parts_count': len(pfep_parts & inventory_parts),
            'missing_parts_count': len(missing_parts),
            'extra_parts_count': len(extra_parts)
        }
    
    def admin_data_management(self):
        """Admin-only PFEP data management interface"""
        st.header("🔧 Admin Dashboard - PFEP Data Management")
        
        # Check if PFEP data is locked
        pfep_locked = st.session_state.get('persistent_pfep_locked', False)
        
        if pfep_locked:
            st.warning("🔒 PFEP data is currently locked. Users are working with this data.")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.info("To modify PFEP data, first unlock it. This will reset all user analysis.")
            with col2:
                if st.button("🔓 Unlock Data", type="secondary"):
                    st.session_state.persistent_pfep_locked = False
                    # Clear related data when PFEP is unlocked
                    st.session_state.persistent_inventory_data = None
                    st.session_state.persistent_inventory_locked = False
                    st.session_state.persistent_analysis_results = None
                    st.success("✅ PFEP data unlocked. Users need to re-upload inventory data.")
                    st.rerun()
            with col3:
                if st.button("👤 Go to User View", type="primary", help="Switch to user interface"):
                    st.session_state.user_role = "User"
                    st.rerun()
            
            # Display current PFEP data if available
            pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
            if pfep_data:
                self.display_pfep_data_preview(pfep_data)
            return
        
        # PFEP Data Loading Options
        st.subheader("📋 Load PFEP Master Data")
        
        data_source = st.radio(
            "Choose data source:",
            ["Upload Excel/CSV File", "Use Sample Data"],
            key="pfep_data_source",
            help="Select how you want to load PFEP master data"
        )
        
        if data_source == "Upload Excel/CSV File":
            self.handle_pfep_file_upload()
        else:
            self.handle_pfep_sample_data()
        
        # Display current PFEP data if available
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data:
            self.display_pfep_data_preview(pfep_data)
    
    def handle_pfep_file_upload(self):
        """Handle PFEP file upload with validation"""
        uploaded_file = st.file_uploader(
            "Upload PFEP Master Data",
            type=['xlsx', 'xls', 'csv'],
            help="Upload Excel or CSV file containing PFEP master data",
            key="pfep_file_uploader"
        )
        
        if uploaded_file:
            try:
                # Read file based on type
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.info(f"📄 File loaded: {uploaded_file.name} ({df.shape[0]} rows, {df.shape[1]} columns)")
                
                # Preview raw data
                with st.expander("👀 Preview Raw Data"):
                    st.dataframe(df.head(), use_container_width=True)
                
                # Process and standardize data
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("🔄 Process & Load PFEP Data", type="primary", key="process_pfep_file"):
                        with st.spinner("Processing PFEP data..."):
                            standardized_data = self.standardize_pfep_data(df)
                            
                            if standardized_data:
                                self.persistence.save_data_to_session_state('persistent_pfep_data', standardized_data)
                                st.success(f"✅ Successfully processed {len(standardized_data)} PFEP records!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to process PFEP data. Please check file format.")
                                
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        # Show lock button if data is loaded
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data and not st.session_state.get('persistent_pfep_locked', False):
            with col2:
                if st.button("🔒 Lock PFEP Data", type="secondary", key="lock_pfep_data"):
                    st.session_state.persistent_pfep_locked = True
                    st.success("✅ PFEP data locked! Users can now upload inventory data.")
                    st.rerun()
    
    def handle_pfep_sample_data(self):
        """Handle loading sample PFEP data"""
        st.info("📋 Using sample PFEP master data with 20 parts from various vendors")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("📥 Load Sample PFEP Data", type="primary", key="load_sample_pfep"):
                sample_data = self.load_sample_pfep_data()
                self.persistence.save_data_to_session_state('persistent_pfep_data', sample_data)
                st.success(f"✅ Loaded {len(sample_data)} sample PFEP records!")
                st.rerun()
        
        # Show lock button if data is loaded
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data and not st.session_state.get('persistent_pfep_locked', False):
            with col2:
                if st.button("🔒 Lock PFEP Data", type="secondary", key="lock_sample_pfep"):
                    st.session_state.persistent_pfep_locked = True
                    st.success("✅ PFEP data locked! Users can now upload inventory data.")
                    st.rerun()
    
    def display_pfep_data_preview(self, pfep_data):
        """Display PFEP data preview with enhanced statistics"""
        st.subheader("📊 PFEP Master Data Overview")
        
        df = pd.DataFrame(pfep_data)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Parts", len(df))
        with col2:
            st.metric("Unique Vendors", df['Vendor_Name'].nunique())
        with col3:
            st.metric("Total RM Quantity", f"{df['RM_IN_QTY'].sum():.0f}")
        with col4:
            st.metric("Avg RM per Part", f"{df['RM_IN_QTY'].mean():.1f}")
        
        # Vendor distribution
        vendor_dist = df.groupby('Vendor_Name').agg({
            'Part_No': 'count',
            'RM_IN_QTY': 'sum'
        }).reset_index()
        vendor_dist.columns = ['Vendor', 'Parts Count', 'Total RM Qty']
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏭 Vendor Distribution")
            fig = px.pie(vendor_dist, values='Parts Count', names='Vendor', 
                        title="Parts Distribution by Vendor")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📦 RM Quantity by Vendor")
            fig = px.bar(vendor_dist, x='Vendor', y='Total RM Qty',
                        title="Total RM Quantity by Vendor")
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Data preview table
        with st.expander("🔍 View PFEP Data Details"):
            st.dataframe(
                df.style.format({'RM_IN_QTY': '{:.2f}'}),
                use_container_width=True,
                height=300
            )
    
    def user_inventory_upload(self):
        """User interface for inventory data upload and analysis"""
        st.header("📦 Inventory Analysis Dashboard")
        
        # Check if PFEP data is available and locked
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        pfep_locked = st.session_state.get('persistent_pfep_locked', False)
        
        if not pfep_data or not pfep_locked:
            st.warning("⚠️ PFEP master data is not available or not locked by admin.")
            st.info("Please contact admin to load and lock PFEP master data first.")
            return
        
        # Display PFEP status
        st.success(f"✅ PFEP master data loaded: {len(pfep_data)} parts available")
        
        # Check if inventory is already loaded and locked
        inventory_locked = st.session_state.get('persistent_inventory_locked', False)
        
        if inventory_locked:
            st.info("🔒 Inventory data is locked. Analysis results are available below.")
            self.display_analysis_results()
            return
        
        # Inventory upload section
        st.subheader("📊 Upload Current Inventory Data")
        
        inventory_source = st.radio(
            "Choose inventory data source:",
            ["Upload Excel/CSV File", "Use Sample Data"],
            key="inventory_data_source"
        )
        
        if inventory_source == "Upload Excel/CSV File":
            uploaded_file = st.file_uploader(
                "Upload Current Inventory Data",
                type=['xlsx', 'xls', 'csv'],
                help="Upload Excel or CSV file containing current inventory data",
                key="inventory_file_uploader"
            )
            
            if uploaded_file:
                try:
                    # Read file
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.info(f"📄 File loaded: {uploaded_file.name} ({df.shape[0]} rows, {df.shape[1]} columns)")
                    
                    # Preview raw data
                    with st.expander("👀 Preview Raw Data"):
                        st.dataframe(df.head(), use_container_width=True)
                    
                    # Process inventory data
                    if st.button("🔄 Process & Analyze Inventory", type="primary", key="process_inventory_file"):
                        with st.spinner("Processing inventory data..."):
                            standardized_data = self.standardize_current_inventory(df)
                            
                            if standardized_data:
                                # Validate against PFEP
                                validation = self.validate_inventory_against_pfep(standardized_data)
                                self.display_validation_results(validation)
                                
                                if validation['is_valid'] or st.button("⚠️ Continue Despite Issues", key="force_continue"):
                                    # Save inventory data and perform analysis
                                    self.persistence.save_data_to_session_state('persistent_inventory_data', standardized_data)
                                    self.perform_inventory_analysis()
                                    st.session_state.persistent_inventory_locked = True
                                    st.rerun()
                            else:
                                st.error("❌ Failed to process inventory data.")
                                
                except Exception as e:
                    st.error(f"❌ Error reading file: {str(e)}")
        
        else:  # Sample data
            st.info("📋 Using sample current inventory data")
            if st.button("📥 Load Sample Inventory & Analyze", type="primary", key="load_sample_inventory"):
                sample_data = self.load_sample_current_inventory()
                self.persistence.save_data_to_session_state('persistent_inventory_data', sample_data)
                self.perform_inventory_analysis()
                st.session_state.persistent_inventory_locked = True
                st.success("✅ Sample inventory loaded and analyzed!")
                st.rerun()
    
    def display_validation_results(self, validation):
        """Display inventory validation results"""
        st.subheader("🔍 Data Validation Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PFEP Parts", validation['pfep_parts_count'])
        with col2:
            st.metric("Inventory Parts", validation['inventory_parts_count'])
        with col3:
            st.metric("Matching Parts", validation['matching_parts_count'])
        with col4:
            match_percentage = (validation['matching_parts_count'] / validation['pfep_parts_count']) * 100
            st.metric("Match %", f"{match_percentage:.1f}%")
        
        # Issues and warnings
        if validation['issues']:
            st.error("❌ **Issues Found:**")
            for issue in validation['issues']:
                st.error(f"• {issue}")
        
        if validation['warnings']:
            st.warning("⚠️ **Warnings:**")
            for warning in validation['warnings']:
                st.warning(f"• {warning}")
        
        if validation['is_valid']:
            st.success("✅ **Validation Passed:** Inventory data is compatible with PFEP master data.")
    
    def perform_inventory_analysis(self):
        """Perform comprehensive inventory analysis"""
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        
        if not pfep_data or not inventory_data:
            st.error("❌ Missing data for analysis")
            return
        
        # Get tolerance from user preferences
        tolerance = st.session_state.user_preferences.get('default_tolerance', 30)
        
        # Perform analysis
        with st.spinner("Analyzing inventory..."):
            analysis_results = self.analyzer.analyze_inventory(pfep_data, inventory_data, tolerance)
            self.persistence.save_data_to_session_state('persistent_analysis_results', analysis_results)
        
        st.success(f"✅ Analysis completed for {len(analysis_results)} parts!")
    
    def display_analysis_results(self):
        """Display comprehensive inventory analysis results"""
        analysis_data = self.persistence.load_data_from_session_state('persistent_analysis_results')
        
        if not analysis_data:
            st.error("❌ No analysis results available")
            return
        
        df = pd.DataFrame(analysis_data)
        
        # Analysis controls
        st.subheader("🎛️ Analysis Controls")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            tolerance = st.slider(
                "Tolerance Percentage (%)", 
                min_value=5, max_value=50, 
                value=st.session_state.user_preferences.get('default_tolerance', 30),
                help="Acceptable variance percentage"
            )
        
        with col2:
            if st.button("🔄 Reanalyze", key="reanalyze_btn"):
                self.reanalyze_with_tolerance(tolerance)
                st.rerun()
        
        with col3:
            if st.session_state.user_role == "Admin":
                if st.button("🔓 Reset Data", key="reset_data_btn"):
                    # Reset all data
                    st.session_state.persistent_inventory_data = None
                    st.session_state.persistent_inventory_locked = False
                    st.session_state.persistent_analysis_results = None
                    st.success("✅ Data reset. Ready for new analysis.")
                    st.rerun()
        
        # Key metrics dashboard
        self.display_analysis_metrics(df)
        
        # Charts and visualizations
        self.display_analysis_charts(df)
        
        # Detailed tables
        self.display_analysis_tables(df)
        
        # Export options
        self.display_export_options(df)
    
    def reanalyze_with_tolerance(self, new_tolerance):
        """Reanalyze inventory with new tolerance"""
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        
        if pfep_data and inventory_data:
            with st.spinner(f"Reanalyzing with {new_tolerance}% tolerance..."):
                analysis_results = self.analyzer.analyze_inventory(pfep_data, inventory_data, new_tolerance)
                self.persistence.save_data_to_session_state('persistent_analysis_results', analysis_results)
                st.session_state.user_preferences['default_tolerance'] = new_tolerance
            st.success("✅ Analysis updated!")
    
    def display_analysis_metrics(self, df):
        """Display key analysis metrics"""
        st.subheader("📊 Key Metrics")
        
        # Calculate metrics
        total_parts = len(df)
        within_norms = len(df[df['Status'] == 'Within Norms'])
        excess_inventory = len(df[df['Status'] == 'Excess Inventory'])
        short_inventory = len(df[df['Status'] == 'Short Inventory'])
        
        total_stock_value = df['Stock_Value'].sum()
        excess_value = df[df['Status'] == 'Excess Inventory']['Stock_Value'].sum()
        short_value = df[df['Status'] == 'Short Inventory']['Stock_Value'].sum()
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Total Parts Analyzed", 
                total_parts,
                help="Total number of parts in analysis"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Within Norms", 
                within_norms,
                delta=f"{(within_norms/total_parts)*100:.1f}%"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Excess Inventory", 
                excess_inventory,
                delta=f"{(excess_inventory/total_parts)*100:.1f}%",
                delta_color="inverse"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "Short Inventory", 
                short_inventory,
                delta=f"{(short_inventory/total_parts)*100:.1f}%",
                delta_color="inverse"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Financial metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Stock Value", 
                f"₹{total_stock_value:,.0f}",
                help="Total value of current inventory"
            )
        
        with col2:
            st.metric(
                "Excess Value", 
                f"₹{excess_value:,.0f}",
                delta=f"{(excess_value/total_stock_value)*100:.1f}%" if total_stock_value > 0 else "0%",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "Short Value", 
                f"₹{short_value:,.0f}",
                delta=f"{(short_value/total_stock_value)*100:.1f}%" if total_stock_value > 0 else "0%",
                delta_color="inverse"
            )
    
    def display_analysis_charts(self, df):
        """Display analysis charts and visualizations"""
        st.subheader("📈 Analysis Visualizations")
        
        # Status distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="graph-description">Distribution of parts by inventory status</div>', unsafe_allow_html=True)
            status_counts = df['Status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values, 
                names=status_counts.index,
                title="Inventory Status Distribution",
                color_discrete_map=self.analyzer.status_colors,
                template=st.session_state.user_preferences.get('chart_theme', 'plotly')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown('<div class="graph-description">Financial impact by inventory status</div>', unsafe_allow_html=True)
            status_values = df.groupby('Status')['Stock_Value'].sum().reset_index()
            
            fig = px.bar(
                status_values, 
                x='Status', 
                y='Stock_Value',
                title="Stock Value by Status",
                color='Status',
                color_discrete_map=self.analyzer.status_colors,
                template=st.session_state.user_preferences.get('chart_theme', 'plotly')
            )
            fig.update_layout(yaxis_title="Stock Value (₹)")
            st.plotly_chart(fig, use_container_width=True)
        
        # Variance analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="graph-description">Quantity variance: Current vs Required</div>', unsafe_allow_html=True)
            fig = px.scatter(
                df, 
                x='RM IN QTY', 
                y='QTY',
                color='Status',
                size='Stock_Value',
                hover_data=['Material', 'Variance_%'],
                title="Current vs Required Quantity",
                color_discrete_map=self.analyzer.status_colors,
                template=st.session_state.user_preferences.get('chart_theme', 'plotly')
            )
            # Add diagonal line for perfect match
            max_qty = max(df['RM IN QTY'].max(), df['QTY'].max())
            fig.add_shape(
                type="line",
                x0=0, y0=0, x1=max_qty, y1=max_qty,
                line=dict(color="gray", width=2, dash="dash")
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown('<div class="graph-description">Parts with highest variance percentages</div>', unsafe_allow_html=True)
            # Top 10 variance parts
            top_variance = df.nlargest(10, 'Variance_%')[['Material', 'Variance_%', 'Status']]
            
            fig = px.bar(
                top_variance, 
                x='Variance_%', 
                y='Material',
                color='Status',
                title="Top 10 Variance Parts (%)",
                orientation='h',
                color_discrete_map=self.analyzer.status_colors,
                template=st.session_state.user_preferences.get('chart_theme', 'plotly')
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        
        # Vendor analysis
        if 'Vendor' in df.columns:
            vendor_analysis = df.groupby(['Vendor', 'Status']).size().unstack(fill_value=0).reset_index()
            
            if not vendor_analysis.empty:
                st.markdown('<div class="graph-description">Inventory status distribution by vendor</div>', unsafe_allow_html=True)
                
                fig = px.bar(
                    vendor_analysis.melt(id_vars=['Vendor'], var_name='Status', value_name='Count'),
                    x='Vendor', 
                    y='Count',
                    color='Status',
                    title="Inventory Status by Vendor",
                    color_discrete_map=self.analyzer.status_colors,
                    template=st.session_state.user_preferences.get('chart_theme', 'plotly')
                )
                fig.update_xaxis(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
    
    def display_analysis_tables(self, df):
        """Display detailed analysis tables"""
        st.subheader("📋 Detailed Analysis")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=df['Status'].unique(),
                default=df['Status'].unique(),
                key="status_filter"
            )
        
        with col2:
            if 'Vendor' in df.columns:
                vendor_filter = st.multiselect(
                    "Filter by Vendor",
                    options=df['Vendor'].unique(),
                    default=df['Vendor'].unique(),
                    key="vendor_filter"
                )
            else:
                vendor_filter = []
        
        with col3:
            variance_threshold = st.number_input(
                "Min Variance % (absolute)",
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=5.0,
                key="variance_threshold"
            )
        
        # Apply filters
        filtered_df = df[df['Status'].isin(status_filter)]
        
        if vendor_filter and 'Vendor' in df.columns:
            filtered_df = filtered_df[filtered_df['Vendor'].isin(vendor_filter)]
        
        if variance_threshold > 0:
            filtered_df = filtered_df[abs(filtered_df['Variance_%']) >= variance_threshold]
        
        st.info(f"Showing {len(filtered_df)} of {len(df)} parts")
        
        # Status-specific tables
        for status in ['Short Inventory', 'Excess Inventory', 'Within Norms']:
            if status in status_filter:
                status_df = filtered_df[filtered_df['Status'] == status]
                
                if not status_df.empty:
                    with st.expander(f"📊 {status} ({len(status_df)} parts)", expanded=(status != 'Within Norms')):
                        
                        # Status-specific styling
                        if status == 'Short Inventory':
                            st.markdown('<div class="status-card status-short">', unsafe_allow_html=True)
                            st.markdown("**⚠️ Action Required:** These parts need restocking")
                        elif status == 'Excess Inventory':
                            st.markdown('<div class="status-card status-excess">', unsafe_allow_html=True)
                            st.markdown("**📦 Optimization Opportunity:** Consider reducing these quantities")
                        else:
                            st.markdown('<div class="status-card status-normal">', unsafe_allow_html=True)
                            st.markdown("**✅ Well Managed:** These parts are within acceptable limits")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Display table
                        display_df = status_df.copy()
                        
                        # Format columns for better display
                        display_df = display_df.round({
                            'QTY': 2,
                            'RM IN QTY': 2,
                            'Variance_%': 1,
                            'Variance_Value': 2
                        })
                        
                        st.dataframe(
                            display_df.style.format({
                                'Stock_Value': '₹{:,.0f}',
                                'Variance_%': '{:.1f}%',
                                'QTY': '{:.2f}',
                                'RM IN QTY': '{:.2f}',
                                'Variance_Value': '{:.2f}'
                            }),
                            use_container_width=True,
                            height=min(300, len(status_df) * 35 + 50)
                        )
    
    def display_export_options(self, df):
        """Display data export options"""
        st.subheader("📥 Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export to CSV
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Download analysis results as CSV file"
            )
        
        with col2:
            # Export summary report
            summary_report = self.generate_summary_report(df)
            st.download_button(
                label="📊 Download Summary",
                data=summary_report,
                file_name=f"inventory_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                help="Download executive summary report"
            )
        
        with col3:
            # Email report option (placeholder)
            if st.button("📧 Email Report", help="Send report via email (Feature coming soon)"):
                st.info("📧 Email functionality will be available in the next update!")
    
    def generate_summary_report(self, df):
        """Generate executive summary report"""
        total_parts = len(df)
        within_norms = len(df[df['Status'] == 'Within Norms'])
        excess_inventory = len(df[df['Status'] == 'Excess Inventory'])
        short_inventory = len(df[df['Status'] == 'Short Inventory'])
        
        total_value = df['Stock_Value'].sum()
        excess_value = df[df['Status'] == 'Excess Inventory']['Stock_Value'].sum()
        short_value = df[df['Status'] == 'Short Inventory']['Stock_Value'].sum()
        
        report = f"""
INVENTORY ANALYSIS SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

OVERVIEW:
- Total Parts Analyzed: {total_parts}
- Total Stock Value: ₹{total_value:,.0f}

INVENTORY STATUS:
- Within Norms: {within_norms} parts ({(within_norms/total_parts)*100:.1f}%)
- Excess Inventory: {excess_inventory} parts ({(excess_inventory/total_parts)*100:.1f}%)
- Short Inventory: {short_inventory} parts ({(short_inventory/total_parts)*100:.1f}%)

FINANCIAL IMPACT:
- Excess Stock Value: ₹{excess_value:,.0f} ({(excess_value/total_value)*100:.1f}% of total)
- Short Stock Value: ₹{short_value:,.0f} ({(short_value/total_value)*100:.1f}% of total)

TOP ISSUES:
"""
        
        # Add top excess items
        if excess_inventory > 0:
            top_excess = df[df['Status'] == 'Excess Inventory'].nlargest(5, 'Variance_%')
            report += "\nTop 5 Excess Items:\n"
            for _, row in top_excess.iterrows():
                report += f"- {row['Material']}: {row['Variance_%']:.1f}% over norm (₹{row['Stock_Value']:,.0f})\n"
        
        # Add top shortage items
        if short_inventory > 0:
            top_short = df[df['Status'] == 'Short Inventory'].nsmallest(5, 'Variance_%')
            report += "\nTop 5 Short Items:\n"
            for _, row in top_short.iterrows():
                report += f"- {row['Material']}: {abs(row['Variance_%']):.1f}% under norm (₹{row['Stock_Value']:,.0f})\n"
        
        report += f"\n{'='*50}\nReport generated by Inventory Management System"
        
        return report
    
    def run(self):
        """Main application runner"""
        # Page header
        st.title("📊 Inventory Management System")
        st.markdown("---")
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.info("👋 Please select your role and authenticate to access the system.")
            st.markdown("""
            ### System Features:
            - **Admin Dashboard**: Load and manage PFEP master data
            - **User Interface**: Upload inventory data and view analysis
            - **Real-time Analysis**: Compare current inventory with PFEP requirements
            - **Interactive Visualizations**: Charts and graphs for better insights
            - **Export Capabilities**: Download results in multiple formats
            """)
            return
        
        # Main application logic based on user role
        if st.session_state.user_role == "Admin":
            self.admin_data_management()
        else:  # User role
            self.user_inventory_upload()

# Application entry point
if __name__ == "__main__":
    try:
        app = InventoryManagementSystem()
        app.run()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        logger.error(f"Application crashed: {str(e)}", exc_info=True)
