import streamlit as st
from openai import OpenAI
import os

# Show title and description.
st.write(
    "I am a chatbot that can help FBCs answer some of the questions they get from the owners."
)

# Load policy documents into memory
doc_options = {
    "Franchise Operations Policy": "policy_doc_1.txt",
    "Employee Conduct Policy": "policy_doc_2.txt",
}

documents = {}
for title, filepath in doc_options.items():
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            documents[title] = file.read()
    else:
        st.error(f"Document '{filepath}' not found.")

# Check if the API key is in session state
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""

# If the API key is not set, display the input field
if not st.session_state.openai_api_key:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if openai_api_key:
        st.session_state.openai_api_key = openai_api_key
        st.experimental_rerun()  # Rerun the script to immediately hide the input after setting the key

# If the API key is set, proceed with the chatbot functionality
if st.session_state.openai_api_key:
    # Create an OpenAI client.
    client = OpenAI(api_key=st.session_state.openai_api_key)

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
 
