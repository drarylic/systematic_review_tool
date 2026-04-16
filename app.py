import streamlit as st
import json
import pandas as pd
from supabase import create_client, Client

# Load configuration
with open('variables.json', 'r') as file:
    config = json.load(file)

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

st.title("DCM Systematic Review Extraction")

# Use tabs to separate Metadata and Metrics
tab1, tab2 = st.tabs(["1. Study Metadata", "2. Diagnostic Metrics"])

# --- TAB 1: METADATA ---
with tab1:
    with st.form("metadata_form"):
        st.subheader("Extraction Table 1: Study Metadata")
        meta_data = {}
        for field in config['table_1']:
            if field['type'] == 'text': meta_data[field['name']] = st.text_input(field['label'])
            elif field['type'] == 'number_int': meta_data[field['name']] = st.number_input(field['label'], step=1)
            elif field['type'] == 'number_float': meta_data[field['name']] = st.number_input(field['label'], step=0.1)
            elif field['type'] == 'select': meta_data[field['name']] = st.selectbox(field['label'], field['options'])
            elif field['type'] == 'checkbox': meta_data[field['name']] = st.checkbox(field['label'])
            elif field['type'] == 'text_area': meta_data[field['name']] = st.text_area(field['label'])
            elif field['type'] == 'dynamic_table':
                st.write(f"**{field['label']}**")
                edited_df = st.data_editor(pd.DataFrame(columns=field['columns']), num_rows="dynamic", key=f"meta_{field['name']}")
                meta_data[field['name']] = edited_df.to_dict(orient='records')
        
        if st.form_submit_button("Save Study Metadata"):
            supabase.table("study_metadata").insert({"study_id": meta_data.get("Study_ID"), "extracted_data": meta_data}).execute()
            st.session_state['active_study'] = meta_data.get("Study_ID") # Keep track of ID for Table 2
            st.success(f"Metadata for {meta_data.get('Study_ID')} saved! Now go to Tab 2.")

# --- TAB 2: METRICS ---
with tab2:
    current_study = st.session_state.get('active_study', "None Selected")
    st.subheader(f"Adding Metrics for: {current_study}")
    
    if current_study == "None Selected":
        st.warning("Please save Metadata in Tab 1 first to lock in the Study ID.")
    else:
        with st.form("metrics_form"):
            metric_data = {"Study_ID": current_study} # Auto-fill Foreign Key
            for field in config['table_2']:
                if field['name'] == "Study_ID": continue # Skip as we auto-fill it
                if field['type'] == 'text': metric_data[field['name']] = st.text_input(field['label'])
                elif field['type'] == 'number_int': metric_data[field['name']] = st.number_input(field['label'], step=1)
                elif field['type'] == 'number_float': metric_data[field['name']] = st.number_input(field['label'], step=0.1)
                elif field['type'] == 'select': metric_data[field['name']] = st.selectbox(field['label'], field['options'])
            
            if st.form_submit_button("Save Metric Row"):
                # We save this to a separate table called 'diagnostic_metrics'
                supabase.table("diagnostic_metrics").insert({
                    "study_id": current_study, 
                    "metric_data": metric_data
                }).execute()
                st.success(f"Metric '{metric_data.get('MRI_Feature_Tested')}' added to {current_study}!")
