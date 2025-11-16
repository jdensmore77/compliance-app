import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Placement File Rule Checker")

# State abbreviation to full name
us_state_abbrev = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana',
    'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan',
    'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
    'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia', 'PR': 'Puerto Rico'
}

# Upload files
placement_file = st.file_uploader("Upload PLACEMENTV2 (CSV or XLSX)", type=["csv", "xlsx"])
rules_file = st.file_uploader("Upload THErules.xlsx", type=["xlsx"])

if placement_file and rules_file:
    placement_df = pd.read_excel(placement_file) if placement_file.name.endswith("xlsx") else pd.read_csv(placement_file)
    rules_df = pd.read_excel(rules_file, sheet_name="Licensing")

    placement_df["State_Full"] = placement_df["State"].map(us_state_abbrev)
    rules_df = rules_df[rules_df["State"].notna()]
    all_states = sorted(rules_df["State"].unique())

    # License selector
    licensed_states = st.multiselect("Select states you ARE licensed in", all_states)
    rules_df.set_index("State", inplace=True)

    def match_license(state):
        return rules_df.at[state, "License Required"] if state in rules_df.index else "Unknown"

    def check_violation(state):
        if state not in all_states:
            return "Unknown"
        if state in licensed_states:
            return "✔ Licensed"
        license_required = str(match_license(state)).lower()
        return "❌ Violation" if "yes" in license_required else "✔ No license needed"

    placement_df["License Required"] = placement_df["State_Full"].apply(match_license)
    placement_df["Status"] = placement_df["State_Full"].apply(check_violation)

    # SOL detection
    matching_cols = [col for col in rules_df.columns if "SOL" in col and "Written" in col]
    sol_col = matching_cols[0] if matching_cols else None
    sol_map = rules_df[sol_col].dropna().to_dict() if sol_col else {}

    def is_outside_sol(state, placement_date):
        try:
            if state not in sol_map:
                return False
            years = int(''.join(filter(str.isdigit, str(sol_map[state]))))
            cutoff_date = placement_date + pd.DateOffset(years=years)
            return datetime.now() > cutoff_date
        except:
            return False

    placement_df["Placement Date"] = pd.to_datetime(placement_df["Placement Date"], errors='coerce')
    placement_df["Outside SOL"] = placement_df.apply(lambda x: is_outside_sol(x["State_Full"], x["Placement Date"]), axis=1)

    # Summary
    total_accounts = len(placement_df)
    passed = len(placement_df[placement_df["Status"] != "❌ Violation"])
    failed = len(placement_df[placement_df["Status"] == "❌ Violation"])
    sol_outside = placement_df["Outside SOL"].sum()

    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accounts", total_accounts)
    col2.metric("Pass", passed)
    col3.metric("Fail", failed)
    col4.metric("Outside SOL", sol_outside)

    # Results with filters — only keep Portfolio and Pass/Fail filters
    st.subheader("Results")
    debt_filter = st.multiselect("Portfolio type", options=placement_df["Debt Type"].dropna().unique())
    status_filter = st.selectbox("Pass/Fail", ["All", "✔ Licensed", "✔ No license needed", "❌ Violation"])

    filtered_df = placement_df.copy()
    if debt_filter:
        filtered_df = filtered_df[filtered_df["Debt Type"].isin(debt_filter)]
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]

    st.dataframe(filtered_df, use_container_width=True)

    # Export
    csv = placement_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Checked File", csv, "CheckedPlacement.csv", "text/csv")

