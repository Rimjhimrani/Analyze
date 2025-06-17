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
        
        # Initialize data processing flags
        if 'pfep_processed' not in st.session_state:
            st.session_state.pfep_processed = False
        
        if 'inventory_processed' not in st.session_state:
            st.session_state.inventory_processed = False
    
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
                    st.session_state.pfep_processed = False
                    # Clear user inventory data when PFEP is unlocked
                    if hasattr(st.session_state, 'current_inventory'):
                        del st.session_state.current_inventory
                    if hasattr(st.session_state, 'inventory_data_locked'):
                        del st.session_state.inventory_data_locked
                    if hasattr(st.session_state, 'inventory_processed'):
                        del st.session_state.inventory_processed
                    st.success("✅ PFEP data unlocked. Users need to re-upload inventory data.")
                    st.rerun()
            
            # Display current PFEP data if available
            if hasattr(st.session_state, 'pfep_data') and st.session_state.pfep_data:
                self.display_pfep_data_preview()
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
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("🔄 Process & Load PFEP Data", type="primary", key="process_pfep_file"):
                        with st.spinner("Processing PFEP data..."):
                            standardized_data = self.standardize_pfep_data(df)
                            
                            if standardized_data:
                                st.session_state.pfep_data = standardized_data
                                st.session_state.pfep_upload_time = datetime.now()
                                st.session_state.pfep_processed = True
                                st.success(f"✅ Successfully processed {len(standardized_data)} PFEP records!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to process PFEP data. Please check file format.")
                                
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        # Show lock button if data is processed but not locked
        if (hasattr(st.session_state, 'pfep_data') and 
            st.session_state.pfep_data and 
            st.session_state.get('pfep_processed', False) and 
            not st.session_state.get('pfep_data_locked', False)):
            
            st.markdown("---")
            st.markdown("### 🔒 Lock Data for User Access")
            st.info("Lock the PFEP data to allow users to upload inventory data and perform analysis.")
            
            if st.button("🔒 Lock PFEP Data for User Access", type="primary", key="lock_pfep_file"):
                st.session_state.pfep_data_locked = True
                st.success("🔒 PFEP data locked! Users can now upload inventory data.")
                st.balloons()
                st.rerun()
    
    def handle_pfep_sample_data(self):
        """Handle sample PFEP data loading"""
        st.info("🎮 This will load sample PFEP data for demonstration purposes")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("📊 Load Sample PFEP Data", type="primary", key="load_sample_pfep"):
                with st.spinner("Loading sample data..."):
                    sample_data = self.load_sample_pfep_data()
                    st.session_state.pfep_data = sample_data
                    st.session_state.pfep_processed = True
                    st.success(f"✅ Loaded sample PFEP data with {len(sample_data)} records!")
                    st.rerun()
        
        # Show lock button if data is processed but not locked
        if (hasattr(st.session_state, 'pfep_data') and 
            st.session_state.pfep_data and 
            st.session_state.get('pfep_processed', False) and 
            not st.session_state.get('pfep_data_locked', False)):
            
            st.markdown("---")
            st.markdown("### 🔒 Lock Data for User Access")
            st.info("Lock the PFEP data to allow users to upload inventory data and perform analysis.")
            
            if st.button("🔒 Lock PFEP Data for User Access", type="primary", key="lock_sample_pfep"):
                st.session_state.pfep_data_locked = True
                st.success("🔒 PFEP data locked! Users can now upload inventory data.")
                st.balloons()
                st.rerun()
    
    def display_pfep_data_preview(self):
        """Display PFEP data preview for admin"""
        st.subheader("📋 Current PFEP Data Preview")
        
        pfep_df = pd.DataFrame(st.session_state.pfep_data)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Parts", len(pfep_df))
        with col2:
            st.metric("Total RM Quantity", f"{pfep_df['RM_IN_QTY'].sum():.0f}")
        with col3:
            st.metric("Unique Vendors", pfep_df['Vendor_Name'].nunique())
        with col4:
            st.metric("Unique Cities", pfep_df['City'].nunique())
        
        # Data table
        st.dataframe(pfep_df, use_container_width=True, height=300)
        
        # Vendor distribution
        vendor_counts = pfep_df['Vendor_Name'].value_counts()
        fig_vendor = px.pie(
            values=vendor_counts.values,
            names=vendor_counts.index,
            title="Parts Distribution by Vendor"
        )
        st.plotly_chart(fig_vendor, use_container_width=True)
    
    def user_inventory_management(self):
        """User interface for inventory data upload and analysis"""
        # Check if PFEP data is available and locked
        if not hasattr(st.session_state, 'pfep_data') or not st.session_state.pfep_data:
            st.error("❌ No PFEP master data available. Please contact admin to load PFEP data.")
            return
        
        if not st.session_state.get('pfep_data_locked', False):
            st.warning("⚠️ PFEP data is not yet locked by admin. Please wait for admin to lock the data.")
            return
        
        st.header("📊 Inventory Analysis Dashboard")
        
        # Check if inventory data is locked
        inventory_locked = getattr(st.session_state, 'inventory_data_locked', False)
        
        if inventory_locked:
            st.success("🔒 Inventory data is locked. Analysis results are available below.")
            self.display_analysis_results()
            return
        
        # Inventory data upload section
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
        
        # Show analysis section if inventory data is available
        if hasattr(st.session_state, 'current_inventory') and st.session_state.current_inventory:
            self.display_inventory_analysis_section()
    
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
                col1, col2 = st.columns([2, 1])
                with col1:
                    if st.button("🔄 Process & Validate Inventory Data", type="primary", key="process_inventory_file"):
                        with st.spinner("Processing inventory data..."):
                            standardized_data = self.standardize_current_inventory(df)
                            
                            if standardized_data:
                                # Validate against PFEP
                                validation_result = self.validate_inventory_against_pfep(standardized_data)
                                
                                # Display validation results
                                if validation_result['is_valid']:
                                    st.success("✅ Inventory data validation passed!")
                                else:
                                    st.warning("⚠️ Inventory data has some issues:")
                                    for issue in validation_result['issues']:
                                        st.error(f"❌ {issue}")
                                
                                if validation_result['warnings']:
                                    st.info("ℹ️ Warnings:")
                                    for warning in validation_result['warnings']:
                                        st.warning(f"⚠️ {warning}")
                                
                                # Show validation summary
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("PFEP Parts", validation_result['pfep_parts_count'])
                                with col2:
                                    st.metric("Inventory Parts", validation_result['inventory_parts_count'])
                                with col3:
                                    st.metric("Matching Parts", validation_result['matching_parts_count'])
                                
                                st.session_state.current_inventory = standardized_data
                                st.session_state.inventory_upload_time = datetime.now()
                                st.session_state.inventory_processed = True
                                st.session_state.validation_result = validation_result
                                
                                st.success(f"✅ Successfully processed {len(standardized_data)} inventory records!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to process inventory data. Please check file format.")
                                
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    def handle_inventory_sample_data(self):
        """Handle sample inventory data loading"""
        st.info("🎮 This will load sample inventory data that matches the PFEP data")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("📊 Load Sample Inventory Data", type="primary", key="load_sample_inventory"):
                with st.spinner("Loading sample inventory data..."):
                    sample_data = self.load_sample_current_inventory()
                    
                    # Validate against PFEP
                    validation_result = self.validate_inventory_against_pfep(sample_data)
                    
                    st.session_state.current_inventory = sample_data
                    st.session_state.inventory_upload_time = datetime.now()
                    st.session_state.inventory_processed = True
                    st.session_state.validation_result = validation_result
                    
                    st.success(f"✅ Loaded sample inventory data with {len(sample_data)} records!")
                    st.rerun()
    
    def display_inventory_analysis_section(self):
        """Display inventory analysis section with tolerance settings"""
        st.markdown("---")
        st.subheader("🔍 Inventory Analysis Settings")
        
        # Tolerance setting
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            tolerance = st.slider(
                "Tolerance Percentage (%)",
                min_value=5,
                max_value=50,
                value=st.session_state.user_preferences['default_tolerance'],
                step=5,
                help="Percentage variance allowed from PFEP requirements"
            )
        
        with col2:
            if st.button("🔍 Analyze Inventory", type="primary", key="analyze_inventory"):
                self.perform_inventory_analysis(tolerance)
        
        with col3:
            if (hasattr(st.session_state, 'analysis_results') and 
                st.session_state.analysis_results and
                not st.session_state.get('inventory_data_locked', False)):
                
                if st.button("🔒 Lock Analysis", type="secondary", key="lock_inventory"):
                    st.session_state.inventory_data_locked = True
                    st.success("🔒 Analysis locked! Results are now finalized.")
                    st.rerun()
    
    def perform_inventory_analysis(self, tolerance):
        """Perform comprehensive inventory analysis"""
        with st.spinner("Analyzing inventory against PFEP requirements..."):
            results = self.analyzer.analyze_inventory(
                st.session_state.pfep_data,
                st.session_state.current_inventory,
                tolerance
            )
            
            st.session_state.analysis_results = results
            st.session_state.analysis_tolerance = tolerance
            st.session_state.analysis_time = datetime.now()
            
            st.success(f"✅ Analysis completed! Found {len(results)} parts to analyze.")
            
            # Display immediate results
            self.display_analysis_results()
    
    def display_analysis_results(self):
        """Display comprehensive analysis results"""
        if not hasattr(st.session_state, 'analysis_results') or not st.session_state.analysis_results:
            st.warning("No analysis results available. Please perform analysis first.")
            return
        
        results_df = pd.DataFrame(st.session_state.analysis_results)
        tolerance = st.session_state.get('analysis_tolerance', 30)
        
        st.markdown("---")
        st.subheader(f"📊 Analysis Results (Tolerance: ±{tolerance}%)")
        
        # Summary metrics
        self.display_summary_metrics(results_df)
        
        # Status breakdown
        self.display_status_breakdown(results_df)
        
        # Detailed analysis tabs
        self.display_detailed_analysis_tabs(results_df)
    
    def display_summary_metrics(self, results_df):
        """Display summary metrics"""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_parts = len(results_df)
        within_norms = len(results_df[results_df['Status'] == 'Within Norms'])
        excess_inventory = len(results_df[results_df['Status'] == 'Excess Inventory'])
        short_inventory = len(results_df[results_df['Status'] == 'Short Inventory'])
        total_value = results_df['Stock_Value'].sum()
        
        with col1:
            st.metric("Total Parts", total_parts)
        with col2:
            st.metric("Within Norms", within_norms, f"{(within_norms/total_parts*100):.1f}%")
        with col3:
            st.metric("Excess Inventory", excess_inventory, f"{(excess_inventory/total_parts*100):.1f}%")
        with col4:
            st.metric("Short Inventory", short_inventory, f"{(short_inventory/total_parts*100):.1f}%")
        with col5:
            st.metric("Total Stock Value", f"₹{total_value:,.0f}")
    
    def display_status_breakdown(self, results_df):
        """Display status breakdown with charts"""
        # Status distribution pie chart
        status_counts = results_df['Status'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Inventory Status Distribution",
                color=status_counts.index,
                color_discrete_map=self.analyzer.status_colors
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Variance distribution
            fig_hist = px.histogram(
                results_df,
                x='Variance_%',
                nbins=20,
                title="Variance Distribution (%)",
                color='Status',
                color_discrete_map=self.analyzer.status_colors
            )
            fig_hist.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="Target")
            st.plotly_chart(fig_hist, use_container_width=True)
    
    def display_detailed_analysis_tabs(self, results_df):
        """Display detailed analysis in tabs"""
        tab1, tab2, tab3, tab4 = st.tabs(["📋 All Parts", "🔴 Short Inventory", "🔵 Excess Inventory", "📈 Analytics"])
        
        with tab1:
            self.display_all_parts_analysis(results_df)
        
        with tab2:
            self.display_short_inventory_analysis(results_df)
        
        with tab3:
            self.display_excess_inventory_analysis(results_df)
        
        with tab4:
            self.display_advanced_analytics(results_df)
    
    def display_all_parts_analysis(self, results_df):
        """Display all parts analysis"""
        st.markdown("### All Parts Analysis")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=results_df['Status'].unique(),
                default=results_df['Status'].unique(),
                key="all_parts_status_filter"
            )
        
        with col2:
            vendor_filter = st.multiselect(
                "Filter by Vendor",
                options=results_df['Vendor'].unique(),
                default=results_df['Vendor'].unique(),
                key="all_parts_vendor_filter"
            )
        
        with col3:
            min_variance = st.number_input(
                "Min Variance %",
                value=float(results_df['Variance_%'].min()),
                key="all_parts_min_variance"
            )
        
        # Apply filters
        filtered_df = results_df[
            (results_df['Status'].isin(status_filter)) &
            (results_df['Vendor'].isin(vendor_filter)) &
            (results_df['Variance_%'] >= min_variance)
        ]
        
        # Display filtered results
        st.dataframe(
            filtered_df[['Material', 'Description', 'QTY', 'RM IN QTY', 'Variance_%', 'Status', 'Vendor']],
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Analysis Results",
            data=csv,
            file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    def display_short_inventory_analysis(self, results_df):
        """Display short inventory analysis"""
        short_df = results_df[results_df['Status'] == 'Short Inventory'].copy()
        
        if short_df.empty:
            st.success("🎉 No short inventory items found!")
            return
        
        st.markdown(f"### Short Inventory Items ({len(short_df)} parts)")
        
        # Sort by most critical (highest negative variance)
        short_df = short_df.sort_values('Variance_%')
        
        # Top 10 most critical
        st.markdown("#### 🔥 Most Critical Shortages")
        critical_df = short_df.head(10)
        
        for _, row in critical_df.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="status-card status-short">
                    <strong>{row['Material']}</strong> - {row['Description']}<br>
                    <strong>Current:</strong> {row['QTY']:.1f} | <strong>Required:</strong> {row['RM IN QTY']:.1f} | 
                    <strong>Shortage:</strong> {abs(row['Variance_Value']):.1f} ({row['Variance_%']:.1f}%)<br>
                    <strong>Vendor:</strong> {row['Vendor']} | <strong>Value:</strong> ₹{row['Stock_Value']:,.0f}
                </div>
                """, unsafe_allow_html=True)
        
        # Chart showing shortage by vendor
        vendor_shortage = short_df.groupby('Vendor').agg({
            'Variance_Value': 'sum',
            'Material': 'count'
        }).reset_index()
        vendor_shortage.columns = ['Vendor', 'Total_Shortage', 'Parts_Count']
        
        fig_vendor = px.bar(
            vendor_shortage,
            x='Vendor',
            y='Total_Shortage',
            title="Shortage Quantity by Vendor",
            color='Parts_Count',
            text='Parts_Count'
        )
        st.plotly_chart(fig_vendor, use_container_width=True)
        
        # Full table
        st.markdown("#### Complete Short Inventory List")
        st.dataframe(
            short_df[['Material', 'Description', 'QTY', 'RM IN QTY', 'Variance_%', 'Vendor', 'Stock_Value']],
            use_container_width=True
        )
    
    def display_excess_inventory_analysis(self, results_df):
        """Display excess inventory analysis"""
        excess_df = results_df[results_df['Status'] == 'Excess Inventory'].copy()
        
        if excess_df.empty:
            st.info("No excess inventory items found.")
            return
        
        st.markdown(f"### Excess Inventory Items ({len(excess_df)} parts)")
        
        # Sort by highest excess
        excess_df = excess_df.sort_values('Variance_%', ascending=False)
        
        # Calculate potential savings
        excess_value = excess_df['Stock_Value'].sum()
        total_excess_qty = excess_df['Variance_Value'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Excess Parts", len(excess_df))
        with col2:
            st.metric("Excess Quantity", f"{total_excess_qty:.0f}")
        with col3:
            st.metric("Excess Value", f"₹{excess_value:,.0f}")
        
        # Top 10 highest excess
        st.markdown("#### 💰 Highest Excess Items")
        top_excess = excess_df.head(10)
        
        for _, row in top_excess.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="status-card status-excess">
                    <strong>{row['Material']}</strong> - {row['Description']}<br>
                    <strong>Current:</strong> {row['QTY']:.1f} | <strong>Required:</strong> {row['RM IN QTY']:.1f} | 
                    <strong>Excess:</strong> {row['Variance_Value']:.1f} ({row['Variance_%']:.1f}%)<br>
                    <strong>Vendor:</strong> {row['Vendor']} | <strong>Value:</strong> ₹{row['Stock_Value']:,.0f}
                </div>
                """, unsafe_allow_html=True)
        
        # Chart showing excess by vendor
        vendor_excess = excess_df.groupby('Vendor').agg({
            'Variance_Value': 'sum',
            'Stock_Value': 'sum',
            'Material': 'count'
        }).reset_index()
        
        fig_excess = px.scatter(
            vendor_excess,
            x='Variance_Value',
            y='Stock_Value',
            size='Material',
            color='Vendor',
            title="Excess Inventory: Quantity vs Value by Vendor",
            hover_data=['Material']
        )
        st.plotly_chart(fig_excess, use_container_width=True)
        
        # Full table
        st.markdown("#### Complete Excess Inventory List")
        st.dataframe(
            excess_df[['Material', 'Description', 'QTY', 'RM IN QTY', 'Variance_%', 'Vendor', 'Stock_Value']],
            use_container_width=True
        )
    
    def display_advanced_analytics(self, results_df):
        """Display advanced analytics and insights"""
        st.markdown("### Advanced Analytics & Insights")
        
        # Vendor performance analysis
        st.markdown("#### 🏢 Vendor Performance Analysis")
        vendor_stats = results_df.groupby('Vendor').agg({
            'Material': 'count',
            'QTY': 'sum',
            'RM IN QTY': 'sum',
            'Stock_Value': 'sum',
            'Variance_%': ['mean', 'std']
        }).round(2)
        
        vendor_stats.columns = ['Parts_Count', 'Current_QTY', 'Required_QTY', 'Total_Value', 'Avg_Variance_%', 'Variance_StdDev']
        vendor_stats = vendor_stats.reset_index()
        
        # Add performance score
        vendor_stats['Performance_Score'] = 100 - abs(vendor_stats['Avg_Variance_%'])
        
        st.dataframe(vendor_stats, use_container_width=True)
        
        # Location-wise analysis
        st.markdown("#### 🗺️ Geographic Distribution")
        location_stats = results_df.groupby(['State', 'City']).agg({
            'Material': 'count',
            'Stock_Value': 'sum',
            'Variance_%': 'mean'
        }).reset_index()
        
        fig_map = px.scatter(
            location_stats,
            x='State',
            y='Material',
            size='Stock_Value',
            color='Variance_%',
            title="Inventory Distribution by Location",
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig_map, use_container_width=True)
        
        # ABC Analysis simulation
        st.markdown("#### 📊 ABC Analysis (Value-based)")
        results_df_sorted = results_df.sort_values('Stock_Value', ascending=False)
        results_df_sorted['Cum_Value'] = results_df_sorted['Stock_Value'].cumsum()
        results_df_sorted['Cum_Value_%'] = (results_df_sorted['Cum_Value'] / results_df_sorted['Stock_Value'].sum()) * 100
        
        # Classify into ABC categories
        results_df_sorted['ABC_Category'] = 'C'
        results_df_sorted.loc[results_df_sorted['Cum_Value_%'] <= 80, 'ABC_Category'] = 'A'
        results_df_sorted.loc[(results_df_sorted['Cum_Value_%'] > 80) & (results_df_sorted['Cum_Value_%'] <= 95), 'ABC_Category'] = 'B'
        
        abc_summary = results_df_sorted.groupby('ABC_Category').agg({
            'Material': 'count',
            'Stock_Value': 'sum'
        }).reset_index()
        
        fig_abc = px.bar(
            abc_summary,
            x='ABC_Category',
            y='Stock_Value',
            title="ABC Analysis - Value Distribution",
            text='Material',
            color='ABC_Category'
        )
        st.plotly_chart(fig_abc, use_container_width=True)
    
    def run(self):
        """Main application runner"""
        # Page header
        st.title("📊 Inventory Management System")
        st.markdown("**Comprehensive PFEP-based Inventory Analysis Platform**")
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.info("👋 Welcome! Please login to access the inventory management system.")
            st.markdown("""
            ### Features:
            - **Admin**: Upload and manage PFEP master data
            - **User**: Upload inventory data and perform analysis
            - **Analytics**: Comprehensive inventory variance analysis
            - **Reports**: Detailed insights and recommendations
            """)
            return
        
        # Main application logic based on user role
        if st.session_state.user_role == "Admin":
            self.admin_data_management()
        else:
            self.user_inventory_management()

# Run the application
if __name__ == "__main__":
    app = InventoryManagementSystem()
    app.run()
