import streamlit as st
from openai import OpenAI
import os

# Show title and description.
st.header(
    "FBC-Chatbot to answer questions."
)

# Display sample questions for users to try
st.write(
    """
    Here are some example questions you can ask me:
    
    - "What are the reporting requirements for franchises?"
    - "Can a franchise deviate from the standard operating procedures?"
    - "What should be done if an employee violates the conduct policy?"
    - "Is there a dress code employees need to follow?"
    - "What policies should a franchise follow regarding employee training?"
    """
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
            context = documents.get("Franchise Operations Policy", "")
        elif "employee" in prompt.lower() or "conduct" in prompt.lower():
            context = documents.get("Employee Conduct Policy", "")

        # Combine the context with the user's prompt for the OpenAI API.
        system_message = (
            "You are a helpful assistant with access to the following policy documents. "
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
