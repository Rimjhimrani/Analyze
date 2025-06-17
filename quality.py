import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging

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
</style>
""", unsafe_allow_html=True)

class InventoryAnalyzer:
    """Enhanced inventory analysis with comprehensive reporting"""
    
    def __init__(self):
        self.status_colors = {
            'Within Norms': '#4CAF50',    # Green
            'Excess Inventory': '#2196F3', # Blue
            'Short Inventory': '#F44336'   # Red
        }
    
    def analyze_inventory(self, pfep_data, current_inventory, tolerance=30):
        """Analyze inventory against PFEP requirements"""
        results = []
        
        # Create lookup dictionaries
        pfep_dict = {item['Part_No']: item for item in pfep_data}
        inventory_dict = {item['Part_No']: item for item in current_inventory}
        
        # Analyze each PFEP item
        for part_no, pfep_item in pfep_dict.items():
            inventory_item = inventory_dict.get(part_no, {})
            
            current_qty = inventory_item.get('Current_QTY', 0)
            rm_qty = pfep_item.get('RM_IN_QTY', 0)
            stock_value = inventory_item.get('Stock_Value', 0)
            
            # Calculate variance
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
            
            # Display data status
            self.display_data_status()
            
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
    
    def display_data_status(self):
        """Display current data loading status in sidebar"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Data Status")
        
        # PFEP Data Status
        if hasattr(st.session_state, 'pfep_data') and st.session_state.pfep_data:
            pfep_count = len(st.session_state.pfep_data)
            pfep_locked = getattr(st.session_state, 'pfep_data_locked', False)
            lock_icon = "🔒" if pfep_locked else "🔓"
            st.sidebar.success(f"✅ PFEP Data: {pfep_count} parts {lock_icon}")
            if hasattr(st.session_state, 'pfep_upload_time'):
                st.sidebar.caption(f"Loaded: {st.session_state.pfep_upload_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.sidebar.error("❌ PFEP Data: Not loaded")
        
        # Current Inventory Status
        if hasattr(st.session_state, 'current_inventory') and st.session_state.current_inventory:
            inv_count = len(st.session_state.current_inventory)
            inv_locked = getattr(st.session_state, 'inventory_data_locked', False)
            lock_icon = "🔒" if inv_locked else "🔓"
            st.sidebar.success(f"✅ Inventory: {inv_count} parts {lock_icon}")
            if hasattr(st.session_state, 'inventory_upload_time'):
                st.sidebar.caption(f"Loaded: {st.session_state.inventory_upload_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.sidebar.error("❌ Inventory: Not loaded")
    
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
        pfep_df = pd.DataFrame(st.session_state.pfep_data)
        inventory_df = pd.DataFrame(inventory_data)
        
        pfep_parts = set(pfep_df['Part_No'])
        inventory_parts = set(inventory_df['Part_No'])
        
        issues = []
        warnings = []
        
        # Check for missing parts in inventory
        missing_parts = pfep_parts - inventory_parts
        if missing_parts:
            issues.append(f"Missing parts in inventory: {len(missing_parts)} parts not found")
            if len(missing_parts) <= 10:
                issues.append(f"Missing parts: {', '.join(list(missing_parts)[:10])}")
        
        # Check for extra parts in inventory (not in PFEP)
        extra_parts = inventory_parts - pfep_parts
        if extra_parts:
            warnings.append(f"Extra parts in inventory: {len(extra_parts)} parts not in PFEP")
            if len(extra_parts) <= 10:
                warnings.append(f"Extra parts: {', '.join(list(extra_parts)[:10])}")
        
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
        pfep_locked = getattr(st.session_state, 'pfep_data_locked', False)
        
        if pfep_locked:
            st.warning("🔒 PFEP data is currently locked. Users are working with this data.")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("To modify PFEP data, first unlock it. This will reset all user analysis.")
            with col2:
                if st.button("🔓 Unlock Data", type="secondary"):
                    st.session_state.pfep_data_locked = False
                    # Clear user inventory data when PFEP is unlocked
                    if hasattr(st.session_state, 'current_inventory'):
                        del st.session_state.current_inventory
                    if hasattr(st.session_state, 'inventory_data_locked'):
                        del st.session_state.inventory_data_locked
                    st.success("✅ PFEP data unlocked. Users need to re-upload inventory data.")
                    st.rerun()
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
        if hasattr(st.session_state, 'pfep_data') and st.session_state.pfep_data:
            self.display_pfep_data_preview()
    
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
                if st.button("🔄 Process & Load PFEP Data", type="primary"):
                    with st.spinner("Processing PFEP data..."):
                        standardized_data = self.standardize_pfep_data(df)
                        
                        if standardized_data:
                            st.session_state.pfep_data = standardized_data
                            st.session_state.pfep_upload_time = datetime.now()
                            st.success(f"✅ Successfully processed {len(standardized_data)} PFEP records!")
                            
                            # Option to lock data
                            if st.button("🔒 Lock PFEP Data for User Access", key="lock_pfep"):
                                st.session_state.pfep_data_locked = True
                                st.success("🔒 PFEP data locked! Users can now upload inventory data.")
                                st.rerun()
                        else:
                            st.error("❌ Failed to process PFEP data. Please check file format.")
                            
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    def handle_pfep_sample_data(self):
        """Handle sample PFEP data loading"""
        st.info("🎮 This will load sample PFEP data for demonstration purposes")
        
        if st.button("📊 Load Sample PFEP Data", type="primary"):
            with st.spinner("Loading sample data..."):
                sample_data = self.load_sample_pfep_data()
                st.session_state.pfep_data = sample_data
                st.success(f"✅ Loaded sample PFEP data with {len(sample_data)} records!")
                
                # Option to lock data
                if st.button("🔒 Lock PFEP Data for User Access", key="lock_sample_pfep"):
                    st.session_state.pfep_data_locked = True
                    st.success("🔒 PFEP data locked! Users can now upload inventory data.")
                    st.rerun()
    
    def display_pfep_data_preview(self):
        """Display PFEP data preview for admin"""
        st.subheader("📋 Current PFEP Data")
        
        pfep_df = pd.DataFrame(st.session_state.pfep_data)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Parts", len(pfep_df))
        with col2:
            st.metric("Unique Vendors", pfep_df['Vendor_Code'].nunique() if 'Vendor_Code' in pfep_df.columns else 0)
        with col3:
            st.metric("Total RM Requirement", f"{pfep_df['RM_IN_QTY'].sum():.2f}")
        with col4:
            locked_status = "🔒 Locked" if getattr(st.session_state, 'pfep_data_locked', False) else "🔓 Unlocked"
            st.metric("Status", locked_status)
        
        # Data preview
        with st.expander("📊 PFEP Data Preview", expanded=True):
            st.dataframe(pfep_df, use_container_width=True)
    
    def user_inventory_management(self):
        """User-only current inventory management interface"""
        st.header("👤 User Dashboard - Current Inventory Upload")
        
        # Check if PFEP data is available and locked
        if not hasattr(st.session_state, 'pfep_data') or not st.session_state.pfep_data:
            st.error("❌ No PFEP master data available. Please contact admin to load PFEP data first.")
            return
        
        if not getattr(st.session_state, 'pfep_data_locked', False):
            st.warning("⚠️ PFEP data is not locked yet. Please wait for admin to lock the data before uploading inventory.")
            return
        
        # Check if inventory data is already locked
        inv_locked = getattr(st.session_state, 'inventory_data_locked', False)
        
        if inv_locked:
            st.success("🔒 Your inventory data is locked and ready for analysis!")
            self.display_analysis_dashboard()
            return
        
        # Display PFEP summary for user reference
        pfep_df = pd.DataFrame(st.session_state.pfep_data)
        st.subheader("📋 Reference: PFEP Master Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Parts in PFEP", len(pfep_df))
        with col2:
            st.metric("Required Parts for Upload", len(pfep_df))
        with col3:
            st.metric("Total RM Requirement", f"{pfep_df['RM_IN_QTY'].sum():.2f}")
        
        # Inventory upload section
        st.subheader("📦 Upload Current Inventory Data")
        
        data_source = st.radio(
            "Choose inventory data source:",
            ["Upload Excel/CSV File", "Use Sample Data"],
            key="inventory_data_source",
            help="Select how you want to load current inventory data"
        )
        
        if data_source == "Upload Excel/CSV File":
            self.handle_inventory_file_upload()
        else:
            self.handle_inventory_sample_data()
    
    def handle_inventory_file_upload(self):
        """Handle inventory file upload with validation"""
        uploaded_file = st.file_uploader(
            "Upload Current Inventory Data",
            type=['xlsx', 'xls', 'csv'],
            help="Upload Excel or CSV file containing current inventory data",
            key="inventory_file_uploader"
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
                
                # Process and validate data
                if st.button("🔄 Process & Validate Inventory Data", type="primary"):
                    with st.spinner("Processing inventory data..."):
                        standardized_data = self.standardize_current_inventory(df)
                        
                        if standardized_data:
                            # Validate against PFEP
                            validation_result = self.validate_inventory_against_pfep(standardized_data)
                            
                            # Display validation results
                            self.display_validation_results(validation_result)
                            
                            if validation_result['is_valid'] or st.checkbox("Proceed despite validation issues"):
                                st.session_state.current_inventory = standardized_data
                                st.session_state.inventory_upload_time = datetime.now()
                                st.success(f"✅ Successfully processed {len(standardized_data)} inventory records!")
                                
                                # Option to lock data and proceed to analysis
                                if st.button("🔒 Lock Data & Start Analysis", key="lock_inventory"):
                                    st.session_state.inventory_data_locked = True
                                    st.success("🔒 Inventory data locked! Starting analysis...")
                                    st.rerun()
                        else:
                            st.error("❌ Failed to process inventory data. Please check file format.")
                            
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    def handle_inventory_sample_data(self):
        """Handle sample inventory data loading"""
        st.info("🎮 This will load sample inventory data that matches the current PFEP data")
        
        if st.button("📊 Load Sample Inventory Data", type="primary"):
            with st.spinner("Loading sample inventory data..."):
                sample_data = self.load_sample_current_inventory()
                
                # Validate against PFEP
                validation_result = self.validate_inventory_against_pfep(sample_data)
                self.display_validation_results(validation_result)
                
                st.session_state.current_inventory = sample_data
                st.session_state.inventory_upload_time = datetime.now()
                st.success(f"✅ Loaded sample inventory data with {len(sample_data)} records!")
                
                # Option to lock data and proceed to analysis
                if st.button("🔒 Lock Data & Start Analysis", key="lock_sample_inventory"):
                    st.session_state.inventory_data_locked = True
                    st.success("🔒 Inventory data locked! Starting analysis...")
                    st.rerun()
    
    def display_validation_results(self, validation_result):
        """Display validation results in a user-friendly format"""
        st.subheader("🔍 Data Validation Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PFEP Parts", validation_result['pfep_parts_count'])
        with col2:
            st.metric("Inventory Parts", validation_result['inventory_parts_count'])
        with col3:
            st.metric("Matching Parts", validation_result['matching_parts_count'])
        with col4:
            match_pct = (validation_result['matching_parts_count'] / validation_result['pfep_parts_count']) * 100 if validation_result['pfep_parts_count'] > 0 else 0
            st.metric("Match %", f"{match_pct:.1f}%")
        
        # Issues and warnings
        if validation_result['issues']:
            st.error("❌ **Critical Issues Found:**")
            for issue in validation_result['issues']:
                st.error(f"• {issue}")
        
        if validation_result['warnings']:
            st.warning("⚠️ **Warnings:**")
            for warning in validation_result['warnings']:
                st.warning(f"• {warning}")
        
        if validation_result['is_valid'] and not validation_result['warnings']:
            st.success("✅ **Validation Passed:** All data looks good!")
    
    def display_analysis_dashboard(self):
        """Main analysis dashboard for users"""
        st.header("📊 Inventory Analysis Dashboard")
        
        # Analysis controls
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            tolerance = st.selectbox(
                "Tolerance Level (%)",
                [10, 20, 30, 40, 50],
                index=2,
                help="Parts within this percentage of target are considered 'Within Norms'"
            )
        with col2:
            analysis_type = st.selectbox(
                "Analysis Type",
                ["Complete Analysis", "Exception Analysis", "Vendor Analysis"],
                help="Choose the type of analysis to perform"
            )
        with col3:
            if st.button("🔄 Refresh Analysis", key="refresh_analysis"):
                st.rerun()
        
        # Perform analysis
        with st.spinner("Analyzing inventory..."):
            analysis_results = self.analyzer.analyze_inventory(
                st.session_state.pfep_data,
                st.session_state.current_inventory,
                tolerance
            )
        
        if not analysis_results:
            st.error("❌ No analysis results generated. Please check your data.")
            return
        
        # Convert to DataFrame for easier manipulation
        results_df = pd.DataFrame(analysis_results)
        
        # Display based on analysis type
        if analysis_type == "Complete Analysis":
            self.display_complete_analysis(results_df, tolerance)
        elif analysis_type == "Exception Analysis":
            self.display_exception_analysis(results_df, tolerance)
        else:
            self.display_vendor_analysis(results_df, tolerance)
    
    def display_complete_analysis(self, results_df, tolerance):
        """Display complete inventory analysis"""
        st.subheader("📋 Complete Inventory Analysis")
        
        # Summary metrics
        total_parts = len(results_df)
        within_norms = len(results_df[results_df['Status'] == 'Within Norms'])
        excess_inventory = len(results_df[results_df['Status'] == 'Excess Inventory'])
        short_inventory = len(results_df[results_df['Status'] == 'Short Inventory'])
        total_stock_value = results_df['Stock_Value'].sum()
        
        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Parts", total_parts)
        with col2:
            st.metric("Within Norms", within_norms, delta=f"{(within_norms/total_parts)*100:.1f}%")
        with col3:
            st.metric("Excess Inventory", excess_inventory, delta=f"{(excess_inventory/total_parts)*100:.1f}%")
        with col4:
            st.metric("Short Inventory", short_inventory, delta=f"{(short_inventory/total_parts)*100:.1f}%")
        with col5:
            st.metric("Total Stock Value", f"₹{total_stock_value:,.0f}")
        
        # Status distribution chart
        st.subheader("📊 Status Distribution")
        status_counts = results_df['Status'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Inventory Status Distribution",
                color_discrete_map=self.analyzer.status_colors
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.markdown("### Status Summary")
            for status, count in status_counts.items():
                percentage = (count / total_parts) * 100
                color = self.analyzer.status_colors.get(status, '#808080')
                st.markdown(f"""
                <div class="status-card status-{status.lower().replace(' ', '-')}">
                    <strong>{status}</strong><br>
                    {count} parts ({percentage:.1f}%)
                </div>
                """, unsafe_allow_html=True)
        
        # Detailed analysis table
        st.subheader("📋 Detailed Analysis")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=results_df['Status'].unique(),
                default=results_df['Status'].unique()
            )
        with col2:
            vendor_filter = st.multiselect(
                "Filter by Vendor",
                options=results_df['Vendor'].unique(),
                default=results_df['Vendor'].unique()
            )
        with col3:
            variance_threshold = st.slider("Min Variance % (absolute)", 0, 100, 0)
        
        # Apply filters
        filtered_df = results_df[
            (results_df['Status'].isin(status_filter)) &
            (results_df['Vendor'].isin(vendor_filter)) &
            (abs(results_df['Variance_%']) >= variance_threshold)
        ]
        
        # Format the dataframe for display
        display_df = filtered_df.copy()
        display_df['Variance_%'] = display_df['Variance_%'].round(2)
        display_df['Stock_Value'] = display_df['Stock_Value'].apply(lambda x: f"₹{x:,.0f}")
        
        # Color code the status
        def color_status(val):
            if val == 'Within Norms':
                return 'background-color: #e8f5e8'
            elif val == 'Excess Inventory':
                return 'background-color: #e3f2fd'
            else:
                return 'background-color: #ffebee'
        
        styled_df = display_df.style.applymap(color_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True)
        
        # Export options
        st.subheader("📤 Export Options")
        col1, col2 = st.columns(2)
        with col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv,
                file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        with col2:
            # Create summary report
            summary_report = self.generate_summary_report(results_df, tolerance)
            st.download_button(
                label="📊 Download Summary Report",
                data=summary_report,
                file_name=f"inventory_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
    
    def display_exception_analysis(self, results_df, tolerance):
        """Display exception-only analysis (items outside tolerance)"""
        st.subheader("⚠️ Exception Analysis")
        
        # Filter for exceptions only
        exceptions_df = results_df[results_df['Status'] != 'Within Norms'].copy()
        
        if exceptions_df.empty:
            st.success("🎉 Congratulations! All items are within tolerance limits.")
            return
        
        # Exception metrics
        total_exceptions = len(exceptions_df)
        excess_count = len(exceptions_df[exceptions_df['Status'] == 'Excess Inventory'])
        short_count = len(exceptions_df[exceptions_df['Status'] == 'Short Inventory'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Exceptions", total_exceptions)
        with col2:
            st.metric("Excess Items", excess_count, delta=f"{(excess_count/total_exceptions)*100:.1f}%")
        with col3:
            st.metric("Short Items", short_count, delta=f"{(short_count/total_exceptions)*100:.1f}%")
        
        # Priority analysis
        st.subheader("🔥 Priority Actions Required")
        
        # High variance items (>50% variance)
        high_variance = exceptions_df[abs(exceptions_df['Variance_%']) > 50]
        if not high_variance.empty:
            st.error(f"❗ **Critical:** {len(high_variance)} items with >50% variance")
            with st.expander("View Critical Items"):
                st.dataframe(high_variance[['Material', 'Description', 'Status', 'Variance_%', 'Vendor']], 
                           use_container_width=True)
        
        # Medium variance items (25-50% variance)
        medium_variance = exceptions_df[
            (abs(exceptions_df['Variance_%']) > 25) & 
            (abs(exceptions_df['Variance_%']) <= 50)
        ]
        if not medium_variance.empty:
            st.warning(f"⚠️ **High Priority:** {len(medium_variance)} items with 25-50% variance")
            with st.expander("View High Priority Items"):
                st.dataframe(medium_variance[['Material', 'Description', 'Status', 'Variance_%', 'Vendor']], 
                           use_container_width=True)
        
        # Variance distribution chart
        fig_hist = px.histogram(
            exceptions_df,
            x='Variance_%',
            color='Status',
            title="Exception Variance Distribution",
            nbins=20,
            color_discrete_map=self.analyzer.status_colors
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Full exceptions table
        st.subheader("📋 All Exceptions")
        st.dataframe(exceptions_df, use_container_width=True)
    
    def display_vendor_analysis(self, results_df, tolerance):
        """Display vendor-wise analysis"""
        st.subheader("🏢 Vendor-wise Analysis")
        
        # Vendor summary
        vendor_summary = results_df.groupby('Vendor').agg({
            'Material': 'count',
            'Stock_Value': 'sum',
            'Variance_%': 'mean',
            'Status': lambda x: (x == 'Within Norms').sum()
        }).round(2)
        
        vendor_summary.columns = ['Total_Parts', 'Total_Stock_Value', 'Avg_Variance_%', 'Within_Norms_Count']
        vendor_summary['Within_Norms_%'] = (vendor_summary['Within_Norms_Count'] / vendor_summary['Total_Parts'] * 100).round(1)
        vendor_summary = vendor_summary.reset_index()
        
        # Display vendor metrics
        st.subheader("📊 Vendor Performance")
        
        # Vendor performance chart
        fig_vendor = px.bar(
            vendor_summary,
            x='Vendor',
            y='Within_Norms_%',
            title="Vendor Performance (% Items Within Norms)",
            color='Within_Norms_%',
            color_continuous_scale='RdYlGn'
        )
        fig_vendor.update_layout(showlegend=False)
        st.plotly_chart(fig_vendor, use_container_width=True)
        
        # Vendor details table
        st.subheader("📋 Vendor Summary Table")
        vendor_display = vendor_summary.copy()
        vendor_display['Total_Stock_Value'] = vendor_display['Total_Stock_Value'].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(vendor_display, use_container_width=True)
        
        # Individual vendor analysis
        st.subheader("🔍 Individual Vendor Analysis")
        selected_vendor = st.selectbox("Select Vendor for Detailed Analysis", vendor_summary['Vendor'].unique())
        
        if selected_vendor:
            vendor_data = results_df[results_df['Vendor'] == selected_vendor]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Parts", len(vendor_data))
            with col2:
                within_norms_pct = (vendor_data['Status'] == 'Within Norms').sum() / len(vendor_data) * 100
                st.metric("Within Norms %", f"{within_norms_pct:.1f}%")
            with col3:
                avg_variance = vendor_data['Variance_%'].mean()
                st.metric("Avg Variance %", f"{avg_variance:.1f}%")
            
            # Vendor specific status distribution
            vendor_status = vendor_data['Status'].value_counts()
            fig_vendor_pie = px.pie(
                values=vendor_status.values,
                names=vendor_status.index,
                title=f"Status Distribution - {selected_vendor}",
                color_discrete_map=self.analyzer.status_colors
            )
            st.plotly_chart(fig_vendor_pie, use_container_width=True)
            
            # Vendor parts details
            st.dataframe(vendor_data, use_container_width=True)
    
    def generate_summary_report(self, results_df, tolerance):
        """Generate a text summary report"""
        total_parts = len(results_df)
        within_norms = len(results_df[results_df['Status'] == 'Within Norms'])
        excess_inventory = len(results_df[results_df['Status'] == 'Excess Inventory'])
        short_inventory = len(results_df[results_df['Status'] == 'Short Inventory'])
        total_stock_value = results_df['Stock_Value'].sum()
        
        report = f"""
INVENTORY ANALYSIS SUMMARY REPORT
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tolerance Level: ±{tolerance}%

=== OVERVIEW ===
Total Parts Analyzed: {total_parts}
Total Stock Value: ₹{total_stock_value:,.0f}

=== STATUS DISTRIBUTION ===
Within Norms: {within_norms} ({(within_norms/total_parts)*100:.1f}%)
Excess Inventory: {excess_inventory} ({(excess_inventory/total_parts)*100:.1f}%)
Short Inventory: {short_inventory} ({(short_inventory/total_parts)*100:.1f}%)

=== KEY INSIGHTS ===
"""
        
        # Add insights based on data
        if within_norms / total_parts >= 0.8:
            report += "✅ Inventory management is performing well with 80%+ items within norms.\n"
        elif within_norms / total_parts >= 0.6:
            report += "⚠️ Inventory management needs attention with 60-80% items within norms.\n"
        else:
            report += "❌ Inventory management requires immediate action with <60% items within norms.\n"
        
        if excess_inventory > short_inventory:
            report += "📈 Excess inventory is the primary concern - consider reducing procurement.\n"
        elif short_inventory > excess_inventory:
            report += "📉 Stock shortages are the primary concern - consider increasing procurement.\n"
        else:
            report += "⚖️ Excess and shortage issues are balanced.\n"
        
        # Vendor insights
        vendor_performance = results_df.groupby('Vendor').agg({
            'Status': lambda x: (x == 'Within Norms').sum() / len(x) * 100
        }).round(1)
        
        best_vendor = vendor_performance.idxmax().iloc[0]
        worst_vendor = vendor_performance.idxmin().iloc[0]
        
        report += f"\n=== VENDOR PERFORMANCE ===\n"
        report += f"Best Performing Vendor: {best_vendor} ({vendor_performance.loc[best_vendor].iloc[0]:.1f}% within norms)\n"
        report += f"Needs Improvement: {worst_vendor} ({vendor_performance.loc[worst_vendor].iloc[0]:.1f}% within norms)\n"
        
        return report
    
    def run(self):
        """Main application runner"""
        # App header
        st.title("📊 Advanced Inventory Management System")
        st.markdown("**Comprehensive PFEP-based Inventory Analysis Platform**")
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.info("👋 Welcome! Please select your role and login to continue.")
            
            # Add some helpful information
            with st.expander("ℹ️ How to use this system"):
                st.markdown("""
                **For Admins:**
                1. Login with admin credentials or use demo mode
                2. Upload or load PFEP master data
                3. Lock the data for user access
                
                **For Users:**
                1. Enter as user (no password required)
                2. Upload current inventory data
                3. Analyze inventory against PFEP requirements
                
                **Features:**
                - Complete inventory analysis with tolerance settings
                - Exception reporting for items outside norms
                - Vendor-wise performance analysis
                - Export capabilities for reports
                """)
            return
        
        # Role-based interface
        if st.session_state.user_role == "Admin":
            self.admin_data_management()
        else:
            self.user_inventory_management()

# Initialize and run the application
if __name__ == "__main__":
    app = InventoryManagementSystem()
    app.run()
