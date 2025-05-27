import streamlit as st
import sys
from io import StringIO
from harvey_torbett_fishing import FishingGame

# Initialize game in session state
if 'game' not in st.session_state:
    st.session_state.game = FishingGame()
    st.session_state.output = []

st.title("🎣 Harvey Torbett Fly Fishing Simulator")
st.subheader("A Thoroughly British Angling Adventure")

# Display game output
if st.session_state.output:
    for message in st.session_state.output[-10:]:  # Show last 10 messages
        st.text(message)

# Display current stats
game = st.session_state.game
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Determination", f"{game.determination}%")
    st.metric("Dignity", f"{game.dignity}%")
with col2:
    st.metric("Fish Caught", game.fish_caught)
    st.metric("Attempts", game.attempts)
with col3:
    st.metric("Inspiration", f"{game.inspiration_level}%")
    st.metric("Chaos Level", f"{game.mishap_level}/{game.max_mishap_level}")

# Command input
command = st.text_input("What would you like to do?", key="command_input")

if st.button("Execute Command") and command:
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        game.execute_command(command.lower().strip())
        output = captured_output.getvalue()
        if output:
            st.session_state.output.append(f"> {command}")
            st.session_state.output.append(output)
    finally:
        sys.stdout = old_stdout
    
    st.rerun()

# Quick action buttons
st.subheader("Quick Actions")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("Cast Rod"):
        st.session_state.command_input = "cast rod"
        st.rerun()
with col2:
    if st.button("Attach Fly"):
        st.session_state.command_input = "attach fly"
        st.rerun()
with col3:
    if st.button("Drink Thermos"):
        st.session_state.command_input = "drink thermos"
        st.rerun()
with col4:
    if st.button("Show Stats"):
        st.session_state.command_input = "stats"
        st.rerun()