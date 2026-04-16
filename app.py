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

st.set_page_config(layout="wide")
st.title("Systematic Review Extraction")

# Initialize Session States
if 'generated_study_id' not in st.session_state:
    st.session_state.generated_study_id = str(random.randint(10000, 99999))
if 'active_study_id' not in st.session_state:
    st.session_state.active_study_id = "None Selected"
if 'active_study_title' not in st.session_state:
    st.session_state.active_study_title = "Unknown Title"
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Demographics"

# Helper to clean data
def clean_data(data_dict):
    cleaned = {}
    for k, v in data_dict.items():
        if v == "" or v == "N/A" or v is None:
            cleaned[k] = None
        elif v == "Yes": 
            cleaned[k] = True
        elif v == "No":
            cleaned[k] = False
        else:
            cleaned[k] = v
    return cleaned

# Helper to format subgroup objects for the dataframe
def format_subgroups(val):
    if isinstance(val, list):
        items = []
        for item in val:
            name = item.get('Subgroup_Name', 'Unknown')
            n = item.get('N', '0')
            items.append(f"{name}: {n}")
        return ", ".join(items)
    return val

# --- SIDEBAR TRACKER ---
st.sidebar.header("Reviewer Status")
try:
    count_response = supabase.table("study_metadata").select("id", count="exact").execute()
    total_studies = count_response.count if count_response.count else 0
    st.sidebar.metric("Total Studies Logged", total_studies)
except:
    st.sidebar.metric("Total Studies Logged", "Error")

# --- NAVIGATION CONTROL ---
view_col1, view_col2 = st.columns(2)
with view_col1:
    if st.button("1. Extract Demographics", use_container_width=True):
        st.session_state.current_view = "Demographics"
with view_col2:
    if st.button("2. Extract Characteristics", use_container_width=True):
        st.session_state.current_view = "Characteristics"

st.divider()

# --- VIEW 1: DEMOGRAPHICS ---
if st.session_state.current_view == "Demographics":
    with st.form("metadata_form"):
        st.subheader("Extract Study Demographics")
        meta_data = {}
        
        for field in config['table_1']:
            if field['name'] == 'Study_ID':
                meta_data[field['name']] = st.text_input(field['label'], value=st.session_state.generated_study_id)
            elif field['type'] == 'text': 
                meta_data[field['name']] = st.text_input(field['label'], value="")
            elif field['type'] in ['number_int', 'number_float']: 
                step_val = 1 if field['type'] == 'number_int' else 0.1
                meta_data[field['name']] = st.number_input(field['label'], step=step_val, value=None)
            elif field['type'] == 'select': 
                options = ["N/A"] + field['options']
                meta_data[field['name']] = st.selectbox(field['label'], options)
            elif field['type'] == 'checkbox': 
                meta_data[field['name']] = st.selectbox(field['label'], ["N/A", "Yes", "No"])
            elif field['type'] == 'text_area': 
                meta_data[field['name']] = st.text_area(field['label'], value="")
            elif field['type'] == 'dynamic_table':
                st.write(f"**{field['label']}**")
                edited_df = st.data_editor(pd.DataFrame(columns=field['columns']), num_rows="dynamic", key=f"meta_{field['name']}")
                meta_data[field['name']] = edited_df.to_dict(orient='records')
        
        if st.form_submit_button("Save Study Demographics"):
            clean_meta = clean_data(meta_data)
            
            supabase.table("study_metadata").insert({
                "study_id": clean_meta.get("Study_ID"), 
                "extracted_data": clean_meta
            }).execute()
            
            # Save context for next step
            st.session_state.active_study_id = clean_meta.get("Study_ID")
            st.session_state.active_study_title = clean_meta.get("Study_Title", "Unknown Title")
            st.session_state.generated_study_id = str(random.randint(10000, 99999))
            
            st.success("Demographics saved successfully!")
            
    # Show button outside form to trigger view change
    if st.session_state.active_study_id != "None Selected":
        if st.button("Proceed to Characteristics Form", type="primary"):
            st.session_state.current_view = "Characteristics"
            st.rerun()

# --- VIEW 2: CHARACTERISTICS ---
elif st.session_state.current_view == "Characteristics":
    st.subheader(f"Extract Characteristics for: {st.session_state.active_study_title}")
    st.caption(f"Study ID: {st.session_state.active_study_id}")
    
    if st.session_state.active_study_id == "None Selected":
        st.warning("Please save Demographics first to lock in the Study ID.")
    else:
        # clear_on_submit=True instantly resets the form for the next metric entry
        with st.form("metrics_form", clear_on_submit=True):
            metric_data = {}
            for field in config['table_2']:
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
                clean_metric["Study_ID"] = st.session_state.active_study_id
                
                feature = str(clean_metric.get('MRI_Feature_Tested', 'unknown'))
                clean_feature = "".join(char for char in feature if char.isalnum()).lower()
                clean_metric["Metric_ID"] = f"{st.session_state.active_study_id}_{clean_feature}"
                
                supabase.table("diagnostic_metrics").insert({
                    "study_id": st.session_state.active_study_id, 
                    "metric_data": clean_metric
                }).execute()
                
                st.success(f"Row saved! The form is now cleared and ready for the next metric.")

# --- DATABASE VIEW ---
st.divider()
st.subheader("Current Database Records")

if st.button("Refresh Database Tables"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Study Demographics**")
        meta_resp = supabase.table("study_metadata").select("*").execute()
        if meta_resp.data:
            meta_records = []
            for row in meta_resp.data:
                flat_record = row['extracted_data']
                # Fix the object display issue
                if 'Subgroup_Sample_Sizes' in flat_record:
                    flat_record['Subgroup_Sample_Sizes'] = format_subgroups(flat_record['Subgroup_Sample_Sizes'])
                meta_records.append(flat_record)
            st.dataframe(pd.DataFrame(meta_records))
        else:
            st.info("No demographics found.")
            
    with col2:
        st.write("**Study Characteristics**")
        metric_resp = supabase.table("diagnostic_metrics").select("*").execute()
        if metric_resp.data:
            metric_records = []
            for row in metric_resp.data:
                flat_record = row['metric_data']
                metric_records.append(flat_record)
            st.dataframe(pd.DataFrame(metric_records))
        else:
            st.info("No characteristics found.")
