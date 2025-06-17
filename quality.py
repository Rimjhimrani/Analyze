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
        """
        Analyze ONLY inventory parts that have matching Part_No in PFEP
        Focus on the 584 parts that exist in inventory, not missing parts
        """
        results = []
        
        # Create lookup dictionaries with proper error handling
        pfep_dict = {}
        for item in pfep_data:
            if 'Part_No' in item and item['Part_No']:
                pfep_dict[item['Part_No']] = item
        
        inventory_dict = {}
        for item in current_inventory:
            if 'Part_No' in item and item['Part_No']:
                inventory_dict[item['Part_No']] = item
        
        # Find matching parts between inventory and PFEP
        inventory_parts = set(inventory_dict.keys())
        pfep_parts = set(pfep_dict.keys())
        matching_parts = inventory_parts.intersection(pfep_parts)
        
        # Log analysis details
        st.write(f"📊 Total Inventory Parts: {len(inventory_parts)}")
        st.write(f"📊 Total PFEP Parts: {len(pfep_parts)}")
        st.write(f"✅ Matching Parts Found: {len(matching_parts)}")
        st.write(f"🔍 Analyzing {len(matching_parts)} matching parts...")
        
        # ✅ Analyze only the matching parts
        for part_no in matching_parts:
            inventory_item = inventory_dict[part_no]
            pfep_item = pfep_dict[part_no]
            
            # Get values from inventory with proper error handling
            current_qty = self._safe_get_numeric(inventory_item, 'Current_QTY', 0)
            stock_value = self._safe_get_numeric(inventory_item, 'Stock_Value', 0)
            unit_price = self._safe_get_numeric(inventory_item, 'Unit_Price', 0)
            
            # Get required quantity from PFEP
            rm_qty = self._safe_get_numeric(pfep_item, 'RM_IN_QTY', 0)
            
            # Calculate variance
            if rm_qty > 0:
                variance_pct = ((current_qty - rm_qty) / rm_qty) * 100
            else:
                variance_pct = 0 if current_qty == 0 else 100
            
            variance_value = current_qty - rm_qty
            
            # Determine status based on tolerance
            if abs(variance_pct) <= tolerance:
                status = 'Within Norms'
            elif variance_pct > tolerance:
                status = 'Excess Inventory'
            else:
                status = 'Short Inventory'
            
            # Create result record
            result = {
                'Material': part_no,
                'Description': pfep_item.get('Description', inventory_item.get('Description', '')),
                'QTY': current_qty,
                'RM IN QTY': rm_qty,
                'Stock_Value': stock_value,
                'Variance_%': round(variance_pct, 2),
                'Variance_Value': variance_value,
                'Status': status,
                'Vendor': pfep_item.get('Vendor_Name', 'Unknown'),
                'Vendor_Code': pfep_item.get('Vendor_Code', ''),
                'City': pfep_item.get('City', ''),
                'State': pfep_item.get('State', ''),
                'Unit_Price': unit_price,
                'Category': pfep_item.get('Category', ''),
                'ABC_Class': pfep_item.get('ABC_Class', '')
            }
            
            results.append(result)
        
        # Display analysis summary
        if results:
            within_norms = len([r for r in results if r['Status'] == 'Within Norms'])
            excess = len([r for r in results if r['Status'] == 'Excess Inventory'])
            short = len([r for r in results if r['Status'] == 'Short Inventory'])
            
            st.success(f"""
            📈 ANALYSIS SUMMARY:
            Total Analyzed Parts: {len(results)}
            Within Norms: {within_norms} ({within_norms/len(results)*100:.1f}%)
            Excess Inventory: {excess} ({excess/len(results)*100:.1f}%)
            Short Inventory: {short} ({short/len(results)*100:.1f}%)
            """)
        
        return results
    
    def _safe_get_numeric(self, item, key, default=0):
        """Safely get numeric value from dictionary"""
        try:
            value = item.get(key, default)
            if pd.isna(value) or value == '' or value is None:
                return default
            return float(str(value).replace(',', '').replace('$', '').replace('₹', ''))
        except (ValueError, TypeError):
            return default

    def get_analysis_summary(self, analysis_results):
        """Get detailed summary statistics from analysis results"""
        if not analysis_results:
            return {}
        
        total_parts = len(analysis_results)
        within_norms = len([r for r in analysis_results if r['Status'] == 'Within Norms'])
        excess = len([r for r in analysis_results if r['Status'] == 'Excess Inventory'])
        short = len([r for r in analysis_results if r['Status'] == 'Short Inventory'])
        
        # Calculate total values
        total_stock_value = sum(r.get('Stock_Value', 0) for r in analysis_results)
        total_current_qty = sum(r.get('QTY', 0) for r in analysis_results)
        total_required_qty = sum(r.get('RM IN QTY', 0) for r in analysis_results)
        
        # Calculate variance values
        excess_value = sum(r.get('Stock_Value', 0) for r in analysis_results if r['Status'] == 'Excess Inventory')
        short_value = sum(r.get('Stock_Value', 0) for r in analysis_results if r['Status'] == 'Short Inventory')
        
        return {
            'total_parts': total_parts,
            'within_norms': within_norms,
            'excess_inventory': excess,
            'short_inventory': short,
            'within_norms_pct': (within_norms/total_parts*100) if total_parts > 0 else 0,
            'excess_pct': (excess/total_parts*100) if total_parts > 0 else 0,
            'short_pct': (short/total_parts*100) if total_parts > 0 else 0,
            'total_stock_value': total_stock_value,
            'total_current_qty': total_current_qty,
            'total_required_qty': total_required_qty,
            'excess_value': excess_value,
            'short_value': short_value
        }

    def create_status_chart(self, analysis_results):
        """Create a visual chart for inventory status"""
        if not analysis_results:
            return None
        
        status_counts = {}
        for result in analysis_results:
            status = result['Status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Inventory Status Distribution",
            color_discrete_map=self.status_colors
        )
        return fig
    
    def create_variance_chart(self, analysis_results):
        """Create variance analysis chart"""
        if not analysis_results:
            return None
        
        df = pd.DataFrame(analysis_results)
        fig = px.scatter(
            df, 
            x='RM IN QTY', 
            y='QTY',
            color='Status',
            title="Current vs Required Quantity Analysis",
            labels={'RM IN QTY': 'Required Quantity', 'QTY': 'Current Quantity'},
            hover_data=['Material', 'Variance_%'],
            color_discrete_map=self.status_colors
        )
        
        # Add diagonal line for perfect match
        max_val = max(df['RM IN QTY'].max(), df['QTY'].max())
        fig.add_shape(
            type="line",
            x0=0, y0=0, x1=max_val, y1=max_val,
            line=dict(color="gray", width=2, dash="dash"),
        )
        
        return fig

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
            # User info and controls
            st.sidebar.success(f"✅ **{st.session_state.user_role}** logged in")
            
            # Display data status
            self.display_data_status()
            
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
    
    def display_inventory_analysis(self):
        """Display comprehensive inventory analysis"""
        st.subheader("📊 Inventory Analysis Dashboard")
        
        # Check if both datasets are available
        pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
        inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
        
        if not pfep_data or not inventory_data:
            st.warning("⚠️ Please upload both PFEP and Inventory data first.")
            return
        
        # Analysis controls
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            tolerance = st.slider("Tolerance (%)", min_value=5, max_value=50, 
                                value=st.session_state.user_preferences.get('default_tolerance', 30))
        with col2:
            if st.button("🔄 Run Analysis", key="run_analysis"):
                st.session_state.persistent_analysis_results = None
        with col3:
            if st.button("📊 Reset Analysis", key="reset_analysis"):
                st.session_state.persistent_analysis_results = None
                st.rerun()
        
        # Perform analysis if not already done
        if st.session_state.persistent_analysis_results is None:
            with st.spinner("🔄 Analyzing inventory data..."):
                analysis_results = self.analyzer.analyze_inventory(
                    pfep_data, inventory_data, tolerance=tolerance
                )
                st.session_state.persistent_analysis_results = analysis_results
        
        results = st.session_state.persistent_analysis_results
        
        if not results:
            st.error("❌ No matching parts found between PFEP and Inventory data.")
            return
        
        # Display summary metrics
        summary = self.analyzer.get_analysis_summary(results)
        
        st.markdown("### 📈 Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Parts", summary['total_parts'])
        with col2:
            st.metric("Within Norms", f"{summary['within_norms']}", 
                     f"{summary['within_norms_pct']:.1f}%")
        with col3:
            st.metric("Excess Inventory", f"{summary['excess_inventory']}", 
                     f"{summary['excess_pct']:.1f}%")
        with col4:
            st.metric("Short Inventory", f"{summary['short_inventory']}", 
                     f"{summary['short_pct']:.1f}%")
        
        # Visual charts
        st.markdown("### 📊 Visual Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            status_chart = self.analyzer.create_status_chart(results)
            if status_chart:
                st.plotly_chart(status_chart, use_container_width=True)
        
        with col2:
            variance_chart = self.analyzer.create_variance_chart(results)
            if variance_chart:
                st.plotly_chart(variance_chart, use_container_width=True)
        
        # Detailed results table
        st.markdown("### 📋 Detailed Analysis Results")
        
        # Filter options
        with st.expander("🔍 Filter Options"):
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", 
                                           ["All", "Within Norms", "Excess Inventory", "Short Inventory"])
            with col2:
                vendor_list = ["All"] + list(set([r['Vendor'] for r in results]))
                vendor_filter = st.selectbox("Filter by Vendor", vendor_list)
        
        # Apply filters
        filtered_results = results
        if status_filter != "All":
            filtered_results = [r for r in filtered_results if r['Status'] == status_filter]
        if vendor_filter != "All":
            filtered_results = [r for r in filtered_results if r['Vendor'] == vendor_filter]
        
        # Display filtered results
        if filtered_results:
            df_results = pd.DataFrame(filtered_results)
            st.dataframe(df_results, use_container_width=True)
            
            # Download button
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="📥 Download Analysis Results",
                data=csv,
                file_name=f"inventory_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No results match the selected filters.")
    
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
        """Load enhanced sample current inventory data"""
        current_sample = [
            ["AC0303020106", "FLAT ALUMINIUM PROFILE", 5.230, 496, 94.67],
            ["AC0303020105", "RAIN GUTTER PROFILE", 8.360, 1984, 237.32],
            ["AA0106010001", "HYDRAULIC POWER STEERING OIL", 12.500, 2356, 188.48],
            ["AC0203020077", "Bulb beading LV battery flap", 3.500, 248, 70.86],
            ["AC0303020104", "L- PROFILE JAM PILLAR", 15.940, 992, 62.22],
            ["AA0112014000", "Conduit Pipe Filter to Compressor", 25, 1248, 49.92],
            ["AA0115120001", "HVPDU ms", 18, 1888, 104.89],
            ["AA0119020017", "REAR TURN INDICATOR", 35, 1512, 43.20],
            ["AA0119020019", "REVERSING LAMP", 28, 1152, 41.14],
            ["AA0822010800", "SIDE DISPLAY BOARD", 42, 2496, 59.43],
        ]
        
        return [{'Part_No': row[0], 'Description': row[1], 
                'Current_QTY': self.safe_float_convert(row[2]), 
                'Stock_Value': self.safe_int_convert(row[3]),
                'Unit_Price': self.safe_float_convert(row[4])} for row in current_sample]

    def upload_data_section(self):
        """Handle data upload section"""
        st.subheader("📁 Data Upload & Management")
        
        # Only allow data upload for Admin users or when data is not locked
        can_upload_pfep = (st.session_state.user_role == "Admin" and 
                          not st.session_state.get('persistent_pfep_locked', False))
        can_upload_inventory = (st.session_state.user_role == "Admin" and 
                               not st.session_state.get('persistent_inventory_locked', False))
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 PFEP Master Data")
            if can_upload_pfep:
                uploaded_pfep = st.file_uploader(
                    "Upload PFEP CSV", 
                    type=['csv'], 
                    key="pfep_upload",
                    help="Upload your PFEP master data file"
                )
                
                if uploaded_pfep:
                    try:
                        df_pfep = pd.read_csv(uploaded_pfep)
                        st.success(f"✅ PFEP file loaded: {len(df_pfep)} rows")
                        
                        # Convert to list of dictionaries
                        pfep_data = df_pfep.to_dict('records')
                        self.persistence.save_data_to_session_state('persistent_pfep_data', pfep_data)
                        
                        # Reset analysis when new data is loaded
                        st.session_state.persistent_analysis_results = None
                        
                        st.dataframe(df_pfep.head(), use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"❌ Error loading PFEP file: {str(e)}")
                
                # Sample data button
                if st.button("📝 Load Sample PFEP Data", key="load_sample_pfep"):
                    sample_data = self.load_sample_pfep_data()
                    self.persistence.save_data_to_session_state('persistent_pfep_data', sample_data)
                    st.session_state.persistent_analysis_results = None
                    st.success(f"✅ Sample PFEP data loaded: {len(sample_data)} parts")
                    st.rerun()
                
                # Lock PFEP data
                if st.session_state.persistent_pfep_data:
                    if st.button("🔒 Lock PFEP Data", key="lock_pfep"):
                        st.session_state.persistent_pfep_locked = True
                        st.success("🔒 PFEP data locked!")
                        st.rerun()
            else:
                if st.session_state.get('persistent_pfep_locked', False):
                    st.info("🔒 PFEP data is locked and cannot be modified")
                    if st.session_state.user_role == "Admin":
                        if st.button("🔓 Unlock PFEP Data", key="unlock_pfep"):
                            st.session_state.persistent_pfep_locked = False
                            st.success("🔓 PFEP data unlocked!")
                            st.rerun()
                else:
                    st.info("👤 Admin access required for data upload")
        
        with col2:
            st.markdown("#### 📦 Current Inventory Data")
            if can_upload_inventory:
                uploaded_inventory = st.file_uploader(
                    "Upload Inventory CSV", 
                    type=['csv'], 
                    key="inventory_upload",
                    help="Upload your current inventory data file"
                )
                
                if uploaded_inventory:
                    try:
                        df_inventory = pd.read_csv(uploaded_inventory)
                        st.success(f"✅ Inventory file loaded: {len(df_inventory)} rows")
                        
                        # Convert to list of dictionaries
                        inventory_data = df_inventory.to_dict('records')
                        self.persistence.save_data_to_session_state('persistent_inventory_data', inventory_data)
                        
                        # Reset analysis when new data is loaded
                        st.session_state.persistent_analysis_results = None
                        
                        st.dataframe(df_inventory.head(), use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"❌ Error loading inventory file: {str(e)}")
                
                # Sample data button
                if st.button("📝 Load Sample Inventory Data", key="load_sample_inventory"):
                    sample_data = self.load_sample_current_inventory()
                    self.persistence.save_data_to_session_state('persistent_inventory_data', sample_data)
                    st.session_state.persistent_analysis_results = None
                    st.success(f"✅ Sample inventory data loaded: {len(sample_data)} parts")
                    st.rerun()
                
                # Lock inventory data
                if st.session_state.persistent_inventory_data:
                    if st.button("🔒 Lock Inventory Data", key="lock_inventory"):
                        st.session_state.persistent_inventory_locked = True
                        st.success("🔒 Inventory data locked!")
                        st.rerun()
            else:
                if st.session_state.get('persistent_inventory_locked', False):
                    st.info("🔒 Inventory data is locked and cannot be modified")
                    if st.session_state.user_role == "Admin":
                        if st.button("🔓 Unlock Inventory Data", key="unlock_inventory"):
                            st.session_state.persistent_inventory_locked = False
                            st.success("🔓 Inventory data unlocked!")
                            st.rerun()
                else:
                    st.info("👤 Admin access required for data upload")

    def display_data_view(self):
        """Display uploaded data for review"""
        st.subheader("👀 Data Preview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 PFEP Master Data")
            pfep_data = self.persistence.load_data_from_session_state('persistent_pfep_data')
            if pfep_data:
                df_pfep = pd.DataFrame(pfep_data)
                st.dataframe(df_pfep, use_container_width=True)
                st.caption(f"Total PFEP records: {len(df_pfep)}")
            else:
                st.info("No PFEP data loaded")
        
        with col2:
            st.markdown("#### 📦 Current Inventory Data")
            inventory_data = self.persistence.load_data_from_session_state('persistent_inventory_data')
            if inventory_data:
                df_inventory = pd.DataFrame(inventory_data)
                st.dataframe(df_inventory, use_container_width=True)
                st.caption(f"Total inventory records: {len(df_inventory)}")
            else:
                st.info("No inventory data loaded")

    def display_settings(self):
        """Display user settings and preferences"""
        st.subheader("⚙️ Settings & Preferences")
        
        with st.expander("🎛️ Analysis Settings"):
            default_tolerance = st.slider(
                "Default Tolerance (%)", 
                min_value=5, 
                max_value=50, 
                value=st.session_state.user_preferences.get('default_tolerance', 30),
                help="Default tolerance level for inventory analysis"
            )
            
            chart_theme = st.selectbox(
                "Chart Theme", 
                ["plotly", "plotly_white", "plotly_dark", "ggplot2", "seaborn"],
                index=0,
                help="Select visual theme for charts"
            )
            
            if st.button("💾 Save Preferences"):
                st.session_state.user_preferences.update({
                    'default_tolerance': default_tolerance,
                    'chart_theme': chart_theme
                })
                st.success("✅ Preferences saved!")
        
        if st.session_state.user_role == "Admin":
            with st.expander("🔧 Admin Controls"):
                st.markdown("**Data Management**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Clear All Data", key="clear_all_data"):
                        # Clear all persistent data
                        for key in self.persistent_keys:
                            st.session_state[key] = None
                        st.session_state.persistent_pfep_locked = False
                        st.session_state.persistent_inventory_locked = False
                        st.success("✅ All data cleared!")
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Reset Analysis", key="reset_analysis_admin"):
                        st.session_state.persistent_analysis_results = None
                        st.success("✅ Analysis reset!")
                        st.rerun()
                
                st.markdown("**System Information**")
                st.info(f"""
                - Session ID: {id(st.session_state)}
                - User Role: {st.session_state.user_role}
                - PFEP Locked: {st.session_state.get('persistent_pfep_locked', False)}
                - Inventory Locked: {st.session_state.get('persistent_inventory_locked', False)}
                """)

    def run(self):
        """Main application runner"""
        st.title("🏭 Inventory Management System")
        st.markdown("**Advanced Inventory Analysis & Management Platform**")
        
        # Authentication
        self.authenticate_user()
        
        # Only proceed if user is authenticated
        if st.session_state.user_role is None:
            st.info("👆 Please login using the sidebar to access the system.")
            return
        
        # Main navigation
        tab1, tab2, tab3, tab4 = st.tabs(["📁 Data Upload", "👀 Data View", "📊 Analysis", "⚙️ Settings"])
        
        with tab1:
            self.upload_data_section()
        
        with tab2:
            self.display_data_view()
        
        with tab3:
            self.display_inventory_analysis()
        
        with tab4:
            self.display_settings()
        
        # Footer
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
            "Inventory Management System v2.0 | Built with Streamlit | "
            f"Session: {st.session_state.user_role or 'Not Authenticated'}"
            "</div>", 
            unsafe_allow_html=True
        )

# Application entry point
def main():
    """Main function to run the application"""
    try:
        app = InventoryAnalyzer()
        app.run()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        logger.error(f"Application error: {e}", exc_info=True)
        
        # Display error details for debugging (Admin only)
        if st.session_state.get('user_role') == 'Admin':
            with st.expander("🐛 Debug Information"):
                st.code(str(e))
                st.write("Session State Keys:", list(st.session_state.keys()))

if __name__ == "__main__":
    main()
