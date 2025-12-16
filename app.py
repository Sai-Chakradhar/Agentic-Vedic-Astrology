import streamlit as st
import datetime
import pandas as pd

import google.generativeai as genai
from astrology import get_chart_data
from llm import get_astrology_response
import database as db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import textwrap
import pymongo

# Page Config
st.set_page_config(
    page_title="Vedic Astrology AI",
    page_icon="🕉️",
    layout="wide"
)

# --- MongoDB Connection ---
@st.cache_resource
def init_connection(uri):
    import certifi
    return pymongo.MongoClient(
        uri,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10,
        retryWrites=False  # Can help with some TLS handshake issues
    )

def main():
    st.title("🕉️ Vedic Astrology AI & Kundli GMT")
    st.markdown("---")

    # --- Sidebar Configuration (API & DB) ---
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # MongoDB URI - Check secrets first
        mongo_uri = None
        if "MONGO_URI" in st.secrets:
            mongo_uri = st.secrets["MONGO_URI"]
        else:
            mongo_uri = st.text_input(
                "MongoDB Connection String (Optional)", 
                type="password", 
                help="Leave empty to use local SQLite database",
                key="mongo_uri_input"
            )
        
        # Gemini API Key - Check secrets first
        api_key = None
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("🔑 Using API Key from secrets")
        else:
            api_key = st.text_input("Gemini API Key", type="password", key="gemini_key_input")

        # Connection Check
        db_conn = None
        if mongo_uri:
            try:
                client = init_connection(mongo_uri)
                client.admin.command('ping')
                db_conn = client.astrology_app
                st.success("✅ MongoDB Connected")
            except Exception as e:
                st.warning(f"⚠️ MongoDB failed, using SQLite: {str(e)[:50]}...")
                db_conn = None
        else:
            st.info("💾 Using local SQLite database")

    # --- Authentication ---
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    
    # Initialize chart_data if not present
    if 'chart_data' not in st.session_state:
        st.session_state['chart_data'] = None

    if st.session_state['username'] is None:
        choice = st.selectbox("Login / Signup", ["Login", "Signup"])
        
        if choice == "Login":
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                user = db.login_user(db_conn, username, password)
                if user:
                    st.session_state['username'] = username
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        else:
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            if st.button("Signup"):
                if db.add_user(db_conn, new_user, new_pass):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists")
        
        st.stop() # Stop here if not logged in

    # --- Logged In View ---
    
    # Sidebar logout
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        st.session_state['username'] = None
        st.session_state['chart_data'] = None
        st.session_state['user_name'] = None
        st.session_state['messages'] = []
        if 'current_conversation_id' in st.session_state:
             del st.session_state['current_conversation_id']
        st.rerun()

    # Sidebar: Saved Profiles
    st.sidebar.subheader("📂 Saved Profiles")
    profiles = db.get_user_profiles(db_conn, st.session_state['username'])
    if profiles:
        selected_profile = st.sidebar.selectbox("Load Profile", ["Select..."] + [f"{p[0]} ({p[3]})" for p in profiles])
        if selected_profile != "Select...":
             # Find profile data
             # Format: name, dob, tob, city
             p_name_label = selected_profile.split(" (")[0]
             for p in profiles:
                 if p[0] == p_name_label:
                     st.session_state['loaded_profile'] = p
                     break
    
    # Main Input Form
    with st.sidebar:
        st.header("Enter Birth Details")
        
        # Pre-fill if loaded
        if 'loaded_profile' in st.session_state:
            lp = st.session_state['loaded_profile']
            def_name = lp[0]
            def_dob = datetime.datetime.strptime(lp[1], "%Y-%m-%d").date()
            def_time = datetime.datetime.strptime(lp[2], "%H:%M").time()
            def_city = lp[3]
            # Clear it so it doesn't stick forever if user changes manual input? 
            # Actually standard input behavior is fine.
        else:
            def_name = "User"
            def_dob = datetime.date(1990, 1, 1)
            def_time = datetime.time(12, 0)
            def_city = "New Delhi, India"

        name = st.text_input("Name", value=def_name)
        current_year = datetime.datetime.now().year
        dob = st.date_input(
            "Date of Birth", 
            value=def_dob,
            min_value=datetime.date(current_year - 100, 1, 1),
            max_value=datetime.date(current_year + 100, 12, 31)
        )
        birth_time = st.time_input("Time of Birth", value=def_time)
        city = st.text_input("City of Birth", value=def_city)

        save_checkbox = st.checkbox("Save Profile after Generation")
        generate_btn = st.button("Generate Birth Chart", type="primary")


        st.markdown("---")
        if st.button("🗑️ Clear Chat History"):
             db.clear_chat_history(db_conn, st.session_state['username'])
             st.session_state["messages"] = []
             st.success("Chat history cleared!")
             st.rerun()

    # Cached wrapper for chart generation
    @st.cache_data(show_spinner=False)
    def cached_get_chart_data(name, dob_str, time_str, city):
        return get_chart_data(name, dob_str, time_str, city)

    if generate_btn:
        if not city:
            st.error("Please enter a city.")
        else:
            with st.spinner("Calculating planetary positions..."):
                dob_str = dob.strftime("%Y-%m-%d")
                time_str = birth_time.strftime("%H:%M")
                
                # Save to DB if requested
                if save_checkbox:
                    db.save_profile(db_conn, st.session_state['username'], name, dob_str, time_str, city)
                    st.sidebar.success(f"Profile '{name}' saved!")
                
                # Use cached function
                data = cached_get_chart_data(name, dob_str, time_str, city)
                
                if "error" in data:
                    st.error(f"Error: {data['error']}")
                else:
                    st.session_state['chart_data'] = data
                    st.session_state['user_name'] = name
                    st.success("Birth Chart Generated Successfully!")

    # Main Content Area
    if st.session_state['chart_data']:
        chart = st.session_state['chart_data']
        
        # Top-level Navigation
        selected_tab = st.radio(
            "Navigation", 
            ["📊 Charts", "⏳ Dasha Timeline", "💬 Ask Astrologer"], 
            horizontal=True,
            label_visibility="collapsed"
        )
        st.divider()

        if selected_tab == "📊 Charts":
            st.subheader(f"✨ Birth Details for {st.session_state['user_name']}")
             # Top Section: Panchanga & Basic Info
            with st.container():
                col1, col2, col3, col4 = st.columns(4)
                
                if "user_details" in chart:
                    ud = chart["user_details"]
                    col1.metric("Nakshatra", ud.get('nakshatra', 'Unknown'), ud.get('rashi', ''))
                    col2.metric("Tithi", ud.get('tithi', 'Unknown'))
                    col3.metric("Yoga", ud.get('yoga', 'Unknown'))
                    col4.metric("Karana", ud.get('karana', 'Unknown'))
            
            st.divider()
            st.header("Divisional Charts")
            
            # Identify available charts
            available_charts = []
            if "D1" in chart: available_charts.append("D1 (Rasi)")
            if "special_points" in chart and "sphuta" in chart["special_points"]:
                sphuta = chart["special_points"]["sphuta"]
                for k in sphuta.keys():
                    if k.startswith("D") and k not in available_charts:
                         available_charts.append(k)
            
            # User selector
            selected_chart_name = st.selectbox("Select Chart", available_charts if available_charts else ["D1"])
            
            chart_planets = []
            
            if selected_chart_name == "D1 (Rasi)" or selected_chart_name == "D1":
                if "D1" in chart and "planets" in chart["D1"]:
                    for p, details in chart["D1"]["planets"].items():
                        chart_planets.append({
                            "Planet": p,
                            "Sign": details.get('sign'),
                            "House": details.get('house'),
                            "Nakshatra": details.get('nakshatra'),
                        })
            else:
                st.warning(f"Detailed planetary positions for {selected_chart_name} might not be fully parsed in this version. Showing Lagna/Points if available.")
                if "special_points" in chart and "sphuta" in chart["special_points"]:
                     sp = chart["special_points"]["sphuta"]
                     # Clean name
                     key = selected_chart_name.split()[0]
                     if key in sp:
                         st.write(sp[key])

            if chart_planets:
                st.subheader("📋 Planetary Details Table")
                df_planets = pd.DataFrame(chart_planets)
                st.table(df_planets)
                
            # Ascendant Detail
            if "D1" in chart and "ascendant" in chart["D1"]:
                 st.caption(f"Ascendant Details: {chart['D1']['ascendant']}")

            # Prepare data for South Indian Chart (moved calculation here)
            sign_order = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            sign_counts = {s: [] for s in sign_order}
            
            # Add Ascendant
            if "D1" in chart and "ascendant" in chart["D1"]:
                asc_sign = chart["D1"]["ascendant"]["sign"]
                if asc_sign in sign_counts:
                    sign_counts[asc_sign].append("As")
            
            # Add Planets
            current_planets_list = []
            if chart_planets: # From the selection logic above
                for p in chart_planets: # p is dict
                    s = p["Sign"]
                    planet_name = p["Planet"]
                    # Shorten names for chart
                    short_name = planet_name[:2]
                    if planet_name == "Jupiter": short_name = "Ju"
                    elif planet_name == "Mars": short_name = "Ma"
                    elif planet_name == "Mercury": short_name = "Me"
                    elif planet_name == "Venus": short_name = "Ve"
                    elif planet_name == "Saturn": short_name = "Sa"
                    elif planet_name == "Moon": short_name = "Mo"
                    elif planet_name == "Sun": short_name = "Su"
                    elif planet_name == "Rahu": short_name = "Ra"
                    elif planet_name == "Ketu": short_name = "Ke"
                    
                    if s in sign_counts:
                        sign_counts[s].append(short_name)
                    
                    current_planets_list.append({"Planet": planet_name, "Sign": s})

            # --- Visualizations Moved to Bottom ---
            st.divider()
            st.subheader("🎨 Visual Chart Representation")
            
            # Helper: Sign Mapping
            element_map = {"Fire": [0, 4, 8], "Earth": [1, 5, 9], "Air": [2, 6, 10], "Water": [3, 7, 11]}
            modality_map = {"Cardinal": [0, 3, 6, 9], "Fixed": [1, 4, 7, 10], "Mutable": [2, 5, 8, 11]}
            
            # South Indian Chart HTML Generator
            def get_content(sign_name):
                 return ", ".join(sign_counts.get(sign_name, []))

            html_chart = f"""
            <style>
                .chart-grid {{ 
                    display: grid; 
                    grid-template-columns: 1fr 1fr 1fr 1fr; 
                    grid-template-rows: 100px 100px 100px 100px; 
                    gap: 2px; 
                    background-color: #000; 
                    border: 2px solid #000; 
                    width: 100%; 
                    max-width: 500px; 
                    margin: auto; 
                }}
                .chart-box {{ 
                    background-color: #ffffff; 
                    color: #000000; 
                    padding: 5px; 
                    font-size: 14px; 
                    display: flex; 
                    flex-direction: column; 
                    justify-content: center; 
                    align-items: center; 
                    text-align: center; 
                    border: 1px solid #ccc; 
                    position: relative; 
                    transition: background-color 0.3s ease, color 0.3s ease;
                }}
                .chart-label {{ 
                    font-size: 10px; 
                    color: #555; 
                    position: absolute; 
                    top: 2px; 
                    left: 2px; 
                    text-transform: uppercase; 
                }}
                .chart-content {{ 
                    font-weight: bold; 
                    color: #d62728; 
                }}
                .center-box {{ 
                    grid-column: 2 / 4; 
                    grid-row: 2 / 4; 
                    background-color: #ffffff; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    font-style: italic; 
                    color: #333; 
                    transition: background-color 0.3s ease, color 0.3s ease;
                }}
                @media (prefers-color-scheme: dark) {{
                    .chart-grid {{
                        background-color: #1a1a1a;
                        border-color: #333;
                    }}
                    .chart-box {{
                        background-color: #2a2a2a;
                        color: #e0e0e0;
                        border-color: #444;
                    }}
                    .chart-label {{
                        color: #aaa;
                    }}
                    .chart-content {{
                        color: #ff6b6b;
                    }}
                    .center-box {{
                        background-color: #2a2a2a;
                        color: #d0d0d0;
                    }}
                }}
                [data-theme="dark"] .chart-grid {{
                    background-color: #1a1a1a;
                    border-color: #333;
                }}
                [data-theme="dark"] .chart-box {{
                    background-color: #2a2a2a;
                    color: #e0e0e0;
                    border-color: #444;
                }}
                [data-theme="dark"] .chart-label {{
                    color: #aaa;
                }}
                [data-theme="dark"] .chart-content {{
                    color: #ff6b6b;
                }}
                [data-theme="dark"] .center-box {{
                    background-color: #2a2a2a;
                    color: #d0d0d0;
                }}
            </style>
            <div class="chart-grid">
                <div class="chart-box"><span class="chart-label">Pisces</span><div class="chart-content">{get_content('Pisces')}</div></div>
                <div class="chart-box"><span class="chart-label">Aries</span><div class="chart-content">{get_content('Aries')}</div></div>
                <div class="chart-box"><span class="chart-label">Taurus</span><div class="chart-content">{get_content('Taurus')}</div></div>
                <div class="chart-box"><span class="chart-label">Gemini</span><div class="chart-content">{get_content('Gemini')}</div></div>
                <div class="chart-box"><span class="chart-label">Aquarius</span><div class="chart-content">{get_content('Aquarius')}</div></div>
                <div class="center-box">South Indian Chart</div>
                <div class="chart-box"><span class="chart-label">Cancer</span><div class="chart-content">{get_content('Cancer')}</div></div>
                <div class="chart-box"><span class="chart-label">Capricorn</span><div class="chart-content">{get_content('Capricorn')}</div></div>
                <div class="chart-box"><span class="chart-label">Leo</span><div class="chart-content">{get_content('Leo')}</div></div>
                <div class="chart-box"><span class="chart-label">Sagittarius</span><div class="chart-content">{get_content('Sagittarius')}</div></div>
                <div class="chart-box"><span class="chart-label">Scorpio</span><div class="chart-content">{get_content('Scorpio')}</div></div>
                <div class="chart-box"><span class="chart-label">Libra</span><div class="chart-content">{get_content('Libra')}</div></div>
                <div class="chart-box"><span class="chart-label">Virgo</span><div class="chart-content">{get_content('Virgo')}</div></div>
            </div>
            """
            st.markdown(html_chart, unsafe_allow_html=True)
            st.caption("South Indian style chart (adapts to light/dark mode). 'As' denotes Ascendant.")
            # st.info("Visual Chart disabled for debugging (checking layout issues).")
            
            st.divider()
            
            # --- Graphical Analysis ---
            st.subheader("📈 Elemental & Modal Analysis")
            col_g1, col_g2 = st.columns(2)
            
            # Calculate Element Distribution
            element_counts = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
            modality_counts = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}
            
            # Use current_planets_list from above
            for p in current_planets_list:
                s = p["Sign"]
                if s in sign_order:
                    idx = sign_order.index(s)
                    
                    # Element
                    for elem, indices in element_map.items():
                        if idx in indices:
                            element_counts[elem] += 1
                            
                     # Modality
                    for mod, indices in modality_map.items():
                        if idx in indices:
                            modality_counts[mod] += 1
                            
            with col_g1:
                # Donut Chart for Elements
                fig_elem = px.pie(names=list(element_counts.keys()), values=list(element_counts.values()), hole=0.4, title="Elemental Balance")
                fig_elem.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_elem, width='stretch')
                with st.expander("What is Elemental Balance?"):
                    st.write("Fire (Energy), Earth (Stability), Air (Intellect), Water (Emotion)")
            
            with col_g2:
                 # Bar Chart for Modalities
                 fig_mod = px.bar(x=list(modality_counts.keys()), y=list(modality_counts.values()), title="Modality Distribution", color=list(modality_counts.keys()))
                 st.plotly_chart(fig_mod, width='stretch')
                 with st.expander("What is Modality?"):
                    st.write("Cardinal (Leaders), Fixed (Stabilizers), Mutable (Adaptable)")

        elif selected_tab == "⏳ Dasha Timeline":
            st.header("Vimshottari Dasha Timeline")
            
            if "dasha" in chart and "Vimshottari" in chart["dasha"]:
                dasha_dict = chart["dasha"]["Vimshottari"]
                
                timeline_data = []
                
                for key, val in dasha_dict.items():
                    if isinstance(val, dict) and "startDate" in val:
                        segments = key.split('-')
                        level = len(segments)
                        
                        start = pd.to_datetime(val["startDate"])
                        end = pd.to_datetime(val["endDate"])
                        
                        if level == 2:
                            major_lord = segments[0]
                            sub_lord = segments[1]
                            timeline_data.append({
                                "Period": f"{major_lord} - {sub_lord}",
                                "Start": start,
                                "Finish": end,
                                "Major Lord": major_lord,
                                "Sub Lord": sub_lord
                            })
                
                if not timeline_data:
                     for key, val in dasha_dict.items():
                         if "startDate" in val:
                             segments = key.split('-')
                             if len(segments) > 1: # At least L2
                                start = pd.to_datetime(val["startDate"])
                                end = pd.to_datetime(val["endDate"])
                                timeline_data.append({
                                    "Period": key,
                                    "Start": start,
                                    "Finish": end,
                                    "Major Lord": segments[0],
                                    "Sub Lord": segments[1] if len(segments) > 1 else segments[0]
                                })
                
                if timeline_data:
                    df_dasha = pd.DataFrame(timeline_data)
                    df_dasha = df_dasha.sort_values("Start")
                    
                    st.write("### 📅 Detailed Dasha Periods (Antardashas)")
                    fig = px.timeline(df_dasha, x_start="Start", x_end="Finish", y="Major Lord", color="Sub Lord", hover_name="Period", title="Vimshottari Dasha (Mahadasha > Antardasha)")
                    fig.update_yaxes(categoryorder="category ascending")
                    st.plotly_chart(fig, width='stretch')
                    
                    with st.expander("View Dasha Table"):
                        st.dataframe(df_dasha[["Major Lord", "Sub Lord", "Start", "Finish"]])

                    st.subheader("Current Dasha")
                    if "current" in chart["dasha"]:
                        st.json(chart["dasha"]["current"])
                else:
                    st.info("No detailed dasha data available.")
            else:
                 st.info("Dasha data not available.")

        elif selected_tab == "💬 Ask Astrologer":
            st.header("Ask the AI Astrologer")
            st.markdown(f"Ask questions based on **{st.session_state['user_name']}'s** chart.")
            
            if not api_key:
                st.warning("Please enter your Gemini API Key in the sidebar to use the Chat feature.")
            else:
                # --- Conversation Management (Sidebar Integration or Local) ---
                # Let's put conversation controls in the main Sidebar for persistent access, 
                # OR right here in columns. User asked for "Create new... button".
                # A sidebar approach is cleanest for list management.
                
                with st.sidebar:
                    st.divider()
                    st.header("💬 Chat Sessions")
                    
                    if st.button("➕ New Conversation", use_container_width=True):
                        new_id = db.create_conversation(db_conn, st.session_state['username'])
                        st.session_state['current_conversation_id'] = new_id
                        st.session_state["messages"] = [] # Clear view
                        st.rerun()

                    # Load Conversations
                    conversations = db.get_user_conversations(db_conn, st.session_state['username'])
                    
                    # Format for selectbox
                    options = {c[0]: f"{c[1]} ({c[2][:10]})" for c in conversations}
                    
                    # Ensure state exists
                    if 'current_conversation_id' not in st.session_state:
                         st.session_state['current_conversation_id'] = conversations[0][0] if conversations else None
                    
                    # Identify current selection index
                    current_index = 0
                    if st.session_state['current_conversation_id']:
                        ids = [c[0] for c in conversations]
                        if st.session_state['current_conversation_id'] in ids:
                            current_index = ids.index(st.session_state['current_conversation_id'])
                    
                    if conversations:
                        selected_conv_id = st.selectbox(
                            "Select Conversation", 
                            options=[c[0] for c in conversations],
                            format_func=lambda x: options[x],
                            index=current_index,
                            key="conv_selector"
                        )
                        
                        # Sync selection
                        if selected_conv_id != st.session_state['current_conversation_id']:
                            st.session_state['current_conversation_id'] = selected_conv_id
                            st.rerun()
                            
                        if st.button("🗑️ Delete Current", type="primary", use_container_width=True):
                            db.delete_conversation(db_conn, st.session_state['current_conversation_id'])
                            st.session_state['current_conversation_id'] = None
                            st.success("Deleted!")
                            st.rerun()
                    else:
                        st.caption("No history.")

                # --- Chat Interface ---
                
                # Verify we have a valid Conversation ID, if not create/reset
                if st.session_state['current_conversation_id'] is None:
                     # Create default if absolutely none, OR prompt user. 
                     # Better to auto-create on first message, but we need ID for loading.
                     # Let's show empty state.
                     pass
                     
                # Load History
                if st.session_state.get('current_conversation_id'):
                     history = db.get_chat_history(db_conn, st.session_state['current_conversation_id'])
                     st.session_state["messages"] = history
                else:
                     st.session_state["messages"] = [{"role": "assistant", "content": "Start a new conversation to ask questions!"}]

                for msg in st.session_state["messages"]:
                    st.chat_message(msg["role"]).write(msg["content"])

                if prompt := st.chat_input("Ask about career, marriage, health, etc..."):
                    
                    # Auto-create conversation if needed
                    if not st.session_state.get('current_conversation_id'):
                        # Use first few words as title
                        title = (prompt[:30] + '..') if len(prompt) > 30 else prompt
                        new_id = db.create_conversation(db_conn, st.session_state['username'], title)
                        st.session_state['current_conversation_id'] = new_id
                        st.rerun() # Rerun to refresh sidebar list logic

                    st.chat_message("user").write(prompt)
                    st.session_state["messages"].append({"role": "user", "content": prompt})
                    
                    # Save user message
                    db.save_chat(db_conn, st.session_state['username'], "user", prompt, st.session_state['current_conversation_id'])
                    
                    # Display assistant response with streaming
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        full_response = ""
                        
                        try:
                            with st.spinner("Consulting the stars..."):
                                # Synchronous call as requested
                                full_response = get_astrology_response(st.session_state['chart_data'], prompt, api_key)
                                message_placeholder.markdown(full_response)
                            
                            # Save assistant response only if valid
                            if not full_response.startswith("Error"):
                                db.save_chat(db_conn, st.session_state['username'], "assistant", full_response, st.session_state['current_conversation_id'])
                            
                        except Exception as e:
                            full_response = f"Error: {str(e)}"
                            message_placeholder.error(full_response)
                            # Errors are not saved to DB
                            
                        st.session_state["messages"].append({"role": "assistant", "content": full_response})


    else:
        st.info("👈 Please enter birth details and click 'Generate Birth Chart' in the sidebar to begin.")

if __name__ == "__main__":
    main()
