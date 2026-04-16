import streamlit as st
import json
import pandas as pd
from supabase import create_client, Client

# Load configuration from your variables.json file
with open('variables.json', 'r') as file:
    config = json.load(file)

# Initialize Supabase client securely
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("Systematic Review Data Extraction")

with st.form("extraction_form"):
    st.subheader("Extraction Table 1: Study Metadata")
    
    form_data = {}
    
    # Dynamically build inputs based on your JSON configuration
    for field in config['table_1']:
        if field['type'] == 'text':
            form_data[field['name']] = st.text_input(field['label'])
            
        elif field['type'] == 'number_int':
            form_data[field['name']] = st.number_input(field['label'], step=1, value=0)
            
        elif field['type'] == 'number_float':
            form_data[field['name']] = st.number_input(field['label'], step=0.1, value=0.0)
            
        elif field['type'] == 'select':
            form_data[field['name']] = st.selectbox(field['label'], field['options'])
            
        elif field['type'] == 'checkbox':
            form_data[field['name']] = st.checkbox(field['label'])
            
        elif field['type'] == 'text_area':
            form_data[field['name']] = st.text_area(field['label'])
            
        # Handle the dynamic tables for things like variable patient subgroups
        elif field['type'] == 'dynamic_table':
            st.write(f"**{field['label']}**")
            df_template = pd.DataFrame(columns=field['columns'])
            
            edited_df = st.data_editor(
                df_template, 
                num_rows="dynamic", 
                use_container_width=True,
                key=field['name']
            )
            form_data[field['name']] = edited_df.to_dict(orient='records')
            
    submitted = st.form_submit_button("Save to Supabase Database")
    
    if submitted:
        # Prepare the payload for the database
        db_payload = {
            "study_id": form_data.get("Study_ID", "Unknown"),
            "extracted_data": form_data
        }
        
        try:
            # Insert the data into your Supabase table
            data, count = supabase.table("study_metadata").insert(db_payload).execute()
            st.success(f"Data for {form_data.get('Study_ID')} successfully saved to Supabase!")
        except Exception as e:
            st.error(f"Error saving data: {str(e)}")

# Add a section at the bottom for the team to view the live database records
st.divider()
st.subheader("Current Database Records")

if st.button("Refresh Database View"):
    # Fetch all records from the database
    response = supabase.table("study_metadata").select("*").execute()
    
    if response.data:
        # Flatten the JSONB data to make it cleanly readable in a dataframe
        records = []
        for row in response.data:
            flat_record = row['extracted_data']
            flat_record['database_id'] = row['id']
            records.append(flat_record)
            
        st.dataframe(pd.DataFrame(records))
    else:
        st.info("The database is currently empty.")
