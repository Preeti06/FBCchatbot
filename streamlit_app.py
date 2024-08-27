import streamlit as st
from openai import OpenAI
import os
import pandas as pd
import requests
from st_files_connection import FilesConnection

# Function to download the Excel file from GitHub
def download_excel_from_github():
    url = "https://raw.githubusercontent.com/Preeti06/FBCchatbot/main/Test_sheet.xlsx"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open("data.xlsx", "wb") as file:
                file.write(response.content)
        else:
            st.error(f"Failed to download the Excel file. Status code: {response.status_code}")
    except Exception as e:
        st.error(f"An error occurred while downloading the Excel file: {e}")

# Function to load the Excel data into a Pandas DataFrame
def load_excel_data():
    file_path = "data.xlsx"
    if os.path.exists(file_path):
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            return df
        except Exception as e:
            st.error(f"An error occurred while reading the Excel file: {e}")
    else:
        st.error("Excel file not found.")
    return None

# Download and load the Excel data
download_excel_from_github()
df = load_excel_data()

# Show title and description.
st.title("FBC Chatbot - here to help")

# Remove the section that displays the Excel data
# if df is not None:
#     st.write("### Excel Data")
#     st.dataframe(df)

# Display sample questions for users to try with a smaller font size for the header
st.markdown("""
    <p style='font-style: italic;'>
        Here are some example questions you can ask me about the data:<br>
        - "What are the top-performing franchises?"<br>
        - "Which franchises have the highest operating costs?"<br>
        - "Can you identify any sales trends?"
    </p>
""", unsafe_allow_html=True)

conn = st.connection('s3', type=FilesConnection)

# Ask user for their OpenAI API key via `st.text_input`.
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the existing chat messages.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a chat input field.
    if prompt := st.chat_input("Ask a question:"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare the context for the chatbot by including relevant policy document text.
        context = ""
        if "franchise" in prompt.lower():
            context = conn.read("fbc-hackathon-test/policy_doc_1.txt", input_format="text", ttl=600)
        elif "employee" in prompt.lower() or "conduct" in prompt.lower():
            context = conn.read("fbc-hackathon-test/policy_doc_2.txt", input_format="text", ttl=600)

        # Combine the context with the user's prompt for the OpenAI API.
        system_message = (
            "You are a helpful assistant with access to the following policy documents and business data. "
            "Use the content to answer questions accurately."
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{context}\n\n{prompt}"},
        ]

        # Generate a response using the OpenAI API.
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
        )

        # Stream the response to the chat and store it in session state.
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
