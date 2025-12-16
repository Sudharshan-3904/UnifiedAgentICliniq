import streamlit as st
import requests
import json
import time

# Page Config
st.set_page_config(
    page_title="MedTool Agent",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .success-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .error-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

# Title and Header
st.title("🏥 MedTool Agent")

# Sidebar for Configuration
with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("Backend API URL", "http://localhost:8000/run")
    st.markdown("---")
    mode = st.radio("Mode", ["Chat Assistant", "Medical Calculators"])
    st.markdown("---")
    st.markdown("### Status")
    st.info("Ready to process queries.")

def process_query(query_text):
    with st.spinner("Agent is processing..."):
        try:
            start_time = time.time()
            # Include thread id for conversational context
            thread_id = st.session_state.get("thread_id")
            payload = {"query": query_text}
            if thread_id:
                payload["thread_id"] = thread_id
            response = requests.post(api_url, json=payload)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                
                # Display Results
                st.markdown("---")
                st.subheader("Assistant Response")

                is_valid = data.get("is_valid", False)
                generation = data.get("generation", "No response generated.")
                safety_report = data.get("safety_report", "No safety report available.")

                if is_valid:
                    st.markdown(f'<div class="success-box">{generation}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="error-box"><strong>Response Rejected by Safety Agent</strong><br>{generation}</div>', unsafe_allow_html=True)

                # Conversation view
                conv_msgs = data.get("messages", [])
                if conv_msgs:
                    with st.expander("🗨️ Conversation", expanded=True):
                        for m in conv_msgs:
                            role = m.get("role", "human")
                            content = m.get("content", "")
                            if role.startswith("ai") or role.startswith("aimessage") or role.startswith("assistant"):
                                st.markdown(f"**Assistant:** {content}")
                            elif role.startswith("system"):
                                st.markdown(f"**System:** {content}")
                            else:
                                st.markdown(f"**You:** {content}")

                # Save thread id back to session
                returned_thread = data.get("thread_id")
                if returned_thread:
                    st.session_state["thread_id"] = returned_thread

                # Metrics
                st.caption(f"Processed in {end_time - start_time:.2f} seconds")

                # Detailed View
                with st.expander("🛡️ Safety Report", expanded=False):
                    if is_valid:
                        st.success("Passed Safety Checks")
                    else:
                        st.error("Failed Safety Checks")
                    st.write(safety_report)

                with st.expander("🔍 Raw API Response"):
                    st.json(data)
                        
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Connection Error: {e}")

if mode == "Chat Assistant":
    st.markdown("### AI-Powered Medical Assistant with Safety Verification")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Patient / Medical Query")
        query = st.text_area("Enter your medical question or patient scenario:", height=150, placeholder="e.g., What are the first-line treatments for hypertension in a 45-year-old male?")
        
        submit_btn = st.button("Analyze & Respond", use_container_width=True)
        reset_btn = st.button("Reset Conversation")
        
    if submit_btn:
        if query:
            process_query(query)
        else:
            st.warning("Please enter a query first.")

    if reset_btn:
        # Reset session on the backend
        thread_id = st.session_state.get("thread_id")
        if thread_id:
            try:
                requests.post(api_url, json={"thread_id": thread_id, "reset": True})
                st.session_state.pop("thread_id", None)
                st.success("Conversation reset.")
            except Exception as e:
                st.error(f"Failed to reset conversation: {e}")
        else:
            st.info("No active conversation to reset.")
            
    with col2:
        st.info("💡 Tip: You can ask about treatments, guidelines, or use the calculators in the other tab.")

elif mode == "Medical Calculators":
    st.markdown("### Clinical Calculators")
    
    calc_type = st.selectbox("Select Calculator", [
        "BMI Calculator",
        "Target Heart Rate",
        "Blood Volume",
        "Daily Water Intake",
        "Waist-to-Hip Ratio",
        "LDL Cholesterol"
    ])
    
    st.markdown("---")
    
    if calc_type == "BMI Calculator":
        st.subheader("Body Mass Index (BMI)")
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Weight", min_value=0.0, value=70.0, step=0.1)
            weight_unit = st.selectbox("Weight Unit", ["kg", "lbs"])
        with col2:
            height = st.number_input("Height", min_value=0.0, value=1.75, step=0.01)
            height_unit = st.selectbox("Height Unit", ["m", "cm", "ft", "in"])
            
        if st.button("Calculate BMI"):
            # Construct query for the agent
            query = f"Calculate BMI for weight {weight} {weight_unit} and height {height} {height_unit}"
            process_query(query)

    elif calc_type == "Target Heart Rate":
        st.subheader("Target Heart Rate Zone")
        age = st.number_input("Age", min_value=1, max_value=120, value=30, step=1)
        
        if st.button("Calculate Heart Rate"):
            query = f"Calculate target heart rate for age {age}"
            process_query(query)

    elif calc_type == "Blood Volume":
        st.subheader("Estimated Blood Volume (Nadler's Equation)")
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Weight", min_value=0.0, value=70.0, step=0.1)
            weight_unit = st.selectbox("Weight Unit", ["kg", "lbs"])
            sex = st.selectbox("Biological Sex", ["Male", "Female"])
        with col2:
            height = st.number_input("Height", min_value=0.0, value=1.75, step=0.01)
            height_unit = st.selectbox("Height Unit", ["m", "cm", "ft", "in"])
            
        if st.button("Calculate Blood Volume"):
            query = f"Calculate blood volume for a {sex} with weight {weight} {weight_unit} and height {height} {height_unit}"
            process_query(query)

    elif calc_type == "Daily Water Intake":
        st.subheader("Daily Water Intake Recommendation")
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Weight", min_value=0.0, value=70.0, step=0.1)
        with col2:
            weight_unit = st.selectbox("Weight Unit", ["kg", "lbs"])
            
        if st.button("Calculate Water Intake"):
            query = f"Calculate daily water intake for weight {weight} {weight_unit}"
            process_query(query)

    elif calc_type == "Waist-to-Hip Ratio":
        st.subheader("Waist-to-Hip Ratio (WHR)")
        col1, col2 = st.columns(2)
        with col1:
            waist = st.number_input("Waist Circumference", min_value=0.0, value=80.0, step=0.1)
        with col2:
            hip = st.number_input("Hip Circumference", min_value=0.0, value=90.0, step=0.1)
            
        if st.button("Calculate WHR"):
            query = f"Calculate waist to hip ratio for waist {waist} and hip {hip}"
            process_query(query)

    elif calc_type == "LDL Cholesterol":
        st.subheader("LDL Cholesterol Estimation (Friedewald)")
        col1, col2, col3 = st.columns(3)
        with col1:
            total = st.number_input("Total Cholesterol", min_value=0.0, value=200.0)
        with col2:
            hdl = st.number_input("HDL Cholesterol", min_value=0.0, value=50.0)
        with col3:
            trig = st.number_input("Triglycerides", min_value=0.0, value=150.0)
            
        unit = st.selectbox("Unit", ["mg/dL", "mmol/L"])
        
        if st.button("Calculate LDL"):
            query = f"Calculate LDL cholesterol for Total {total}, HDL {hdl}, Triglycerides {trig} in {unit}"
            process_query(query)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #666;'>MedTool Agent v1.1 | Powered by LangGraph & Ollama</div>", unsafe_allow_html=True)
