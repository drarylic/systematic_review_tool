import streamlit as st
import json
import pandas as pd

# Load configuration
with open('variables.json', 'r') as file:
    config = json.load(file)

st.title("Systematic Review Data Extraction")

# Initialize session state for temporary data storage
if 'temp_data' not in st.session_state:
    st.session_state.temp_data = []

with st.form("extraction_form"):
    st.subheader("Extraction Table 1: Study Metadata")
    
    form_data = {}
    
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
            
    submitted = st.form_submit_button("Save to Master Datasheet")
    
    if submitted:
        st.session_state.temp_data.append(form_data)
        st.success("Data saved successfully!")

if st.session_state.temp_data:
    st.write("Current Extracted Cohort:")
    st.dataframe(pd.DataFrame(st.session_state.temp_data))