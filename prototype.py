import pandas as pd
import math

# Full path to CSV (Update the path as necessary for your local setup)
CSV_FILE = "sample_villages.csv" 

# --- CONFIGURATION (Based on PM-AJAY/Adarsh Gram principles) ---
BASE_THRESHOLDS = {
    "schools_per_1000": 1, 
    "toilets_per_household": 1.0, 
    "PHCs_min": 1, 
    "water_points_per_50_hh": 1, 
    "electricity_hours_min": 24 
}

# ----------------------------
# Load and Clean Data
# ----------------------------
try:
    df = pd.read_csv(CSV_FILE)
    df.columns = df.columns.str.strip() # Clean headers

    # FIX: Fill NaN values with 0 for count-based columns
    count_cols = ["schools", "toilets", "PHCs", "water_points"]
    df[count_cols] = df[count_cols].fillna(0).astype(int)
    df["electricity_hours"] = df["electricity_hours"].fillna(0)
    
except FileNotFoundError:
    print(f"Error: The file '{CSV_FILE}' was not found. Please ensure it's in the correct directory.")
    exit()

# ----------------------------
# Function to analyze gaps for each village (DYNAMIC)
# ----------------------------
def analyze_gaps(row):
    gaps = []
    score = 0
    
    # 1. Schools (Dynamic: 1 per 1000 population, min 1)
    required_schools = max(1, math.ceil(row['population'] / 1000) * BASE_THRESHOLDS["schools_per_1000"])
    if row['schools'] < required_schools:
        need = required_schools - row['schools']
        gaps.append("Schools")
        score += need # Score by magnitude

    # 2. Toilets (Dynamic: 1 per household)
    required_toilets = math.ceil(row['households'] * BASE_THRESHOLDS["toilets_per_household"])
    if row['toilets'] < required_toilets:
        gaps.append("Toilets")
        score += min(5, math.ceil((required_toilets - row['toilets']) / 100)) # Score by magnitude
        
    # 3. PHC (Fixed Minimum: 1)
    if row['PHCs'] < BASE_THRESHOLDS["PHCs_min"]:
        gaps.append("PHC")
        score += 3 # Higher score for critical health gap

    # 4. Electricity (Fixed: 24 hours)
    if row['electricity_hours'] < BASE_THRESHOLDS["electricity_hours_min"]:
        gaps.append("Electricity")
        score += math.ceil((BASE_THRESHOLDS["electricity_hours_min"] - row['electricity_hours']) / 4)

    # 5. Water points (Dynamic: 1 per 50 households, min 1)
    required_water = max(1, math.ceil(row['households'] / 50) * BASE_THRESHOLDS["water_points_per_50_hh"])
    if row['water_points'] < required_water:
        need = required_water - row['water_points']
        gaps.append("Water")
        score += need
        
    return gaps, score

# Apply gap analysis
df['gaps_list'], df['priority_score'] = zip(*df.apply(analyze_gaps, axis=1))
df['gaps'] = df['gaps_list'].apply(lambda g: ", ".join(g) if g else "None")


# ----------------------------
# Print Output
# ----------------------------
print("Village Data with Gaps and Priority Scores:")
# Select and display relevant columns
display_cols = ['village_id','village_name','population','households','schools','toilets','PHCs','water_points','electricity_hours','gaps','priority_score']
print(df[display_cols].to_markdown(index=False))

# Top priority villages
top = df.sort_values('priority_score', ascending=False).head(5)
print("\nTop 5 Priority Villages:")
print(top[['village_id','village_name','gaps','priority_score']].to_markdown(index=False))
