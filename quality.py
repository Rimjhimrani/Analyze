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

.info-box {
    background-color: #e7f3ff;
    border: 1px solid #b3d9ff;
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
        
        # ✅ Loop over inventory only - analyze only matching parts
        for part_no, inventory_item in inventory_dict.items():
            pfep_item = pfep_dict.get(part_no)
            if not pfep_item:
                continue  # Skip inventory parts not found in PFEP
            current_qty = inventory_item.get('Current_QTY', 0)
            stock_value = inventory_item.get('Stock_Value', 0)
            rm_qty = pfep_item.get('RM_IN_QTY', 0)
            
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
        """✅ UPDATED: Focus on intersection analysis rather than missing parts"""
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if not pfep_data:
            return {'is_valid': False, 'issues': ['No PFEP data available'], 'warnings': []}
        
        pfep_df = pd.DataFrame(pfep_data)
        inventory_df = pd.DataFrame(inventory_data)
        
        pfep_parts = set(pfep_df['Part_No'])
        inventory_parts = set(inventory_df['Part_No'])
        
        issues = []
        warnings = []
        
        # Find matching parts (intersection)
        matching_parts = pfep_parts & inventory_parts
        
        # Only show critical issues, not missing parts as errors
        if len(matching_parts) == 0:
            issues.append("No matching parts found between PFEP and Inventory data")
        
        # Check for extra parts in inventory (informational only)
        extra_parts = inventory_parts - pfep_parts
        if extra_parts:
            warnings.append(f"📋 Additional inventory parts not in PFEP: {len(extra_parts)} parts")
            if len(extra_parts) <= 5:
                warnings.append(f"Extra parts: {', '.join(list(extra_parts)[:5])}")
        
        # Check for parts in PFEP but not in current inventory (informational only)
        missing_from_inventory = pfep_parts - inventory_parts
        if missing_from_inventory:
            warnings.append(f"📋 PFEP parts not in current inventory: {len(missing_from_inventory)} parts")
        
        # Check for data quality issues in matching parts only
        matching_inventory = inventory_df[inventory_df['Part_No'].isin(matching_parts)]
        zero_qty_parts = matching_inventory[matching_inventory['Current_QTY'] == 0]['Part_No'].tolist()
        if zero_qty_parts:
            warnings.append(f"⚠️ Matching parts with zero quantity: {len(zero_qty_parts)} parts")
        
        # ✅ Consider validation successful if we have matching parts to analyze
        is_valid = len(matching_parts) > 0
        
        return {
            'is_valid': is_valid,
            'issues': issues,
            'warnings': warnings,
            'pfep_parts_count': len(pfep_parts),
            'inventory_parts_count': len(inventory_parts),
            'matching_parts_count': len(matching_parts),
            'missing_parts_count': len(missing_from_inventory),
            'extra_parts_count': len(extra_parts),
            'match_percentage': (len(matching_parts) / len(pfep_parts)) * 100 if len(pfep_parts) > 0 else 0
        }
    
    def display_validation_results(self, validation_results):
        """✅ UPDATED: Display improved validation results focusing on analysis readiness"""
        st.markdown("### 🔍 Data Validation Results")
        
        # Create metrics display
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("PFEP Parts", validation_results['pfep_parts_count'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Inventory Parts", validation_results['inventory_parts_count'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Matching Parts", validation_results['matching_parts_count'])
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            match_pct = validation_results.get('match_percentage', 0)
            st.metric("Analysis Coverage", f"{match_pct:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ✅ Updated status display
        if validation_results['is_valid']:
            st.markdown(f"""
            <div class="success-box">
                <h4>✅ Ready for Analysis</h4>
                <p><strong>{validation_results['matching_parts_count']}</strong> parts can be analyzed. 
                This represents <strong>{validation_results.get('match_percentage', 0):.1f}%</strong> of your PFEP master data.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="status-card status-short">
                <h4>❌ Analysis Not Possible</h4>
                <p>No matching parts found between PFEP and Inventory data. Please check your data files.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display issues (only critical ones)
        if validation_results['issues']:
            st.markdown("**🚨 Critical Issues:**")
            for issue in validation_results['issues']:
                st.error(f"• {issue}")
        
        # Display warnings (informational)
        if validation_results['warnings']:
            with st.expander("ℹ️ Additional Information", expanded=False):
                for warning in validation_results['warnings']:
                    st.info(f"• {warning}")
        
        def load_pfep_data_section(self):
            """Enhanced PFEP data loading with locking mechanism"""
            st.markdown("## 📋 PFEP Master Data")
            # Check if data is locked
            is_locked = st.session_state.get('persistent_pfep_locked', False)
            if is_locked:
                st.markdown("""
                <div class="info-box">
                   <h4>🔒 PFEP Data Locked</h4>
                   <p>PFEP data is currently locked and cannot be modified. Only Admin can unlock.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show current data info
                pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
                if pfep_data:
                    st.success(f"✅ Current PFEP data contains {len(pfep_data)} parts")
                    with st.expander("📊 View PFEP Data Preview"):
                        df = pd.DataFrame(pfep_data)
                        st.dataframe(df.head(10), use_container_width=True)
                # Admin unlock option
                if st.session_state.user_role == "Admin":
                    st.markdown("---")
                    if st.button("🔓 Unlock PFEP Data", key="unlock_pfep"):
                        st.session_state.persistent_pfep_locked = False
                        st.success("🔓 PFEP data unlocked! You can now modify it.")
                        st.rerun()
                return
            # Data loading options
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📁 Upload PFEP File")
                uploaded_pfep = st.file_uploader(
                    "Choose PFEP file",
                    type=['csv', 'xlsx', 'xls'],
                    key="pfep_uploader",
                    help="Upload your PFEP master data file (CSV or Excel format)"
            )
            with col2:
                st.markdown("### 🎯 Sample Data")
                if st.button("📊 Load Sample PFEP Data", key="load_sample_pfep"):
                    sample_data = self.load_sample_pfep_data()
                    self.persistence.save_data_to_session_state('persistent_pfep_data', sample_data)
                    st.success(f"✅ Sample PFEP data loaded! ({len(sample_data)} parts)")
                    st.rerun()
            # Process uploaded file
            if uploaded_pfep is not None:
                try:
                    if uploaded_pfep.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_pfep)
                    else:
                        df = pd.read_excel(uploaded_pfep)
                    standardized_data = self.standardize_pfep_data(df)
                    
                    if standardized_data:
                        self.persistence.save_data_to_session_state('persistent_pfep_data', standardized_data)
                        st.success(f"✅ PFEP data loaded successfully! ({len(standardized_data)} parts)")
                        # Show previe
                        with st.expander("📊 Data Preview", expanded=True):
                            preview_df = pd.DataFrame(standardized_data).head(10)
                            st.dataframe(preview_df, use_container_width=True)
                        st.rerun()
                    else:
                        st.error("❌ Failed to process PFEP data. Please check your file format.")
                except Exception as e:
                    st.error(f"❌ Error loading PFEP file: {str(e)}")
        
        # Show current data status
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if pfep_data:
            st.markdown("---")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.success(f"✅ PFEP data ready: {len(pfep_data)} parts loaded")
                timestamp = self.persistence.get_data_timestamp('persistent_pfep_data')
                if timestamp:
                    st.caption(f"Last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            with col2:
                if st.session_state.user_role == "Admin":
                    if st.button("🔒 Lock PFEP Data", key="lock_pfep"):
                        st.session_state.persistent_pfep_locked = True
                        st.success("🔒 PFEP data locked successfully!")
                        st.rerun()
    
    def load_current_inventory_section(self):
        """Enhanced current inventory loading with validation"""
        st.markdown("## 📦 Current Inventory Data")
        
        # Check if data is locked
        is_locked = st.session_state.get('persistent_inventory_locked', False)
        
        if is_locked:
            st.markdown("""
            <div class="info-box">
                <h4>🔒 Inventory Data Locked</h4>
                <p>Inventory data is currently locked and cannot be modified.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show current data info
            inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
            if inventory_data:
                st.success(f"✅ Current inventory data contains {len(inventory_data)} parts")
                with st.expander("📊 View Inventory Data Preview"):
                    df = pd.DataFrame(inventory_data)
                    st.dataframe(df.head(10), use_container_width=True)
            
            # Admin unlock option
            if st.session_state.user_role == "Admin":
                st.markdown("---")
                if st.button("🔓 Unlock Inventory Data", key="unlock_inventory"):
                    st.session_state.persistent_inventory_locked = False
                    st.success("🔓 Inventory data unlocked! You can now modify it.")
                    st.rerun()
            
            return
        
        # Check if PFEP is loaded first
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        if not pfep_data:
            st.warning("⚠️ Please load PFEP master data first before loading inventory data.")
            return
        
        # Data loading options
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📁 Upload Inventory File")
            uploaded_inventory = st.file_uploader(
                "Choose Current Inventory file",
                type=['csv', 'xlsx', 'xls'],
                key="inventory_uploader",
                help="Upload your current inventory data file (CSV or Excel format)"
            )
        
        with col2:
            st.markdown("### 🎯 Sample Data")
            if st.button("📊 Load Sample Inventory Data", key="load_sample_inventory"):
                sample_data = self.load_sample_current_inventory()
                
                # Validate against PFEP
                validation_results = self.validate_inventory_against_pfep(sample_data)
                
                if validation_results['is_valid']:
                    self.persistence.save_data_to_session_state('persistent_inventory_data', sample_data)
                    st.success(f"✅ Sample inventory data loaded! ({len(sample_data)} parts)")
                    st.rerun()
                else:
                    st.error("❌ Sample inventory data validation failed!")
        
        # Process uploaded file
        if uploaded_inventory is not None:
            try:
                if uploaded_inventory.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_inventory)
                else:
                    df = pd.read_excel(uploaded_inventory)
                
                standardized_data = self.standardize_current_inventory(df)
                
                if standardized_data:
                    # Validate against PFEP
                    validation_results = self.validate_inventory_against_pfep(standardized_data)
                    self.display_validation_results(validation_results)
                    
                    if validation_results['is_valid']:
                        self.persistence.save_data_to_session_state('persistent_inventory_data', standardized_data)
                        st.success(f"✅ Inventory data loaded successfully! ({len(standardized_data)} parts)")
                        
                        # Show preview
                        with st.expander("📊 Data Preview", expanded=True):
                            preview_df = pd.DataFrame(standardized_data).head(10)
                            st.dataframe(preview_df, use_container_width=True)
                        
                        st.rerun()
                    else:
                        st.error("❌ Inventory data validation failed. Please review the issues above.")
                else:
                    st.error("❌ Failed to process inventory data. Please check your file format.")
                    
            except Exception as e:
                st.error(f"❌ Error loading inventory file: {str(e)}")
        
        # Show current data status
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        if inventory_data:
            st.markdown("---")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.success(f"✅ Inventory data ready: {len(inventory_data)} parts loaded")
                timestamp = self.persistence.get_data_timestamp('persistent_inventory_data')
                if timestamp:
                    st.caption(f"Last updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            with col2:
                if st.session_state.user_role == "Admin":
                    if st.button("🔒 Lock Inventory Data", key="lock_inventory"):
                        st.session_state.persistent_inventory_locked = True
                        st.success("🔒 Inventory data locked successfully!")
                        st.rerun()
    
    def perform_analysis_section(self):
        """Enhanced analysis section with comprehensive reporting"""
        st.markdown("## 📊 Inventory Analysis")
        
        # Check if both datasets are available
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        
        if not pfep_data or not inventory_data:
            st.warning("⚠️ Please load both PFEP and Current Inventory data to perform analysis.")
            return
        
        # Analysis controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            tolerance = st.selectbox(
                "📏 Tolerance Level (%)",
                [10, 20, 30, 40, 50],
                index=2,
                key="analysis_tolerance",
                help="Parts within this tolerance percentage will be considered 'Within Norms'"
            )
        
        with col2:
            if st.button("🔍 Run Analysis", key="run_analysis", type="primary"):
                with st.spinner("Analyzing inventory..."):
                    analysis_results = self.analyzer.analyze_inventory(
                        pfep_data, inventory_data, tolerance
                    )
                    self.persistence.save_data_to_session_state('persistent_analysis_results', analysis_results)
                    st.success(f"✅ Analysis completed! {len(analysis_results)} parts analyzed.")
                    st.rerun()
        
        with col3:
            # Auto-refresh toggle
            auto_refresh = st.checkbox("🔄 Auto-refresh", key="auto_refresh")
        
        # Display analysis results
        analysis_results = self.persistence.load_data_from_session_state('persistent_analysis_results')
        
        if analysis_results:
            self.display_analysis_results(analysis_results, tolerance)
        else:
            st.info("💡 Click 'Run Analysis' to start the inventory analysis.")
    
    def display_analysis_results(self, results, tolerance):
        """Display comprehensive analysis results with enhanced visualizations"""
        if not results:
            return
        
        df = pd.DataFrame(results)
        
        # Summary metrics
        st.markdown("### 📈 Analysis Summary")
        
        status_counts = df['Status'].value_counts()
        total_parts = len(df)
        total_value = df['Stock_Value'].sum()
        
        # Create metrics columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Total Parts Analyzed", f"{total_parts:,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Total Stock Value", f"₹{total_value:,.0f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            within_norms = status_counts.get('Within Norms', 0)
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Within Norms", f"{within_norms} ({within_norms/total_parts*100:.1f}%)")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Tolerance Used", f"±{tolerance}%")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Status breakdown cards
        st.markdown("### 🚦 Status Breakdown")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            excess_count = status_counts.get('Excess Inventory', 0)
            excess_value = df[df['Status'] == 'Excess Inventory']['Stock_Value'].sum()
            st.markdown(f"""
            <div class="status-card status-excess">
                <h4>📈 Excess Inventory</h4>
                <p><strong>{excess_count} parts</strong> ({excess_count/total_parts*100:.1f}%)</p>
                <p>Value: ₹{excess_value:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            short_count = status_counts.get('Short Inventory', 0)
            short_value = df[df['Status'] == 'Short Inventory']['Stock_Value'].sum()
            st.markdown(f"""
            <div class="status-card status-short">
                <h4>📉 Short Inventory</h4>
                <p><strong>{short_count} parts</strong> ({short_count/total_parts*100:.1f}%)</p>
                <p>Value: ₹{short_value:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            normal_count = status_counts.get('Within Norms', 0)
            normal_value = df[df['Status'] == 'Within Norms']['Stock_Value'].sum()
            st.markdown(f"""
            <div class="status-card status-normal">
                <h4>✅ Within Norms</h4>
                <p><strong>{normal_count} parts</strong> ({normal_count/total_parts*100:.1f}%)</p>
                <p>Value: ₹{normal_value:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Visualizations
        self.create_analysis_charts(df)
        
        # Detailed data table
        self.display_detailed_results_table(df)
    
    def create_analysis_charts(self, df):
        """Create comprehensive analysis charts"""
        st.markdown("### 📊 Visual Analysis")
        
        # Chart selection tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Status Distribution", "💰 Value Analysis", "📈 Variance Analysis", "🏢 Vendor Analysis"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Status pie chart
                status_counts = df['Status'].value_counts()
                fig_pie = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Parts Distribution by Status",
                    color_discrete_map=self.analyzer.status_colors
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Status bar chart
                fig_bar = px.bar(
                    x=status_counts.index,
                    y=status_counts.values,
                    title="Parts Count by Status",
                    color=status_counts.index,
                    color_discrete_map=self.analyzer.status_colors
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                # Value distribution by status
                value_by_status = df.groupby('Status')['Stock_Value'].sum().reset_index()
                fig_value = px.bar(
                    value_by_status,
                    x='Status',
                    y='Stock_Value',
                    title="Stock Value by Status",
                    color='Status',
                    color_discrete_map=self.analyzer.status_colors
                )
                fig_value.update_layout(showlegend=False)
                st.plotly_chart(fig_value, use_container_width=True)
            
            with col2:
                # Top 10 parts by value
                top_value_parts = df.nlargest(10, 'Stock_Value')
                fig_top = px.bar(
                    top_value_parts,
                    x='Stock_Value',
                    y='Material',
                    orientation='h',
                    title="Top 10 Parts by Stock Value",
                    color='Status',
                    color_discrete_map=self.analyzer.status_colors
                )
                st.plotly_chart(fig_top, use_container_width=True)
        
        with tab3:
            col1, col2 = st.columns(2)
            
            with col1:
                # Variance percentage distribution
                fig_variance = px.histogram(
                    df,
                    x='Variance_%',
                    nbins=30,
                    title="Variance Percentage Distribution",
                    color='Status',
                    color_discrete_map=self.analyzer.status_colors
                )
                st.plotly_chart(fig_variance, use_container_width=True)
            
            with col2:
                # Scatter plot: Current QTY vs RM QTY
                fig_scatter = px.scatter(
                    df,
                    x='RM IN QTY',
                    y='QTY',
                    color='Status',
                    size='Stock_Value',
                    hover_data=['Material', 'Variance_%'],
                    title="Current Quantity vs Required Quantity",
                    color_discrete_map=self.analyzer.status_colors
                )
                # Add diagonal line for perfect match
                max_qty = max(df['QTY'].max(), df['RM IN QTY'].max())
                fig_scatter.add_shape(
                    type='line',
                    x0=0, y0=0, x1=max_qty, y1=max_qty,
                    line=dict(dash='dash', color='gray')
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
        
        with tab4:
            if 'Vendor' in df.columns and df['Vendor'].notna().any():
                col1, col2 = st.columns(2)
                
                with col1:
                    # Vendor performance
                    vendor_stats = df.groupby('Vendor').agg({
                        'Status': lambda x: (x == 'Within Norms').sum() / len(x) * 100,
                        'Material': 'count'
                    }).reset_index()
                    vendor_stats.columns = ['Vendor', 'Within_Norms_Pct', 'Part_Count']
                    vendor_stats = vendor_stats[vendor_stats['Part_Count'] >= 2]  # Only vendors with 2+ parts
                    
                    if not vendor_stats.empty:
                        fig_vendor = px.bar(
                            vendor_stats,
                            x='Vendor',
                            y='Within_Norms_Pct',
                            title="Vendor Performance (% Within Norms)",
                            text='Part_Count'
                        )
                        fig_vendor.update_traces(texttemplate='%{text} parts', textposition='outside')
                        st.plotly_chart(fig_vendor, use_container_width=True)
                
                with col2:
                    # State-wise analysis
                    if 'State' in df.columns and df['State'].notna().any():
                        state_stats = df.groupby('State')['Status'].value_counts().unstack(fill_value=0)
                        fig_state = px.bar(
                            state_stats,
                            title="State-wise Inventory Status",
                            color_discrete_map=self.analyzer.status_colors
                        )
                        st.plotly_chart(fig_state, use_container_width=True)
    
    def display_detailed_results_table(self, df):
        """Display detailed results in an interactive table"""
        st.markdown("### 📋 Detailed Analysis Results")
        
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
            variance_range = st.slider(
                "Variance Range (%)",
                min_value=float(df['Variance_%'].min()),
                max_value=float(df['Variance_%'].max()),
                value=(float(df['Variance_%'].min()), float(df['Variance_%'].max())),
                key="variance_filter"
            )
        
        with col3:
            if 'Vendor' in df.columns:
                vendor_filter = st.multiselect(
                    "Filter by Vendor",
                    options=df['Vendor'].unique(),
                    default=df['Vendor'].unique(),
                    key="vendor_filter"
                )
            else:
                vendor_filter = []
        
        # Apply filters
        filtered_df = df[
            (df['Status'].isin(status_filter)) &
            (df['Variance_%'] >= variance_range[0]) &
            (df['Variance_%'] <= variance_range[1])
        ]
        
        if vendor_filter and 'Vendor' in df.columns:
            filtered_df = filtered_df[filtered_df['Vendor'].isin(vendor_filter)]
        
        # Display filtered results
        st.info(f"Showing {len(filtered_df)} of {len(df)} parts")
        
        # Format the dataframe for display
        display_df = filtered_df.copy()
        display_df['Variance_%'] = display_df['Variance_%'].round(2)
        display_df['Stock_Value'] = display_df['Stock_Value'].apply(lambda x: f"₹{x:,.0f}")
        
        # Reorder columns
        column_order = ['Material', 'Description', 'QTY', 'RM IN QTY', 'Variance_%', 'Stock_Value', 'Status']
        if 'Vendor' in display_df.columns:
            column_order.extend(['Vendor', 'City', 'State'])
        
        display_df = display_df[column_order]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Variance_%": st.column_config.NumberColumn(
                    "Variance %",
                    format="%.2f%%"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    width="medium"
                )
            }
        )
        
        # Export options
        if st.session_state.user_role == "Admin":
            st.markdown("### 📤 Export Results")
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download as CSV",
                    data=csv_data,
                    file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_csv"
                )
            
            with col2:
                # Summary report
                summary_report = self.generate_summary_report(filtered_df)
                st.download_button(
                    label="📊 Download Summary Report",
                    data=summary_report,
                    file_name=f"inventory_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key="download_summary"
                )
    
    def generate_summary_report(self, df):
        """Generate a text summary report"""
        total_parts = len(df)
        total_value = df['Stock_Value'].sum()
        status_counts = df['Status'].value_counts()
        
        report = f"""
INVENTORY ANALYSIS SUMMARY REPORT
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=====================================

OVERVIEW:
- Total Parts Analyzed: {total_parts:,}
- Total Stock Value: ₹{total_value:,.0f}

STATUS BREAKDOWN:
- Within Norms: {status_counts.get('Within Norms', 0)} parts ({status_counts.get('Within Norms', 0)/total_parts*100:.1f}%)
- Excess Inventory: {status_counts.get('Excess Inventory', 0)} parts ({status_counts.get('Excess Inventory', 0)/total_parts*100:.1f}%)
- Short Inventory: {status_counts.get('Short Inventory', 0)} parts ({status_counts.get('Short Inventory', 0)/total_parts*100:.1f}%)

VALUE ANALYSIS:
- Excess Inventory Value: ₹{df[df['Status'] == 'Excess Inventory']['Stock_Value'].sum():,.0f}
- Short Inventory Value: ₹{df[df['Status'] == 'Short Inventory']['Stock_Value'].sum():,.0f}
- Within Norms Value: ₹{df[df['Status'] == 'Within Norms']['Stock_Value'].sum():,.0f}

TOP 5 EXCESS PARTS (by variance %):
"""
        
        excess_parts = df[df['Status'] == 'Excess Inventory'].nlargest(5, 'Variance_%')
        for _, part in excess_parts.iterrows():
            report += f"- {part['Material']}: {part['Variance_%']:.1f}% excess\n"
        
        report += "\nTOP 5 SHORT PARTS (by variance %):\n"
        short_parts = df[df['Status'] == 'Short Inventory'].nsmallest(5, 'Variance_%')
        for _, part in short_parts.iterrows():
            report += f"- {part['Material']}: {abs(part['Variance_%']):.1f}% short\n"
        
        return report
    
    def run(self):
        """Main application runner"""
        # Header
        st.title("📊 Advanced Inventory Management System")
        st.markdown("*Comprehensive inventory analysis with PFEP integration*")
        
        # Authentication
        self.authenticate_user()
        
        if st.session_state.user_role is None:
            st.markdown("""
            <div class="info-box">
                <h3>🔐 Welcome to Inventory Management System</h3>
                <p>Please select your role from the sidebar to continue:</p>
                <ul>
                    <li><strong>Admin:</strong> Full access to all features including data management</li>
                    <li><strong>User:</strong> View-only access to analysis and reports</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Main content based on user role
        if st.session_state.user_role == "Admin":
            # Admin can see all sections
            self.load_pfep_data_section()
            st.markdown("---")
            self.load_current_inventory_section()
            st.markdown("---")
            self.perform_analysis_section()
        
        elif st.session_state.user_role == "User":
            # User can only see analysis if data is locked
            pfep_locked = st.session_state.get('persistent_pfep_locked', False)
            inventory_locked = st.session_state.get('persistent_inventory_locked', False)
            
            if pfep_locked and inventory_locked:
                self.perform_analysis_section()
            else:
                st.markdown("""
                <div class="info-box">
                    <h3>⏳ Waiting for Data Setup</h3>
                    <p>The Admin is currently setting up the data. Analysis will be available once:</p>
                    <ul>
                        <li>PFEP master data is loaded and locked</li>
                        <li>Current inventory data is loaded and locked</li>
                    </ul>
                    <p>Please check back later or contact your Administrator.</p>
                </div>
                """, unsafe_allow_html=True)

# Run the application
if __name__ == "__main__":
    app = InventoryManagementSystem()
    app.run()
