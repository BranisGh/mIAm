import streamlit as st
import time

st.title("This is the app title")
st.header("This is the header")
st.markdown("This is the markdown")
st.subheader("This is the subheader")
st.caption("This is the caption")
st.code("x = 2021")
st.latex(r''' a+a r^1+a r^2+a r^3 ''')

st.image("/home/branis/Pictures/Screenshots/Screenshot from 2024-06-27 15-11-23.png", caption="A kid playing")
st.audio("/home/branis/Downloads/file_example_MP3_700KB.mp3")
st.video("/home/branis/Downloads/file_example_MP4_480_1_5MG.mp4")

st.checkbox('Yes')
st.button('Click Me')
st.radio('Pick your gender', ['Male', 'Female'])
st.selectbox('Pick a fruit', ['Apple', 'Banana', 'Orange'])
st.multiselect('Choose a planet', ['Jupiter', 'Mars', 'Neptune'])
st.select_slider('Pick a mark', ['Bad', 'Good', 'Excellent'])
st.slider('Pick a number', 0, 50)

st.number_input('Pick a number', 0, 10)
st.text_input('Email address')
st.date_input('Traveling date')
st.time_input('School time')
st.text_area('Description')
st.file_uploader('Upload a photo')
st.color_picker('Choose your favorite color')


st.balloons()  
st.progress(30)  
with st.spinner('Wait for it...'):    
    time.sleep(3)  # Simulating a process delay

st.success("You did it!")
st.error("Error occurred")
st.warning("This is a warning")
st.info("It's easy to build a Streamlit app")
st.exception(RuntimeError("RuntimeError exception"))

st.sidebar.title("Sidebar Title")
st.sidebar.markdown("This is the sidebar content")
st.sidebar.button("Click Me too")
st.sidebar.checkbox("No")
st.sidebar.radio("Pick your favorit dish", ["Pasta", "Pizza", "Salad"])


with st.container():    
    st.write("This is inside the container")