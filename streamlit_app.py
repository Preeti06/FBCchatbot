import streamlit as st
import pandas as pd
import re
from io import StringIO
from openai import OpenAI
from st_files_connection import FilesConnection

# Key columns to focus on for Operations_ScoreCard
KEY_COLUMNS = [
    'CurrentYearTotalRevenue', 'LastYearTotalRevenue',
    'CurrentYearTotalBillableHours', 'LastYearTotalBillableHours',
    'RPNLeadsGrowth', 'CPNetGrowth', 'SOCGrowth',
    'HoursGrowth', 'RevenueGrowth', 'WeightedScore',
    'Rank', 'RPNQuartile', 'CPNETQuartile', 'SOCQuartile',
    'HOURSQuartile', 'REVQuartile'
]

# Function to load CSV data from S3 into a Pandas DataFrame
def load_csv_data_from_s3(conn, file_key, filter_columns=None):
    try:
        # Read the CSV content from S3
        file_content = conn.read(file_key)
        
        # Assume the content is a string and read it into a DataFrame
        df = pd.read_csv(StringIO(file_content))
        
        # Filter to specific columns if required
        if filter_columns:
            df = df[filter_columns]
        
        return df
    except Exception as e:
        st.error(f"An error occurred while loading the CSV file from S3: {e}")
        st.write("Error details:", str(e))
    return None

# Function to load plain text documents from S3
def load_text_data_from_s3(conn, file_key):
    try:
        # Read the text content from the file
        text_content = conn.read(file_key)
        return text_content
    except Exception as e:
        st.error(f"An error occurred while loading the text file from S3: {e}")
        st.write("Error details:", str(e))
    return None

# Function to extract the franchise number from the user's prompt
def extract_franchise_number(prompt):
    # Assuming the franchise number follows the word "Franchise" in the query
    match = re.search(r"Franchise\s+(\d+)", prompt, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

# Function to determine which files are needed based on the user's query
def determine_files_needed(prompt):
    prompt_lower = prompt.lower()
    files_needed = []
    
    franchise_number = extract_franchise_number(prompt)
    
    if any(keyword in prompt_lower for keyword in ["revenue", "performance", "sales", "data", "franchise"]):
        files_needed.append(("csv", "fbc-hackathon-test/Operations_ScoreCard.csv", KEY_COLUMNS, franchise_number))
    if any(keyword in prompt_lower for keyword in ["kpi", "consultant", "development"]):
        files_needed.append(("csv", "fbc-hackathon-test/Home Care Consultant Development Plan 1.0 - KPIs.csv", None, franchise_number))
    if any(keyword in prompt_lower for keyword in ["balance", "sheet"]):
        files_needed.append(("csv", "fbc-hackathon-test/Balance Sheet Example - Sheet1.csv", None, franchise_number))
    if any(keyword in prompt_lower for keyword in ["income", "statement"]):
        files_needed.append(("csv", "fbc-hackathon-test/Basic Income Statement Example - Sheet1.csv", None, franchise_number))
    if any(keyword in prompt_lower for keyword in ["median", "network"]):
        files_needed.append(("csv", "fbc-hackathon-test/Network Median.csv", None, franchise_number))
    if any(keyword in prompt_lower for keyword in ["weekly", "metrics", "meeting"]):
        files_needed.append(("text", "fbc-hackathon-test/Weekly Metrics Meeting.txt"))
    if any(keyword in prompt_lower for keyword in ["yext"]):
        files_needed.append(("text", "fbc-hackathon-test/Yext.txt"))
    if any(keyword in prompt_lower for keyword in ["job", "template", "hcc"]):
        files_needed.append(("text", "fbc-hackathon-test/HCC Job template.txt"))

    return files_needed

# Function to load the required data from the relevant files
def load_data(conn, files_needed):
    context = ""

    for file_type, file_key, *optional in files_needed:
        franchise_number = optional[1] if len(optional) > 1 else None
        if file_type == "csv":
            df = load_csv_data_from_s3(conn, file_key, optional[0] if optional else None)
            if df is not None:
                if franchise_number:
                    # Filter the DataFrame for the specific franchise number
                    df = df[df['Number'] == int(franchise_number)]
                context += f"\nData from {file_key}:\n{df.head().to_string(index=False)}\n"
        elif file_type == "text":
            text_content = load_text_data_from_s3(conn, file_key)
            if text_content:
                context += f"\nContent from {file_key}:\n{text_content[:1000]}\n"  # Limiting text content to first 1000 characters

    return context

# Function to generate response from OpenAI based on the context and prompt
def generate_response(client, context, prompt):
    system_message = (
        "You are a helpful assistant with access to the following documents and business data. "
        "Use the content to answer questions accurately."
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"{context}\n\n{prompt}"},
    ]

    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
        )

        # Stream the response to the chat and store it in session state.
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

    except openai.error.OpenAIError as e:
        st.error(f"OpenAI API request failed: {e}")

# Establish connection to S3
try:
    conn = st.connection('s3', type=FilesConnection)
except Exception as e:
    st.error(f"An error occurred while establishing connection to S3: {e}")
    st.write("Error details:", str(e))

# Show title and description.
st.title("FBC Chatbot - Here to Help")

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

        # Determine which files are needed based on the prompt
        files_needed = determine_files_needed(prompt)

        # Load data from the required files
        context = load_data(conn, files_needed)

        # Generate a response from OpenAI based on the context and prompt
        generate_response(client, context, prompt)
