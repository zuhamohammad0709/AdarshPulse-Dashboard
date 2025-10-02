import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import math

# --- CONFIGURATION (Based on PM-AJAY/Adarsh Gram principles) ---
# These are the *MINIMUM* acceptable standards based on population/households
BASE_THRESHOLDS = {
    # 1 school per 1000 population (or min 1)
    "schools_per_1000": 1, 
    # 1 toilet per household (100% saturation)
    "toilets_per_household": 1.0, 
    # Minimum 1 PHC/Sub-centre for any village
    "PHCs_min": 1, 
    # 1 water point per 50 households (for easy access)
    "water_points_per_50_hh": 1, 
    # 24 hours of electricity supply is the goal
    "electricity_hours_min": 24 
}

# ----------------------------
# Load Village Data
# ----------------------------
@st.cache_data
def load_data():
    # Load data (assuming sample_villages.csv is in the same directory)
    df = pd.read_csv("sample_villages.csv")
    
    # Data Cleaning FIX: Fill NaN values with 0 for count-based columns
    df.columns = df.columns.str.strip()
    count_cols = ["schools", "toilets", "PHCs", "water_points"]
    df[count_cols] = df[count_cols].fillna(0).astype(int)
    df["electricity_hours"] = df["electricity_hours"].fillna(0) 

    # Ensure latitude and longitude are float
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    return df

df = load_data()

# ----------------------------
# Utility: Gap & Score Calculation (Using DYNAMIC Thresholds)
# ----------------------------
def calculate_gaps(row, base_thresholds):
    gaps = []
    improvements = []
    score = 0
    
    # 1. Schools (Dynamic: 1 per 1000 population, min 1)
    required_schools = max(1, math.ceil(row["population"] / 1000) * base_thresholds["schools_per_1000"])
    if row["schools"] < required_schools:
        need = required_schools - row["schools"]
        gaps.append("Schools")
        improvements.append(f"{need} more school(s) (Target: {required_schools})")
        score += need # Score by magnitude of gap

    # 2. Toilets (Dynamic: 1 per household - 100% saturation)
    required_toilets = math.ceil(row["households"] * base_thresholds["toilets_per_household"])
    if row["toilets"] < required_toilets:
        need = required_toilets - row["toilets"]
        gaps.append("Toilets")
        improvements.append(f"Complete {need} household toilet(s) (Target: {required_toilets})")
        # Higher score for larger gap
        score += min(5, math.ceil(need / 100)) 

    # 3. PHCs (Fixed Minimum)
    required_PHCs = base_thresholds["PHCs_min"]
    if row["PHCs"] < required_PHCs:
        need = required_PHCs - row["PHCs"]
        gaps.append("PHCs")
        improvements.append(f"{need} more PHC/Sub-centre(s) (Target: {required_PHCs})")
        score += need * 3 # Higher weight for critical health gap

    # 4. Water Points (Dynamic: 1 per 50 households, min 1)
    required_water = max(1, math.ceil(row["households"] / 50) * base_thresholds["water_points_per_50_hh"])
    if row["water_points"] < required_water:
        need = required_water - row["water_points"]
        gaps.append("Water Points")
        improvements.append(f"{need} more water point(s) (Target: {required_water})")
        score += need

    # 5. Electricity (Fixed: 24-hour supply)
    required_electricity = base_thresholds["electricity_hours_min"]
    if row["electricity_hours"] < required_electricity:
        gaps.append("Electricity")
        improvements.append(f"Need {required_electricity} hrs electricity supply")
        # Score based on how far from 24h they are
        score += math.ceil((required_electricity - row["electricity_hours"]) / 4)
        
    return gaps, score, improvements

# ----------------------------
# Sidebar – Simulation Controls (Use as Adjustment Factors)
# ----------------------------
st.sidebar.header("⚙️ Simulation Controls")

st.sidebar.subheader("Adjust Minimum Standards")

