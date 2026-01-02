import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- Page Configuration ---
st.set_page_config(
    page_title="Dropship Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS / Styling ---
st.markdown("""
<style>
    .kpi-card {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        text-align: left;
        border-left: 5px solid #4B8bf4;
        margin-bottom: 20px;
    }
    .kpi-title {
        color: #666;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .kpi-value {
        color: #333;
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .kpi-sub {
        color: #888;
        font-size: 12px;
    }
    [data-testid="stMetricValue"] {
        font-size: 20px;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---

@st.cache_data
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def normalize_columns(df):
    """Maps varied column names to standard logical names."""
    # Define mapping priorities (lower case)
    mapping = {
        'order_id': ['order id', 'id', 'order_no', 'order number', 'order_name'],
        'order_date': ['created at', 'order date', 'date', 'timestamp', 'created_at'],
        'order_status': ['status', 'order status', 'fulfillment status', 'financial status'],
        'payment_method': ['payment method', 'payment mode', 'type'],
        'product_name': ['product name', 'item name', 'title', 'lineitem name'],
        'sku': ['sku', 'variant sku', 'item sku', 'lineitem sku', 'product code', 'reference', 'model number', 'master sku'],
        'state': ['shipping province', 'shipping state', 'state', 'province', 'shipping_address_province', 'customer state', 'billing state', 'region', 'destination state', 'state/province', 'state / province', 'shipping address state', 'address state'],
        'gmv_amount': ['total', 'order total', 'gmv', 'amount', 'price', 'total_price'],
        'margin_amount': ['margin', 'profit', 'margin amount'],
        'margin_percent': ['margin %', 'margin percent', 'profit %'],
        'confirmation_status': ['confirmation status', 'is confirmed', 'tags'], # Tags often contain confirmation info
        'return_status': ['return status', 'return_state'],
        'sync_status': ['synced', 'is_synced', 'failed_to_sync']
    }

    df.columns = df.columns.str.lower().str.strip()
    renamed_cols = {}
    
    for target, variations in mapping.items():
        found = False
        for var in variations:
            if var in df.columns:
                renamed_cols[var] = target
                found = True
                break
        # Special check for exact partial matches if not found? (Avoiding for safety)
    
    df = df.rename(columns=renamed_cols)
    return df

def process_data(df):
    """Cleans and calculates necessary fields."""
    
    # Ensure required columns exist (create dummies if missing)
    required_defaults = {
        'order_id': 'Unknown',
        'order_date': pd.NaT,
        'order_status': 'Unknown',
        'gmv_amount': 0,
        'payment_method': 'Unknown',
        'product_name': 'Unknown Product',
        'sku': 'Unknown SKU',
        'state': 'Unknown'
    }
    
    for col, default in required_defaults.items():
        if col not in df.columns:
            df[col] = default

    # Date conversion
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    
    # GMV cleanup
    if df['gmv_amount'].dtype == 'object':
        df['gmv_amount'] = df['gmv_amount'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df['gmv_amount'] = pd.to_numeric(df['gmv_amount'], errors='coerce').fillna(0)
    
    # Margin cleanup
    if 'margin_percent' in df.columns:
        if df['margin_percent'].dtype == 'object':
             df['margin_percent'] = df['margin_percent'].astype(str).str.replace('%', '').str.strip()
             df['margin_percent'] = pd.to_numeric(df['margin_percent'], errors='coerce')
    
    # Derived Status
    # Standardize Status Strings
    st_map = df['order_status'].astype(str).str.lower().str.strip()
    
    def get_status_bucket(s):
        if s == 'delivered':
            return 'DELIVERED'
        elif any(x in s for x in ['rto', 'returned to origin']):
            return 'RTO'
        elif 'undelivered' in s:
            return 'UNDELIVERED'
        elif any(x in s for x in ['shipped', 'out for delivery', 'in transit']): 
            return 'IN_TRANSIT'
        else:
            return 'OTHER'

    df['status_bucket'] = st_map.apply(get_status_bucket)
    
    # Special Logic: IN_TRANSIT count includes Undelivered for specific metrics,
    # but we store the primary bucket as derived above. 
    
    return df

def format_currency(val):
    return f"₹{val:,.0f}"

# --- Main App Logic ---

st.title("Dropship Analytics Dashboard")

uploaded_file = st.sidebar.file_uploader("Upload Excel/CSV", type=['xlsx', 'csv'])

if uploaded_file:
    raw_df = load_data(uploaded_file)
    
    if raw_df is not None:
        df = normalize_columns(raw_df)
        
        # --- Column Mapping Fallback ---
        # Check if 'state' was successfully detected or if it's just the default dummy
        state_col_valid = 'state' in df.columns and not (df['state'] == 'Unknown').all()
        
        if not state_col_valid:
            st.sidebar.warning("State column not auto-detected.")
            # Restore original columns for selection to avoid confusion (or use current)
            # offering all columns from df as potential candidates
            possible_cols = df.columns.tolist()
            manual_state_col = st.sidebar.selectbox("Select State Column", ['Select One...'] + possible_cols)
            
            if manual_state_col != 'Select One...':
                df['state'] = df[manual_state_col].astype(str).str.strip()
            else:
                # keep default but warn
                if 'state' not in df.columns:
                    df['state'] = 'Unknown'

        df = process_data(df)
        
        # --- Sidebar Filters ---
        st.sidebar.header("Filters")
        
        # Date Range
        min_date = df['order_date'].min()
        max_date = df['order_date'].max()
        
        if pd.notnull(min_date) and pd.notnull(max_date):
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        else:
            date_range = []

        # Categorical Filters
        status_options = ['All'] + sorted(df['status_bucket'].unique().tolist())
        selected_status = st.sidebar.selectbox("Order Status", status_options)
        
        payment_options = ['All'] + sorted(df['payment_method'].astype(str).unique().tolist())
        selected_payment = st.sidebar.selectbox("Payment Method", payment_options)
        
        product_options = ['All'] + sorted(df['product_name'].astype(str).unique().tolist())
        selected_product = st.sidebar.multiselect("Product Name", product_options, default=None) 
        
        sku_options = ['All'] + sorted(df['sku'].astype(str).unique().tolist())
        selected_sku = st.sidebar.multiselect("SKU", sku_options, default=None)
        
        # --- Filtering Data ---
        filtered_df = df.copy()
        
        if len(date_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['order_date'].dt.date >= date_range[0]) &
                (filtered_df['order_date'].dt.date <= date_range[1])
            ]
            
        if selected_status != 'All':
            filtered_df = filtered_df[filtered_df['status_bucket'] == selected_status]
            
        if selected_payment != 'All':
            filtered_df = filtered_df[filtered_df['payment_method'].astype(str) == selected_payment]
            
        if selected_product:
            filtered_df = filtered_df[filtered_df['product_name'].isin(selected_product)]
            
        if selected_sku:
            filtered_df = filtered_df[filtered_df['sku'].isin(selected_sku)]
            
        # --- KPI Calculations ---
        # B) Synced Orders
        # Remove blank order IDs
        valid_orders = filtered_df[filtered_df['order_id'].astype(str).str.strip() != '']
        if 'sync_status' in filtered_df.columns:
            # If explicit column (logic depends on data, assuming '1' or 'True' or string 'Synced')
            # For now fallback to simple count as per prompt "Otherwise count unique"
            pass # Use generic logic below unless specific values known
            
        synced_orders_count = valid_orders['order_id'].nunique()
        failed_sync = 0 # Placeholder if column exists
        
        # C) GMV
        total_gmv = valid_orders['gmv_amount'].sum()
        
        # Counts for Formulae
        # Buckets: DELIVERED, RTO, UNDELIVERED
        # IN_TRANSIT special logic: Shipped + Out + InTransit + Undelivered
        
        # We need counts based on status_bucket, but strictly following the prompt's matrix formula
        # Prompt: In Transit % = (Shipped + Out for Delivery + Undelivered) / Synced
        # Note: My `status_bucket` logic already grouped synonyms.
        # Let's count explicitly using standard buckets
        
        count_delivered = valid_orders[valid_orders['status_bucket'] == 'DELIVERED']['order_id'].nunique()
        count_rto = valid_orders[valid_orders['status_bucket'] == 'RTO']['order_id'].nunique()
        count_undelivered = valid_orders[valid_orders['status_bucket'] == 'UNDELIVERED']['order_id'].nunique()
        count_intransit_pure = valid_orders[valid_orders['status_bucket'] == 'IN_TRANSIT']['order_id'].nunique()
        
        # Prompt Rule: IN_TRANSIT count includes Undelivered
        count_intransit_total = count_intransit_pure + count_undelivered 

        # Denominator for percentages (Delivery/RTO definitions in prompt)
        # Denom = Delivered + RTO + Undelivered
        denom_delivery_rto = count_delivered + count_rto + count_undelivered
        
        # In Transit % = (InTransitOrders / SyncedOrders) * 100
        # NOTE: Prompt Matrix says "Undelivered" is part of numerator for InTransit%
        intransit_pct = (count_intransit_total / synced_orders_count * 100) if synced_orders_count > 0 else 0
        
        # Delivery %
        delivery_pct = (count_delivered / denom_delivery_rto * 100) if denom_delivery_rto > 0 else 0
        
        # RTO %
        rto_pct = (count_rto / denom_delivery_rto * 100) if denom_delivery_rto > 0 else 0
        
        # Margin Logic
        # D) Margin
        margin_val = 0
        if 'margin_percent' in valid_orders.columns and valid_orders['margin_percent'].notnull().any():
            # Weighted average by GMV
            total_gmv_margin = valid_orders.loc[valid_orders['margin_percent'].notnull(), 'gmv_amount'].sum()
            if total_gmv_margin > 0:
                 weighted_margin = (valid_orders['margin_percent'] * valid_orders['gmv_amount']).sum() / total_gmv_margin
                 margin_val = weighted_margin
            else:
                 margin_val = valid_orders['margin_percent'].mean()
        elif 'margin_amount' in valid_orders.columns:
            total_margin = valid_orders['margin_amount'].sum()
            margin_val = (total_margin / total_gmv * 100) if total_gmv > 0 else 0

        # --- KPI Cards Row ---
        def kpi_card(title, value, sub):
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">{title}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

        k1, k2, k3, k4, k5 = st.columns(5)
        
        with k1:
             kpi_card("Synced Orders", f"{synced_orders_count:,}", f"Failed: {failed_sync}" if failed_sync > 0 else "")
        with k2:
             kpi_card("GMV", format_currency(total_gmv), f"Margin Applied: {margin_val:.2f}%")
        with k3:
             kpi_card("In Transit %", f"{intransit_pct:.2f}%", f"Orders: {count_intransit_total}")
        with k4:
             kpi_card("Delivery %", f"{delivery_pct:.2f}%", f"Delivered: {count_delivered}")
        with k5:
             kpi_card("RTO %", f"{rto_pct:.2f}%", f"RTO: {count_rto}")

        # --- Charts Row ---
        c1, c2 = st.columns([2, 1])
        
        # Daily Data
        # Prepare aggregation dictionary dynamically
        agg_dict = {
            'gmv_amount': 'sum',
            'order_id': 'nunique'
        }
        if 'margin_percent' in valid_orders.columns:
            agg_dict['margin_percent'] = 'mean'

        daily_df = valid_orders.groupby(valid_orders['order_date'].dt.date).agg(agg_dict).reset_index()
        daily_df.rename(columns={'order_date': 'Date'}, inplace=True)
        
        with c1:
            st.subheader("Orders & GMV")
            if not daily_df.empty:
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=daily_df['Date'], y=daily_df['gmv_amount'], name='GMV', yaxis='y2', marker_color='#4B8bf4', opacity=0.7))
                fig1.add_trace(go.Scatter(x=daily_df['Date'], y=daily_df['order_id'], name='Orders', yaxis='y1', line=dict(color='#333', width=2)))
                
                fig1.update_layout(
                    yaxis=dict(title="Orders", side='left', showgrid=False),
                    yaxis2=dict(title="GMV", side='right', overlaying='y', showgrid=True),
                    legend=dict(orientation="h", y=1.1),
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No date data available.")
                
        with c2:
            st.subheader("Margin Applied %")
            if not daily_df.empty and 'margin_percent' in valid_orders.columns:
                 fig2 = px.line(daily_df, x='Date', y='margin_percent', markers=True)
                 fig2.update_traces(line_color='#2c3e50')
                 fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0), yaxis_title="Margin %")
                 st.plotly_chart(fig2, use_container_width=True)
            else:
                 st.info("Margin data not available.")

        # --- Donuts Row ---
        d1, d2, d3 = st.columns(3)
        
        with d1:
            st.subheader("Orders by Payment Mode")
            pay_dist = valid_orders['payment_method'].value_counts().reset_index()
            pay_dist.columns = ['Method', 'Orders']
            fig_d1 = px.pie(pay_dist, values='Orders', names='Method', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set2)
            fig_d1.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_d1, use_container_width=True)
            
        with d2:
            st.subheader("Orders by Confirmation")
            # Logic F)
            if 'confirmation_status' in valid_orders.columns:
                conf_data = valid_orders['confirmation_status'].fillna('Confirmed')
            else:
                conf_data = pd.Series(['Confirmed'] * len(valid_orders))
            
            conf_dist = conf_data.value_counts().reset_index()
            conf_dist.columns = ['Status', 'Orders']
            fig_d2 = px.pie(conf_dist, values='Orders', names='Status', hole=0.5, color_discrete_sequence=['#2ecc71', '#e74c3c'])
            fig_d2.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_d2, use_container_width=True)

        with d3:
            st.subheader("Confirmed Orders Status")
            # Logic: If confirmation status exists, filter confirmed first. Else all.
            if 'confirmation_status' in valid_orders.columns:
                # Basic check for 'confirmed' string
                confirmed_orders = valid_orders[valid_orders['confirmation_status'].astype(str).str.lower().str.contains('confirm', na=False)]
                if confirmed_orders.empty: confirmed_orders = valid_orders # Fallback
            else:
                confirmed_orders = valid_orders
                
            status_dist = confirmed_orders['status_bucket'].value_counts().reset_index()
            status_dist.columns = ['Status', 'Count']
            
            # Custom colors for status
            colors = {'DELIVERED': '#2ecc71', 'RTO': '#e74c3c', 'UNDELIVERED': '#f1c40f', 'IN_TRANSIT': '#3498db'}
            
            fig_d3 = px.pie(status_dist, values='Count', names='Status', hole=0.5, color='Status', color_discrete_map=colors)
            fig_d3.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_d3, use_container_width=True)

        # --- Map & Margin Table Row ---
        m1, m2 = st.columns([1, 1])
        
        with m1:
            st.subheader("Delivery by State")
            
            state_grp = valid_orders.groupby('state').apply(
                lambda x: pd.Series({
                    'Orders': x['order_id'].nunique(),
                    'Delivered': x[x['status_bucket'] == 'DELIVERED']['order_id'].nunique(),
                    'RTO': x[x['status_bucket'] == 'RTO']['order_id'].nunique(),
                    'Undelivered': x[x['status_bucket'] == 'UNDELIVERED']['order_id'].nunique()
                })
            ).reset_index()

            state_grp['Order Share %'] = (state_grp['Orders'] / synced_orders_count * 100).round(2)
            denom_state = state_grp['Delivered'] + state_grp['RTO'] + state_grp['Undelivered']
            state_grp['Delivered %'] = np.where(denom_state > 0, (state_grp['Delivered'] / denom_state * 100), 0)
            state_grp['RTO %'] = np.where(denom_state > 0, (state_grp['RTO'] / denom_state * 100), 0)

            display_state_cols = ['state', 'Order Share %', 'Delivered %', 'RTO %']
            
            st.dataframe(
                state_grp[display_state_cols].sort_values('Order Share %', ascending=False),
                column_config={
                    "state": "State",
                    "Order Share %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Delivered %": st.column_config.NumberColumn(format="%.2f%%"),
                    "RTO %": st.column_config.NumberColumn(format="%.2f%%")
                },
                hide_index=True,
                use_container_width=True
            )

        with m2:
            st.subheader("Delivery by Margin Range")
            if 'margin_percent' in valid_orders.columns:
                # H) Margin Ranges
                bins = [0, 50, 100, 150, 200, 250, 300, 9999]
                labels = ['0-50', '50-100', '100-150', '150-200', '200-250', '250-300', '300+']
                valid_orders['margin_range'] = pd.cut(valid_orders['margin_percent'], bins=bins, labels=labels, right=False)
                
                margin_grp = valid_orders.groupby('margin_range').apply(
                    lambda x: pd.Series({
                        'Orders': x['order_id'].nunique(),
                        'Delivered': x[x['status_bucket'] == 'DELIVERED']['order_id'].nunique(),
                        'RTO': x[x['status_bucket'] == 'RTO']['order_id'].nunique(),
                        'Undelivered': x[x['status_bucket'] == 'UNDELIVERED']['order_id'].nunique()
                    })
                ).reset_index()
                
                margin_grp['Order Share %'] = (margin_grp['Orders'] / synced_orders_count * 100).round(2)
                
                denom = margin_grp['Delivered'] + margin_grp['RTO'] + margin_grp['Undelivered']
                margin_grp['Delivered %'] = np.where(denom > 0, (margin_grp['Delivered'] / denom * 100), 0).round(2)
                
                st.dataframe(margin_grp[['margin_range', 'Order Share %', 'Delivered %']].style.format("{:.2f}%", subset=['Order Share %', 'Delivered %']), hide_index=True)
            else:
                st.warning("Margin data missing, creating distinct ranges not possible.")

        # --- Product Analysis Table ---
        st.subheader("Products Analysis")
        # I) Product Table
        # Group by Product Name
        prod_grp = valid_orders.groupby('product_name').apply(
            lambda x: pd.Series({
                'Orders': x['order_id'].nunique(),
                'GMV': x['gmv_amount'].sum(),
                # Margin Sum if exists
                'Margin': x['margin_amount'].sum() if 'margin_amount' in x.columns else 0, 
                'Delivered': x[x['status_bucket'] == 'DELIVERED']['order_id'].nunique(),
                'RTO': x[x['status_bucket'] == 'RTO']['order_id'].nunique(),
                'Undelivered': x[x['status_bucket'] == 'UNDELIVERED']['order_id'].nunique(),
                # Returned (Use return_status if exists, else 0)
                'Returned': x['order_id'].nunique() if 'return_status' in x.columns and x[x['return_status'].notnull()]['return_status'].any() else 0 # Placeholder logic depending on value
            })
        ).reset_index()
        
        prod_grp['Order Share %'] = (prod_grp['Orders'] / synced_orders_count * 100).round(2)
        
        denom_prod = prod_grp['Delivered'] + prod_grp['RTO'] + prod_grp['Undelivered']
        prod_grp['Delivered %'] = np.where(denom_prod > 0, (prod_grp['Delivered'] / denom_prod * 100), 0)
        prod_grp['RTO %'] = np.where(denom_prod > 0, (prod_grp['RTO'] / denom_prod * 100), 0)
        prod_grp['Returned %'] = 0 # Default as per prompt unless signal
        
        # Reorder columns
        display_cols = ['product_name', 'Orders', 'Order Share %', 'GMV', 'Margin', 'Delivered %', 'RTO %', 'Returned %']
        # Remove Margin if 0 everywhere? No, keep structure.
        
        # Formatting
        st.dataframe(
            prod_grp[display_cols].sort_values('Orders', ascending=False),
            column_config={
                "Order Share %": st.column_config.NumberColumn(format="%.2f%%"),
                "Delivered %": st.column_config.NumberColumn(format="%.2f%%"),
                "RTO %": st.column_config.NumberColumn(format="%.2f%%"),
                "Returned %": st.column_config.NumberColumn(format="%.2f%%"),
                "GMV": st.column_config.NumberColumn(format="₹%.2f"),
                "Margin": st.column_config.NumberColumn(format="₹%.2f"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Export Button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("Export Filtered Report", data=csv, file_name="filtered_dropship_data.csv", mime="text/csv")
        
    else:
        st.info("Please upload a file to begin.")
else:
    st.info("Awaiting file upload...")

# --- Requirements comment for clarity ---
# pip install streamlit pandas plotly openpyxl
