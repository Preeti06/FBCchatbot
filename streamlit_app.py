import streamlit as st
import pandas as pd
from io import BytesIO
from openai import OpenAI
from st_files_connection import FilesConnection

# Function to load CSV data from S3 into a Pandas DataFrame
def load_csv_data_from_s3(conn, file_key):
    try:
        st.write(f"Attempting to read CSV file '{file_key}' from S3...")
        file_content = conn.read(file_key, input_format="text")
        df = pd.read_csv(BytesIO(file_content.encode()))
        st.write("Successfully loaded CSV data into DataFrame.")
        return df
    except Exception as e:
        st.error(f"An error occurred while loading the CSV file from S3: {e}")
        st.write("Error details:", str(e))
    return None

# Function to load policy documents from S3
def load_policy_documents(conn):
    try:
        st.write("Attempting to read policy documents from S3...")
        documents = {
            "franchise": conn.read("fbc-hackathon-test/policy_doc_1.txt", input_format="text", ttl=600),
            "employee_conduct": conn.read("fbc-hackathon-test/policy_doc_2.txt", input_format="text", ttl=600)
        }
        st.write("Successfully loaded policy documents.")
        return documents
    except Exception as e:
        st.error(f"An error occurred while loading the policy documents from S3: {e}")
        st.write("Error details:", str(e))
    return None

# Function to determine whether to use policy documents or CSV data
def determine_context_and_response(prompt, policy_documents, csv_df):
    try:
        st.write("Determining the context based on the user's prompt...")
        prompt_lower = prompt.lower()

        if "csv" in prompt_lower:  # Example condition for CSV-related queries
            if csv_df is not None:
                context = f"Here is the data from the CSV file:\n{csv_df.to_string(index=False)}"
            else:
                context = "CSV data is not available."
        else:
            # If the question is about policy, search in the policy documents
            context = ""
            if "franchise" in prompt_lower:
                context = policy_documents["franchise"]
            elif "employee" in prompt_lower or "conduct" in prompt_lower:
                context = policy_documents["employee_conduct"]

            # If context is empty, return "Answer not found"
            if not context.strip():
                context = "Answer not found."

        st.write("Context determined successfully.")
        return context
    except Exception as e:
        st.error(f"An error occurred while determining the context: {e}")
        st.write("Error details:", str(e))
        return "An error occurred while determining the context."

# Establish connection to S3
try:
    st.write("Establishing connection to S3...")
    conn = st.connection('s3', type=FilesConnection)
    st.write("Successfully connected to S3.")
except Exception as e:
    st.error(f"An error occurred while establishing connection to S3: {e}")
    st.write("Error details:", str(e))

# Load the policy documents and CSV data from S3
policy_documents = load_policy_documents(conn)
csv_df = load_csv_data_from_s3(conn, "fbc-hackathon-test/sample_data.csv")  # Replace with your CSV file key

# Show title and description.
st.title("FBC Chatbot - Here to Help")

# Display sample questions for users to try
st.markdown("""
    <p style='font-style: italic;'>
        Here are some example questions you can ask me about the data:<br>
        - "What are the top-performing franchises?"<br>
        - "Which franchises have the highest operating costs?"<br>
        - "Can you identify any sales trends?"
    </p>
""", unsafe_allow_html=True)

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

    # Handle the user prompt and generate a response
    if prompt := st.chat_input("Ask a question:"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Determine context based on the user's prompt
        context = determine_context_and_response(prompt, policy_documents, csv_df)

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
