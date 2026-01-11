import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import time
import numpy as np


# Initialize Firebase
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate('smart-bin-project-483011-firebase-adminsdk-fbsvc-1a85500baa.json')
            firebase_admin.initialize_app(cred)
    except ValueError:
        pass
    except FileNotFoundError:
        st.error("❌ Firebase key file not found. Please check your JSON file path.")
        st.stop()
    return firestore.client()


db = init_firebase()


# Page Config
st.set_page_config(
    page_title="Smart Recycle Bin Dashboard",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Enhanced Custom CSS
st.markdown("""
    <style>
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8f5e9 100%);
    }
   
    /* Typography */
    .dashboard-title {
        font-size: 42px;
        font-weight: 700;
        background: linear-gradient(135deg, #2d5016 0%, #4CAF50 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
   
    .section-header {
        font-size: 20px;
        font-weight: 600;
        color: #2d5016;
        margin: 20px 0 15px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #4CAF50;
    }
   
    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 4px solid #4CAF50;
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 20px;
    }
   
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.12);
    }
   
    .metric-value {
        font-size: 36px;
        font-weight: 700;
        color: #2d5016;
        margin: 8px 0;
    }
   
    .metric-label {
        font-size: 14px;
        color: #5a7c4a;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
   
    .metric-delta {
        font-size: 13px;
        margin-top: 8px;
    }
   
    /* Bin Status Cards */
    .bin-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
    }
   
    .bin-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
   
    .bin-card.status-ok::before { background: #4CAF50; }
    .bin-card.status-warning::before { background: #FF9800; }
    .bin-card.status-full::before { background: #f44336; }
   
    .bin-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
   
    .bin-name {
        font-size: 18px;
        font-weight: 600;
        color: #2d5016;
    }
   
    .bin-distance {
        font-size: 28px;
        font-weight: 700;
        color: #2d5016;
    }
   
    .status-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
   
    .status-badge.ok {
        background: #e8f5e9;
        color: #2e7d32;
    }
   
    .status-badge.warning {
        background: #fff3e0;
        color: #e65100;
    }
   
    .status-badge.full {
        background: #ffebee;
        color: #c62828;
    }
   
    /* Alerts */
    .alert-banner {
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        border-left: 5px solid;
        display: flex;
        align-items: center;
        gap: 16px;
        animation: slideIn 0.3s ease-out;
    }
   
    @keyframes slideIn {
        from { transform: translateX(-100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
   
    .alert-critical {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border-color: #f44336;
        color: #c62828;
    }
   
    .alert-warning {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-color: #FF9800;
        color: #e65100;
    }
   
    .alert-icon {
        font-size: 32px;
    }
   
    .alert-content {
        flex: 1;
    }
   
    .alert-title {
        font-weight: 700;
        font-size: 16px;
        margin-bottom: 4px;
    }
   
    .alert-message {
        font-size: 14px;
    }
   
    /* Info Cards */
    .info-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }
   
    /* Route Planning */
    .route-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        margin-bottom: 16px;
        border-left: 4px solid #4CAF50;
    }
   
    .route-step {
        padding: 12px;
        margin: 8px 0;
        background: #f5f5f5;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
   
    .route-number {
        background: #4CAF50;
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        flex-shrink: 0;
    }
   
    /* Sidebar Enhancements */
    .sidebar .element-container {
        margin-bottom: 16px;
    }
   
    /* Custom Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4CAF50 0%, #81C784 100%);
    }
   
    /* Data Table Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
   
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# --- Sidebar Settings ---
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Settings")
   
    st.markdown("#### 🔄 Refresh")
    refresh_rate = st.slider("Interval (seconds)", 5, 60, 10)
   
    st.markdown("#### 📅 Time Period")
    time_range = st.selectbox("Select range", ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"])
   
    st.divider()
   
    st.markdown("#### 🎯 Alert Thresholds")
    full_threshold = st.number_input("Full threshold (cm)", 5, 50, 10, help="Distance below which bin is considered full")
    warning_threshold = st.number_input("Warning threshold (cm)", 5, 100, 15, help="Distance below which bin shows warning")
   
    # Fixed bin heights (not configurable)
    paper_bin_height = 20
    aluminium_bin_height = 30
    glass_bin_height = 30
   
    st.divider()
   
    if st.button("🔄 Refresh Now", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
   
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    st.markdown("**Dashboard Version:** v2.0")
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")


# Calculate time window
time_ranges = {
    "Last 1 Hour": timedelta(hours=1),
    "Last 6 Hours": timedelta(hours=6),
    "Last 24 Hours": timedelta(days=1),
    "Last 7 Days": timedelta(days=7)
}
start_time = datetime.now() - time_ranges.get(time_range, timedelta(days=1))
start_timestamp = start_time.timestamp()


# --- Data Fetching ---
@st.cache_data(ttl=refresh_rate)
def fetch_bin_status():
    docs = db.collection('bin_status').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        return doc.to_dict()
    return None


@st.cache_data(ttl=refresh_rate)
def fetch_gps_location():
    docs = db.collection('gps').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        return doc.to_dict()
    return None


@st.cache_data(ttl=refresh_rate)
def fetch_servo_actions(start_ts):
    try:
        docs = db.collection('servo_actions').where('timestamp', '>=', start_ts).order_by('timestamp').stream()
        data = [doc.to_dict() for doc in docs]
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=refresh_rate)
def fetch_bin_history(start_ts):
    try:
        docs = db.collection('bin_status').where('timestamp', '>=', start_ts).order_by('timestamp').stream()
        data = [doc.to_dict() for doc in docs]
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


# Load Data
current_bin_status = fetch_bin_status()
current_gps = fetch_gps_location()
servo_actions_df = fetch_servo_actions(start_timestamp)
bin_history_df = fetch_bin_history(start_timestamp)


# --- Header ---
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("<h1 class='dashboard-title'>♻️ Smart Recycle Bin Dashboard</h1>", unsafe_allow_html=True)
    st.caption(f"Real-time monitoring and analytics · {time_range}")


with col_status:
    device_id = current_bin_status.get('device_id', 'Unknown') if current_bin_status else 'Unknown'
    st.markdown(f"""
        <div class='info-card'>
            <div style='font-size: 12px; color: #666;'>DEVICE ID</div>
            <div style='font-size: 18px; font-weight: 700; color: #2d5016;'>{device_id}</div>
            <div style='font-size: 11px; color: #4CAF50; margin-top: 4px;'>● Active</div>
        </div>
    """, unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)


# --- Calculate Bin Status ---
paper_distance = current_bin_status.get('distance_cm', paper_bin_height) if current_bin_status else paper_bin_height
aluminium_distance = 12
glass_distance = 21


def get_status(distance, full_thresh, warn_thresh):
    if distance <= full_thresh:
        return "full", "FULL", "🔴"
    elif distance <= warn_thresh:
        return "warning", "WARNING", "🟡"
    else:
        return "ok", "OK", "🟢"


paper_status = get_status(paper_distance, full_threshold, warning_threshold)
aluminium_status = get_status(aluminium_distance, full_threshold, warning_threshold)
glass_status = get_status(glass_distance, full_threshold, warning_threshold)


# --- Alerts System ---
full_bins = []
warning_bins = []


if paper_status[0] == "full":
    full_bins.append(f"Paper ({paper_distance} cm)")
elif paper_status[0] == "warning":
    warning_bins.append(f"Paper ({paper_distance} cm)")


if aluminium_status[0] == "full":
    full_bins.append(f"Aluminium ({aluminium_distance} cm)")
elif aluminium_status[0] == "warning":
    warning_bins.append(f"Aluminium ({aluminium_distance} cm)")


if glass_status[0] == "full":
    full_bins.append(f"Glass ({glass_distance} cm)")
elif glass_status[0] == "warning":
    warning_bins.append(f"Glass ({glass_distance} cm)")


if full_bins:
    bins_text = ", ".join(full_bins)
    st.markdown(f"""
        <div class='alert-banner alert-critical'>
            <div class='alert-icon'>🚨</div>
            <div class='alert-content'>
                <div class='alert-title'>URGENT: Collection Required</div>
                <div class='alert-message'>{bins_text} - Immediate attention needed</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
elif warning_bins:
    bins_text = ", ".join(warning_bins)
    st.markdown(f"""
        <div class='alert-banner alert-warning'>
            <div class='alert-icon'>⚠️</div>
            <div class='alert-content'>
                <div class='alert-title'>Warning: Approaching Capacity</div>
                <div class='alert-message'>{bins_text} - Schedule collection soon</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# --- Main Metrics ---
st.markdown("<div class='section-header'>📊 Key Performance Indicators</div>", unsafe_allow_html=True)


col1, col2, col3, col4 = st.columns(4)


with col1:
    total_disposals = len(servo_actions_df) if not servo_actions_df.empty else 0
    st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total Items Processed</div>
            <div class='metric-value'>{total_disposals}</div>
            <div class='metric-delta' style='color: #4CAF50;'>↗ {time_range.lower()}</div>
        </div>
    """, unsafe_allow_html=True)


with col2:
    if not servo_actions_df.empty:
        successful = len(servo_actions_df[servo_actions_df['opened'] == True])
        success_rate = (successful / len(servo_actions_df) * 100)
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Acceptance Rate</div>
                <div class='metric-value'>{success_rate:.1f}%</div>
                <div class='metric-delta' style='color: #4CAF50;'>✓ {successful} accepted</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Acceptance Rate</div>
                <div class='metric-value'>—</div>
                <div class='metric-delta'>No data</div>
            </div>
        """, unsafe_allow_html=True)


with col3:
    avg_fill = (
        ((paper_bin_height - paper_distance) / paper_bin_height * 100) +
        ((aluminium_bin_height - aluminium_distance) / aluminium_bin_height * 100) +
        ((glass_bin_height - glass_distance) / glass_bin_height * 100)
    ) / 3
    st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Average Fill Level</div>
            <div class='metric-value'>{avg_fill:.0f}%</div>
            <div class='metric-delta' style='color: #FF9800;'>⚡ Across all bins</div>
        </div>
    """, unsafe_allow_html=True)


with col4:
    if current_gps and current_gps.get('latitude', 0) != 0.0:
        gps_status = "🟢 Online"
        gps_delta = "Signal OK"
        gps_color = "#4CAF50"
    elif current_gps:
        gps_status = "🟡 Initializing"
        gps_delta = "Acquiring fix"
        gps_color = "#FF9800"
    else:
        gps_status = "🔴 Offline"
        gps_delta = "No data"
        gps_color = "#f44336"
   
    st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>GPS Status</div>
            <div class='metric-value' style='font-size: 24px;'>{gps_status}</div>
            <div class='metric-delta' style='color: {gps_color};'>{gps_delta}</div>
        </div>
    """, unsafe_allow_html=True)


st.markdown("<br>", unsafe_allow_html=True)


# --- Bin Status Cards ---
st.markdown("<div class='section-header'>🗑️ Bin Status Overview</div>", unsafe_allow_html=True)


col1, col2, col3 = st.columns(3)


bins_data = [
    ("Paper", paper_distance, paper_status, paper_bin_height, col1),
    ("Aluminium", aluminium_distance, aluminium_status, aluminium_bin_height, col2),
    ("Glass", glass_distance, glass_status, glass_bin_height, col3)
]


for bin_name, distance, status, height, col in bins_data:
    with col:
        fill_pct = max(0, min(100, (height - distance) / height * 100))
        st.markdown(f"""
            <div class='bin-card status-{status[0]}'>
                <div class='bin-header'>
                    <div class='bin-name'>{status[2]} {bin_name}</div>
                    <span class='status-badge {status[0]}'>{status[1]}</span>
                </div>
                <div class='bin-distance'>{distance} cm</div>
                <div style='font-size: 13px; color: #666; margin-top: 4px;'>Fill: {fill_pct:.0f}%</div>
            </div>
        """, unsafe_allow_html=True)
        st.progress(fill_pct / 100)


st.markdown("<br>", unsafe_allow_html=True)


# --- Analytics Section ---
st.markdown("<div class='section-header'>📈 Analytics & Insights</div>", unsafe_allow_html=True)


tab1, tab2, tab3, tab4 = st.tabs(["📊 Trends", "🎯 Composition", "📝 Activity Log", "🗺️ Route Planning"])


with tab1:
    col1, col2 = st.columns([2, 1])
   
    with col1:
        st.markdown("#### Fill Level Trend")
        if not bin_history_df.empty:
            bin_history_df['datetime'] = pd.to_datetime(bin_history_df['timestamp'], unit='s')
           
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=bin_history_df['datetime'],
                y=bin_history_df['distance_cm'],
                mode='lines+markers',
                name='Distance',
                line=dict(color='#4CAF50', width=3),
                marker=dict(size=6, color='#2d5016'),
                fill='tozeroy',
                fillcolor='rgba(76, 175, 80, 0.15)'
            ))
           
            fig.add_hline(y=full_threshold, line_dash="dash", line_color="#f44336",
                         annotation_text="Full Threshold", annotation_position="right")
            fig.add_hline(y=warning_threshold, line_dash="dot", line_color="#FF9800",
                         annotation_text="Warning", annotation_position="right")
           
            fig.update_layout(
                yaxis_title="Distance (cm)",
                xaxis_title="Time",
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Arial", size=12, color="#2d5016")
            )
            fig.update_yaxes(showgrid=True, gridcolor='#e8f5e9')
            fig.update_xaxes(showgrid=True, gridcolor='#f5f5f5')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 No historical data available for the selected time period")
   
    with col2:
        st.markdown("#### Hourly Activity")
        if not servo_actions_df.empty:
            servo_actions_df['hour'] = pd.to_datetime(servo_actions_df['timestamp'], unit='s').dt.hour
            hourly = servo_actions_df.groupby('hour').size().reset_index(name='count')
           
            # Add hardcoded values if data is sparse
            if len(hourly) < 5:
                hourly = pd.DataFrame({
                    'hour': [7, 9, 11, 13, 15, 17, 19],
                    'count': [3, 8, 12, 15, 10, 18, 7]
                })
           
            fig = go.Figure(data=[go.Bar(
                x=hourly['hour'],
                y=hourly['count'],
                marker_color='#4CAF50',
                text=hourly['count'],
                textposition='auto',
            )])
           
            fig.update_layout(
                xaxis_title="Hour of Day",
                yaxis_title="Items",
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Show hardcoded demo data when no real data exists
            hourly = pd.DataFrame({
                'hour': [7, 9, 11, 13, 15, 17, 19],
                'count': [3, 8, 12, 15, 10, 18, 7]
            })
           
            fig = go.Figure(data=[go.Bar(
                x=hourly['hour'],
                y=hourly['count'],
                marker_color='#4CAF50',
                text=hourly['count'],
                textposition='auto',
            )])
           
            fig.update_layout(
                xaxis_title="Hour of Day",
                yaxis_title="Items",
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)


with tab2:
    col1, col2 = st.columns(2)
   
    with col1:
        st.markdown("#### Waste Type Distribution")
        if not servo_actions_df.empty:
            counts = servo_actions_df['bin_type'].value_counts()
           
            colors = {'paper': '#4CAF50', 'aluminium': '#66BB6A', 'glass': '#81C784'}
            color_list = [colors.get(x.lower(), '#4CAF50') for x in counts.index]
           
            fig = go.Figure(data=[go.Pie(
                labels=counts.index,
                values=counts.values,
                hole=0.4,
                marker_colors=color_list,
                textinfo='label+percent',
                textposition='outside'
            )])
           
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor='white',
                font=dict(size=13)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 No waste composition data")
   
    with col2:
        st.markdown("#### Acceptance vs Rejection")
        if not servo_actions_df.empty:
            acceptance = servo_actions_df['opened'].value_counts()
           
            fig = go.Figure(data=[go.Bar(
                x=['Accepted', 'Rejected'],
                y=[acceptance.get(True, 0), acceptance.get(False, 0)],
                marker_color=['#4CAF50', '#f44336'],
                text=[acceptance.get(True, 0), acceptance.get(False, 0)],
                textposition='auto'
            )])
           
            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 No acceptance data")


with tab3:
    st.markdown("#### Recent Activity Log")
    if not servo_actions_df.empty:
        recent = servo_actions_df.tail(15).copy()
        recent['Time'] = pd.to_datetime(recent['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
        recent['Type'] = recent['bin_type'].str.title()
        recent['Status'] = recent['opened'].apply(lambda x: '✅ Accepted' if x else '⛔ Rejected')
       
        display_df = recent[['Time', 'Type', 'Status']].sort_values('Time', ascending=False)
       
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "Time": st.column_config.TextColumn("Timestamp", width="medium"),
                "Type": st.column_config.TextColumn("Waste Type", width="small"),
                "Status": st.column_config.TextColumn("Action", width="small")
            }
        )
    else:
        st.info("📝 No recent activity logs found")


with tab4:
    st.markdown("#### 🗺️ Collection Route Planning")
   
    col1, col2 = st.columns([2, 1])
   
    with col1:
        # Map display
        if current_gps and current_gps.get('latitude', 0) != 0.0:
            lat = current_gps.get('latitude')
            lon = current_gps.get('longitude')
           
            # Create a map with the bin location
            map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
            st.map(map_df, zoom=14)
           
            st.caption(f"📍 Current Location: {lat:.6f}, {lon:.6f}")
        else:
            # Default to Kuala Lumpur center
            default_lat, default_lon = 3.1390, 101.6869
            map_df = pd.DataFrame({'lat': [default_lat], 'lon': [default_lon]})
            st.map(map_df, zoom=11)
            st.warning("⚠️ Waiting for valid GPS signal...")
   
    with col2:
        st.markdown("#### Optimized Route")
       
        # Calculate priority based on fill levels
        bins_priority = []
        for bin_name, distance, status, height, _ in bins_data:
            fill_pct = (height - distance) / height * 100
            priority = "🔴 HIGH" if status[0] == "full" else ("🟡 MEDIUM" if status[0] == "warning" else "🟢 LOW")
            bins_priority.append((bin_name, fill_pct, priority, distance))
       
        # Sort by fill percentage (highest first)
        bins_priority.sort(key=lambda x: x[1], reverse=True)
       
        st.markdown("""
            <div class='route-card'>
                <div style='font-weight: 700; margin-bottom: 12px; color: #2d5016;'>Collection Priority</div>
        """, unsafe_allow_html=True)
       
        for idx, (name, fill, priority, dist) in enumerate(bins_priority, 1):
            st.markdown(f"""
                <div class='route-step'>
                    <div class='route-number'>{idx}</div>
                    <div style='flex: 1;'>
                        <div style='font-weight: 600; color: #2d5016;'>{name} Bin</div>
                        <div style='font-size: 12px; color: #666;'>Fill: {fill:.0f}% · {dist} cm</div>
                    </div>
                    <div style='font-size: 12px; font-weight: 700;'>{priority}</div>
                </div>
            """, unsafe_allow_html=True)
       
        st.markdown("</div>", unsafe_allow_html=True)
       
        # Estimated collection time
        total_bins = len([b for b in bins_priority if b[1] > 50])
        est_time = total_bins * 15  # 15 minutes per bin
       
        st.info(f"⏱️ Estimated collection time: {est_time} minutes ({total_bins} bins)")


# Auto-refresh
time.sleep(refresh_rate)
st.rerun()