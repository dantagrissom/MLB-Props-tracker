import streamlit as st
import requests
import pandas as pd

# App Layout Configuration
st.set_page_config(page_title="MLB Edge Board Manager", page_icon="⚾", layout="centered")

st.markdown("""
    <style>
    .big-metric { font-size:40px !important; font-weight: bold; color: #1E88E5; }
    .hit-card { padding: 15px; border-radius: 10px; background-color: #2e7d32; color: white; margin-bottom: 20px; }
    .miss-card { padding: 15px; border-radius: 10px; background-color: #c62828; color: white; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚾ MLB Pure Stats Prop Board")

# --- UNDER-THE-HOOD API ENGINE ---
def search_player_id(player_name):
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}&sportId=1"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            people = response.json().get('people', [])
            if people:
                p = people[0]
                pos = p.get('primaryPosition', {}).get('code', 'O')
                return p['id'], p['fullName'], (True if pos == '1' else False)
    except: pass
    return None, None, False

def get_realtime_logs(player_id, player_type, season=2026):
    group_type = "pitching" if player_type == "Pitcher" else "hitting"
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group={group_type}&season={season}"
    try:
        response = requests.get(url)
        if response.status_code == 200: return response.json()
    except: pass
    return None

def ip_to_outs(ip_str):
    try:
        if '.' in str(ip_str):
            parts = str(ip_str).split('.')
            return int(parts[0]) * 3 + int(parts[1])
        return int(ip_str) * 3
    except: return 0

# --- USER SIDEBAR CONTROLS ---
st.sidebar.header("🎯 Board Select")
player_input = st.sidebar.text_input("Player Name", value="Mookie Betts")

pid, full_name, auto_pitcher = search_player_id(player_input)
default_idx = 1 if auto_pitcher else 0
player_type = st.sidebar.radio("Position Category", ["Hitter", "Pitcher"], index=default_idx)

if player_type == "Hitter":
    prop_type = st.sidebar.selectbox(
        "Prop Line Type",
        ["Hits", "Hits+Runs+RBIs", "Total Bases", "Runs", "RBIs", "Home Runs", "Walks", "Plate Appearances", "Singles", "Doubles", "Stolen Bases (SB)", "Hitter Strikeouts (Ks)"]
    )
    pp_line = st.sidebar.slider("Prop Target Value", min_value=0.5, max_value=6.5, value=1.5, step=0.5)
else:
    prop_type = st.sidebar.selectbox(
        "Prop Line Type",
        ["Pitcher Strikeouts", "Outs Recorded", "Earned Runs", "Hits Allowed", "Walks Allowed", "Pitches Thrown"]
    )
    pp_line = st.sidebar.slider("Prop Target Value", min_value=0.5, max_value=105.5, value=5.5, step=0.5)

# --- EXECUTION & RENDERING ---
if player_input and pid:
    raw_data = get_realtime_logs(pid, player_type)
        
    if raw_data and 'stats' in raw_data and raw_data['stats'][0]['splits']:
        splits = raw_data['stats'][0]['splits']
        parsed_games = []
        
        for game in splits:
            stats = game.get('stat', {})
            h, r, rbi, tb, bb, hr = stats.get('hits', 0), stats.get('runs', 0), stats.get('rbi', 0), stats.get('totalBases', 0), stats.get('baseOnBalls', 0), stats.get('homeRuns', 0)
            
            pa = stats.get('plateAppearances', stats.get('atBats', 0) + bb + stats.get('hitByPitch', 0) + stats.get('sacFlies', 0))
            singles = h - (stats.get('doubles', 0) + stats.get('triples', 0) + hr)
            
            if player_type == "Hitter":
                if prop_type == "Hits": target_val = h
                elif prop_type == "Hits+Runs+RBIs": target_val = h + r + rbi
                elif prop_type == "Total Bases": target_val = tb
                elif prop_type == "Runs": target_val = r
                elif prop_type == "RBIs": target_val = rbi
                elif prop_type == "Home Runs": target_val = hr
                elif prop_type == "Walks": target_val = bb
                elif prop_type == "Plate Appearances": target_val = pa
                elif prop_type == "Singles": target_val = singles
                elif prop_type == "Doubles": target_val = stats.get('doubles', 0)
                elif prop_type == "Stolen Bases (SB)": target_val = stats.get('stolenBases', 0)
                elif prop_type == "Hitter Strikeouts (Ks)": target_val = stats.get('strikeOuts', 0)
            else:
                if prop_type == "Pitcher Strikeouts": target_val = stats.get('strikeOuts', 0)
                elif prop_type == "Outs Recorded": target_val = ip_to_outs(stats.get('inningsPitched', '0.0'))
                elif prop_type == "Earned Runs": target_val = stats.get('earnedRuns', 0)
                elif prop_type == "Hits Allowed": target_val = h
                elif prop_type == "Walks Allowed": target_val = bb
                elif prop_type == "Pitches Thrown": target_val = stats.get('pitchesThrown', 0)

            parsed_games.append({
                'Date': game.get('date', ''),
                'Opponent': game.get('opponent', {}).get('name', 'UNK'),
                'Actual Value': target_val
            })
            
        df = pd.DataFrame(parsed_games)
        total_games = len(df)
        overs = sum(df['Actual Value'] > pp_line)
        hit_rate = (overs / total_games) * 100 if total_games > 0 else 0
        
        # --- APP LAYOUT NAVIGATION ---
        tab1, tab2 = st.tabs(["📊 Probability Engine", "📋 Past Performances Log"])
        
        with tab1:
            st.subheader(f"Baseline Trend Summary: {full_name}")
            
            if hit_rate >= 54.3:
                st.markdown(f'<div class="hit-card">🔥 PROBABLE OVER HISTORICAL TREND<br>Line hits at a <b>{hit_rate:.1f}%</b> clip this season.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="miss-card">🧊 PROBABLE UNDER HISTORICAL TREND<br>Line clears at only a <b>{hit_rate:.1f}%</b> clip this season.</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            col1.metric("Games Logged", total_games)
            col2.metric("Season Average", f"{df['Actual Value'].mean():.2f}")
            
            st.write("### Recent Game Run (Last 5 Outings)")
            df_snap = df.head(5).copy()
            df_snap['Result'] = df_snap['Actual Value'].apply(lambda x: "✅ OVER" if x > pp_line else "❌ UNDER")
            st.table(df_snap)

        with tab2:
            st.subheader("🗂️ Full Season History Logs")
            df_full = df.copy()
            df_full['Line Target'] = pp_line
            df_full['Status'] = df_full['Actual Value'].apply(lambda x: "✅ OVER" if x > pp_line else "❌ UNDER")
            st.dataframe(df_full, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Data currently unpopulated or game logs processing on servers.")
else:
    st.error("Enter a valid query above.")
            