# Use the base thresholds as the default
ADJUSTED_THRESHOLDS = {
    "schools_per_1000": st.sidebar.slider("Schools (per 1000 pop)", 1, 3, BASE_THRESHOLDS["schools_per_1000"]),
    
    # FIX: Added step=0.1 to resolve the StreamlitAPIException
    "toilets_per_household": st.sidebar.slider(
        "Toilets (% HH Saturation)", 
        1.0, 
        1.2, 
        BASE_THRESHOLDS["toilets_per_household"], 
        step=0.1 
    ),
    
    "PHCs_min": st.sidebar.slider("PHCs (Minimum)", 1, 3, BASE_THRESHOLDS["PHCs_min"]),
    "water_points_per_50_hh": st.sidebar.slider("Water Points (per 50 HH)", 1, 3, BASE_THRESHOLDS["water_points_per_50_hh"]),
    "electricity_hours_min": st.sidebar.slider("Electricity (Min Hours)", 10, 24, BASE_THRESHOLDS["electricity_hours_min"])
}

# ----------------------------
# Apply Calculations
# ----------------------------
df["gaps_list"], df["priority_score"], df["improvements_list"] = zip(*df.apply(lambda row: calculate_gaps(row, ADJUSTED_THRESHOLDS), axis=1))
df["gaps"] = df["gaps_list"].apply(lambda x: ", ".join(x) if x else "None")
df["improvements"] = df["improvements_list"].apply(lambda x: ", ".join(x))

# Priority Color Coding (Updated based on a magnitude-based score)
def assign_priority_color(score):
    if score >= 10: return "red"
    elif score >= 5: return "orange"
    else: return "green"

df["priority_color"] = df["priority_score"].apply(assign_priority_color)

# ----------------------------
# Dashboard Title
# ----------------------------
st.title("🏡 AdarshPulse: PM-AJAY Gap Analysis")

# ----------------------------
# Summary Metrics
# ----------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Total Villages", len(df))
col2.metric("🔴 High Priority Villages", len(df[df["priority_color"]=="red"]))
col3.metric("🟠 Medium Priority Villages", len(df[df["priority_color"]=="orange"]))

# ----------------------------
# Village Data Table
# ----------------------------
st.subheader("📋 Village Data with Gaps and Priority Scores")
# Display fewer columns for a cleaner look
st.dataframe(df.drop(columns=["gaps_list", "improvements_list", "lat", "lon"]))

# ----------------------------
# Top 5 Priority Villages
# ----------------------------
top_villages = df.sort_values(by="priority_score", ascending=False).head(5)
st.subheader("🎯 Top 5 Priority Villages")
st.dataframe(top_villages[["village_id","village_name","population","gaps","priority_score"]].reset_index(drop=True))

# ----------------------------
# AI Suggestions (Refined)
# ----------------------------
st.subheader("🤖 AI Suggestions: Project Focus Areas")
for _, row in top_villages.iterrows():
    if row['gaps'] != "None":
        st.write(f"✅ **{row['village_name']}** (Score: {row['priority_score']}) requires: **{row['improvements']}**")
    else:
        st.write(f"✅ **{row['village_name']}** has **No major gaps** based on current thresholds.")

# ----------------------------
# Gaps Distribution Chart
# ----------------------------
st.subheader("📊 Gaps Distribution Across Villages")
# Use the list column for accurate counting of individual gaps
gap_series = df["gaps_list"].explode().value_counts()
if not gap_series.empty:
    fig = px.bar(gap_series, x=gap_series.index, y=gap_series.values,
                 labels={"x":"Gap Type","y":"Villages with this Gap"}, 
                 title="Frequency of Infrastructure Gaps")
    st.plotly_chart(fig)
else:
    st.info("No infrastructure gaps detected based on current thresholds.")

# ----------------------------
# Village Map (Simplified)
# ----------------------------
st.subheader("🗺️ Village Map (Priority View)")
# Create a robust map centered on the data
map_center = [df["lat"].mean(), df["lon"].mean()] if not df.empty and df["lat"].notna().any() else [25.0, 80.0]
m = folium.Map(location=map_center, zoom_start=7)

# Add all markers 
for i, row in df.dropna(subset=['lat', 'lon']).iterrows():
    popup_html = f"""
        <b>{row['village_name']}</b> (Score: {row['priority_score']})<br>
        Population: {row['population']}<br>
        Gaps: {row['gaps']}<br>
        Needs: {row['improvements']}
    """
    folium.Marker(
        [row["lat"], row["lon"]],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color=row["priority_color"], icon='home', prefix='fa')
    ).add_to(m)

st_folium(m, width=700, height=500)

# ----------------------------
# Comparison Mode (FIXED)
# ----------------------------
st.subheader("⚖️ Compare 2 Villages")
colA, colB = st.columns(2)

