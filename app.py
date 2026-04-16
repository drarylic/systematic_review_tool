import streamlit as st
import json
import pandas as pd
import random
from supabase import create_client, Client

# Load configuration
with open('variables.json', 'r') as file:
    config = json.load(file)

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

st.title("DCM Systematic Review Extraction")

# Initialize Session States for Auto-IDs
if 'generated_study_id' not in st.session_state:
    st.session_state.generated_study_id = str(random.randint(10000, 99999))
if 'active_study' not in st.session_state:
    st.session_state.active_study = "None Selected"

# Helper function to convert missing inputs to None (JSON null)
def clean_data(data_dict):
    cleaned = {}
    for k, v in data_dict.items():
        if v == "" or v == "N/A" or v is None:
            cleaned[k] = None
        elif v == "Yes": # Map checkbox fallbacks
            cleaned[k] = True
        elif v == "No":
            cleaned[k] = False
        else:
            cleaned[k] = v
    return cleaned

# Tab setup
tab1, tab2 = st.tabs(["Extract Study Demographics", "Extract Study Characteristics"])

# --- TAB 1: DEMOGRAPHICS (Study Metadata) ---
with tab1:
    with st.form("metadata_form"):
        st.subheader("Extract Study Demographics")
        meta_data = {}
        
        for field in config['table_1']:
            if field['name'] == 'Study_ID':
                # Auto-populate random ID
                meta_data[field['name']] = st.text_input(field['label'], value=st.session_state.generated_study_id)
                
            elif field['type'] == 'text': 
                meta_data[field['name']] = st.text_input(field['label'], value="")
                
            elif field['type'] in ['number_int', 'number_float']: 
                # value=None leaves the box blank initially
                step_val = 1 if field['type'] == 'number_int' else 0.1
                meta_data[field['name']] = st.number_input(field['label'], step=step_val, value=None)
                
            elif field['type'] == 'select': 
                # Prepend N/A to options
                options = ["N/A"] + field['options']
                meta_data[field['name']] = st.selectbox(field['label'], options)
                
            elif field['type'] == 'checkbox': 
                # Convert checkbox to selectbox to allow for an N/A state
                meta_data[field['name']] = st.selectbox(field['label'], ["N/A", "Yes", "No"])
                
            elif field['type'] == 'text_area': 
                meta_data[field['name']] = st.text_area(field['label'], value="")
                
            elif field['type'] == 'dynamic_table':
                st.write(f"**{field['label']}**")
                edited_df = st.data_editor(pd.DataFrame(columns=field['columns']), num_rows="dynamic", key=f"meta_{field['name']}")
                meta_data[field['name']] = edited_df.to_dict(orient='records')
        
        if st.form_submit_button("Save Study Demographics"):
            # Clean empty fields to nulls
            clean_meta = clean_data(meta_data)
            
            # Save to database
            supabase.table("study_metadata").insert({
                "study_id": clean_meta.get("Study_ID"), 
                "extracted_data": clean_meta
            }).execute()
            
            # Update session states for Tab 2 and generate next ID
            st.session_state.active_study = clean_meta.get("Study_ID")
            st.session_state.generated_study_id = str(random.randint(10000, 99999))
            
            st.success(f"Demographics for Study ID {st.session_state.active_study} saved! Proceed to the next tab.")

# --- TAB 2: CHARACTERISTICS (Diagnostic Metrics) ---
with tab2:
    current_study = st.session_state.active_study
    st.subheader(f"Extract Study Characteristics for ID: {current_study}")
    
    if current_study == "None Selected":
        st.warning("Please save Demographics in the first tab to lock in the Study ID.")
    else:
        with st.form("metrics_form"):
            metric_data = {}
            for field in config['table_2']:
                # Skip IDs as we handle them under the hood
                if field['name'] in ["Study_ID", "Metric_ID"]: 
                    continue 
                
                if field['type'] == 'text': 
                    metric_data[field['name']] = st.text_input(field['label'], value="")
                elif field['type'] in ['number_int', 'number_float']: 
                    step_val = 1 if field['type'] == 'number_int' else 0.1
                    metric_data[field['name']] = st.number_input(field['label'], step=step_val, value=None)
                elif field['type'] == 'select': 
                    options = ["N/A"] + field['options']
                    metric_data[field['name']] = st.selectbox(field['label'], options)
            
            if st.form_submit_button("Save Characteristic Row"):
                clean_metric = clean_data(metric_data)
                clean_metric["Study_ID"] = current_study
                
                # Auto-generate Metric ID (e.g., 59281_t2hyperintensity)
                feature = str(clean_metric.get('MRI_Feature_Tested', 'unknown'))
                clean_feature = "".join(char for char in feature if char.isalnum()).lower()
                clean_metric["Metric_ID"] = f"{current_study}_{clean_feature}"
                
                # Save to database
                supabase.table("diagnostic_metrics").insert({
                    "study_id": current_study, 
                    "metric_data": clean_metric
                }).execute()
                
                st.success(f"Characteristic row (ID: {clean_metric['Metric_ID']}) added to Study {current_study}!")

# --- DATABASE VIEW ---
st.divider()
st.subheader("Current Database Records (Demographics)")

if st.button("Refresh Database View"):
    response = supabase.table("study_metadata").select("*").execute()
    if response.data:
        records = []
        for row in response.data:
            flat_record = row['extracted_data']
            flat_record['database_id'] = row['id']
            records.append(flat_record)
        st.dataframe(pd.DataFrame(records))
    else:
        st.info("The database is currently empty.")
