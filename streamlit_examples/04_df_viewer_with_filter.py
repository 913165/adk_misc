import streamlit as st
import pandas as pd

st.title("Employee Data Viewer")

data = {
    "Name": ["Amit", "Neha", "Rahul", "Sneha", "Vikram"],
    "Department": ["IT", "HR", "IT", "Finance", "HR"],
    "Salary": [70000, 50000, 80000, 60000, 55000]
}

df = pd.DataFrame(data)

dept = st.selectbox("Select Department", df["Department"].unique())

filtered_df = df[df["Department"] == dept]

st.write("Filtered Data")
st.dataframe(filtered_df)