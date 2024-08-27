import streamlit as st
from openai import OpenAI
import os

# Custom CSS to style the app
st.markdown("""
    <style>
    body {
        background-color: #F0F0F0;  /* Light gray background */
        font-family: 'Arial', sans-serif;
    }
    .title {
        font-size: 36px;
        color: #0D47A1;  /* Deep Blue color */
        text-align: center;
        padding: 20px 0;
    }
    .description {
        font-size: 18px;
        color: #333333;  /* Dark Charcoal color */
        text-align: center;
        padding-bottom: 20px;
    }
    .chat-message {
        border-radius: 15px;
        padding: 10px;
        margin: 10px 0;
    }
    .user-message {
        background-color: #D5F5E3;  /* Light Green background */
        text-align: right;
        margin-right: 10px;
    }
    .bot-message {
        background-color: #ECEFF1;  /* Light Grayish Blue background */
        text-align: left;
        margin-left: 10px;
    }
    .sample-questions {
        font-size: 18px;
        color: #0D47A1;  /* Deep Blue color */
        background-color: #E3F2FD;  /* Soft Blue background */
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        font-style: italic;
    }
    .input-box {
        padding: 15px;
        border-radius: 15px;
        font-size: 18px;
        border: 2px solid #ccc;
    }
    </style>
""", unsafe_allow_html=True)

# Header with a title
st.markdown("<div class='title'>💬 FBC Chatbot</div>", unsafe_allow_html=True)
st.markdown("<div class='description' style="color: #0D47A1; font-size: 20px; background-color: #F0F0F0; padding: 10px; border-radius: 8px;">
    I am here to help FBCs answer questions from franchise owners.
</div>", unsafe_allow_html=True)

# Display sample questions for users to try with a light blue background, deep blue font, and italic font
st.markdown("<div class='sample-questions'><strong>Sample Questions</strong><br>"
            "- What are the reporting requirements for franchises?<br>"
            "- Can a franchise deviate from the standard operating procedures?<br>"
            "- What should be done if an employee violates the conduct policy?<br>"
            "- Is there a dress code employees need to follow?<br>"
            "- What policies should a franchise follow regarding employee training?</div>",
            unsafe_allow_html=True)

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
openai_api_key = st.text_input("OpenAI API Key", type="password", key="input-box")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the existing chat messages with custom styling.
    for message in st.session_state.messages:
        message_class = "user-message" if message["role"] == "user" else "bot-message"
        st.markdown(f"<div class='chat-message {message_class}'>{message['content']}</div>", unsafe_allow_html=True)

    # Create a chat input field with custom styling.
    if prompt := st.text_input("Ask a question:", key="chat-input"):
        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(f"<div class='chat-message user-message'>{prompt}</div>", unsafe_allow_html=True)

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
        response = ""
        for message in stream:
            response += message["choices"][0]["delta"].get("content", "")

        st.markdown(f"<div class='chat-message bot-message'>{response}</div>", unsafe_allow_html=True)
        st.session_state.messages.append({"role": "assistant", "content": response})
