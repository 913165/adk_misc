import streamlit as st
import pandas as pd
import numpy as np

st.title("Sales Chart")

days = st.slider("Select number of days", 5, 30, 10)

data = pd.DataFrame({
    "Day": range(1, days+1),
    "Sales": np.random.randint(100, 500, days)
})

st.line_chart(data.set_index("Day"))