village_names = df["village_name"].tolist()
v1 = colA.selectbox("Select Village 1", village_names, index=0)
v2_default_index = 1 if len(village_names) > 1 else 0
v2 = colB.selectbox("Select Village 2", village_names, index=v2_default_index)


if v1 and v2 and v1 != v2:
    d1 = df[df["village_name"] == v1].iloc[0].drop(["gaps_list", "improvements_list"])
    d2 = df[df["village_name"] == v2].iloc[0].drop(["gaps_list", "improvements_list"])

    # Create a comparison table
    comparison_data = {
        "Metric": d1.index,
        v1: d1.values,
        v2: d2.values
    }
    
    # Filter for key comparison columns
    comparison_df = pd.DataFrame(comparison_data).set_index("Metric")
    key_metrics = ["population", "households", "schools", "toilets", "PHCs", "water_points", "electricity_hours", "gaps", "priority_score"]
    
    # Calculate the difference for numerical columns
    diff_df = comparison_df.loc[key_metrics].copy()
    diff_df['Difference (' + v1 + ' - ' + v2 + ')'] = diff_df.apply(
        lambda row: row[v1] - row[v2] if pd.api.types.is_numeric_dtype(type(row[v1])) and pd.api.types.is_numeric_dtype(type(row[v2])) else 'N/A', 
        axis=1
    )
    
    st.dataframe(diff_df)

elif v1 == v2:
     st.warning("Please select two different villages for comparison.")
else:
     st.info("Select two villages above to see a detailed comparison.")


# ----------------------------
# Progress Simulation
# ----------------------------
st.subheader("📈 Progress Simulation")
sim_village = st.selectbox("Select a village to simulate upgrade", df["village_name"], key="sim_select")
infra = st.selectbox("Infrastructure to add", ["School","Toilet (100 HH)","PHC","Water Point","Electricity Hours"], key="infra_select")
increment = st.slider("Increase by", 1, 5, 1, key="inc_slider")

if st.button("Simulate"):
    sim_row = df[df["village_name"]==sim_village].iloc[0].copy()
    
    # Apply the upgrade
    if infra=="School": sim_row["schools"] += increment
    elif infra=="PHC": sim_row["PHCs"] += increment
    elif infra=="Water Point": sim_row["water_points"] += increment
    elif infra=="Toilet (100 HH)": sim_row["toilets"] += (increment * 100) # Simulate a block of 100 toilets
    elif infra=="Electricity Hours": 
        sim_row["electricity_hours"] = min(24, sim_row["electricity_hours"] + increment)

    # Re-calculate the score with the *Adjusted* thresholds
    _, new_score, _ = calculate_gaps(sim_row, ADJUSTED_THRESHOLDS)
    new_color = assign_priority_color(new_score)
    
    original_score = df[df["village_name"]==sim_village].iloc[0]["priority_score"]
    original_color = df[df["village_name"]==sim_village].iloc[0]["priority_color"]
    
    st.success(f"**{sim_village}** Upgrade: +{increment} {infra}")
    st.markdown(f"**Original Status**: Score **{original_score}** ({original_color.upper()} priority)")
    st.markdown(f"**New Status**: Score **{new_score}** ({new_color.upper()} priority)")

# ----------------------------
# Download Reports
# ----------------------------
st.subheader("📥 Download Reports")

# Excel
excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False, engine="openpyxl")
st.download_button("Download Excel Report", excel_buffer.getvalue(), file_name="village_gap_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# PDF
def create_pdf(dataframe):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("Village Gap Report (AdarshPulse)", styles['Title']))
    elements.append(Spacer(1, 12))
    
    report_df = dataframe.sort_values('priority_score', ascending=False)
    
    for _, row in report_df.iterrows():
        elements.append(Paragraph(f"<b>{row['village_name']}</b> (Score: {row['priority_score']})", styles['h3']))
        elements.append(Paragraph(f"Gaps: {row['gaps']}", styles['Normal']))
        elements.append(Paragraph(f"Suggested Improvement: {row['improvements']}", styles['Normal']))
        elements.append(Spacer(1, 12))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

pdf_buffer = create_pdf(df)
st.download_button("Download PDF Report", pdf_buffer, file_name="village_gap_report.pdf", mime="application/pdf")
