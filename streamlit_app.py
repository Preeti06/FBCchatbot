import streamlit as st
import pandas as pd
from openai import OpenAI
from st_files_connection import FilesConnection
from io import BytesIO

# Function to load the Excel data from S3 into a Pandas DataFrame
def load_excel_data_from_s3(conn):
    try:
        st.write("Attempting to read Excel file from S3...")
        # Read the file content from S3 (this is binary data)
        file_content = conn.read("fbc-hackathon-test/Test_sheet.xlsx")
        st.write("Successfully read the file content from S3.")

        # Convert the binary content into a BytesIO object
        file_bytes = BytesIO(file_content)

        # Load the Excel file into a Pandas DataFrame
        df = pd.read_excel(file_bytes, engine='openpyxl')
        st.write("Successfully loaded Excel data into DataFrame.")
        return df
    except Exception as e:
        st.error(f"An error occurred while loading the Excel file from S3: {e}")
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

# Function to determine whether to use policy documents or Excel data
def determine_context_and_response(prompt, policy_documents, df):
    try:
        st.write("Determining the context based on the user's prompt...")
        prompt_lower = prompt.lower()

        if "soc" in prompt_lower or "growth" in prompt_lower:
            # If the question is about SOCs Growth, use the Excel data
            if df is not None:
                context = f"The following franchises have issues with their SOCs Growth:\n{socs_growth_issues}"
            else:
                context = "SOCs Growth data is not available."
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

# Load the policy documents and Excel data from S3
policy_documents = load_policy_documents(conn)
df = load_excel_data_from_s3(conn)

if df is not None:
    # Ensure the "SOCs Growth" column is numeric
    try:
        st.write("Ensuring the 'SOCs Growth' column is numeric...")
        df["SOCs Growth"] = pd.to_numeric(df["SOCs Growth"], errors='coerce')
        
        # Filter the data to find franchises with low or negative SOCs Growth
        franchises_needing_help = df[df["SOCs Growth"] <= 0]
        
        # Prepare the context to be passed to the chatbot
        socs_growth_issues = franchises_needing_help.to_string(index=False)
        st.write("SOCs Growth data processed successfully.")
    except KeyError as e:
        st.error("The 'SOCs Growth' column is not found in the data.")
        st.write("Error details:", str(e))
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.write("Error details:", str(e))

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
        context = determine_context_and_response(prompt, policy_documents, df)

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
