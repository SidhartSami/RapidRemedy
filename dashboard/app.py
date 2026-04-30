import streamlit as st
import requests
import os

st.set_page_config(page_title="Rapid Remedy Dashboard", page_icon="💊")

st.title("💊 Rapid Remedy Dashboard")
st.write("Welcome to the Rapid Remedy medical information dashboard.")

backend_url = os.getenv("BACKEND_URL", "http://backend:8000")

if st.button("Check Backend Health"):
    try:
        response = requests.get(f"{backend_url}/health")
        if response.status_code == 200:
            st.success(f"Backend is healthy! Status: {response.json()['status']}")
        else:
            st.error(f"Backend returned error: {response.status_code}")
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
