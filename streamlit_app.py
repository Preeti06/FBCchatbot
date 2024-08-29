import streamlit as st
import pandas as pd
from io import BytesIO
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
def load_csv_data_from_s3(conn, file_key):
    try:
        # Read the CSV content as a string
        file_content = conn.read(file_key)
        
        # Load the string content into a Pandas DataFrame
        df = pd.read_csv(BytesIO(file_content.encode()))

        # If loading Operations_ScoreCard, filter to key columns
        if file_key == "fbc-hackathon-test/Operations_ScoreCard.csv":
            df = df[KEY_COLUMNS]
        
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

# Function to determine whether to use text documents or CSV data
def determine_context_and_response(prompt, csv_df, text_content):
    try:
        st.write("Determining the context based on the user's prompt...")
        prompt_lower = prompt.lower()

        if any(keyword in prompt_lower for keyword in ["csv", "data", "franchise", "trends", "performance", "sales"]):
            if csv_df is not None:
                context = f"Here is the data from the CSV file:\n{csv_df.to_string(index=False)}"
            else:
                context = "CSV data is not available."
        elif any(keyword in prompt_lower for keyword in ["text", "document", "weekly metrics", "yext"]):
            context = text_content if text_content else "Document content is not available."

        else:
            context = "The query does not match any known categories. Please specify if you're asking about CSV data or documents."

        st.write("Context determined successfully.")
        return context
    except Exception as e:
        st.error(f"An error occurred while determining the context: {e}")
        st.write("Error details:", str(e))
        return "An error occurred while determining the context."

# Establish connection to S3
try:
    conn = st.connection('s3', type=FilesConnection)
except Exception as e:
    st.error(f"An error occurred while establishing connection to S3: {e}")
    st.write("Error details:", str(e))

# Option for user to select which CSV file to load
csv_file_options = {
    "Operations ScoreCard": "fbc-hackathon-test/Operations_ScoreCard.csv",
    "Home Care Consultant KPIs": "fbc-hackathon-test/Home Care Consultant Development Plan 1.0 - KPIs.csv",
    "Balance Sheet Example": "fbc-hackathon-test/Balance Sheet Example - Sheet1.csv",
    "Basic Income Statement Example": "fbc-hackathon-test/Basic Income Statement Example - Sheet1.csv",
    "Network Median": "fbc-hackathon-test/Network Median.csv"
}

# Option for user to select which plain text file to load
text_file_options = {
    "Weekly Metrics Meeting": "fbc-hackathon-test/Weekly Metrics Meeting.txt",
    "Yext Document": "fbc-hackathon-test/Yext.txt",
    "HCC Job template": "fbc-hackathon-test/HCC Job template.txt"
}

# User selects CSV file
csv_file_selection = st.selectbox("Select a CSV file to load:", list(csv_file_options.keys()))
csv_df = load_csv_data_from_s3(conn, csv_file_options[csv_file_selection])

# User selects text file
text_file_selection = st.selectbox("Select a text file to load:", list(text_file_options.keys()))
text_content = load_text_data_from_s3(conn, text_file_options[text_file_selection])

# Show title and description.
st.title("FBC Chatbot - Here to Help")

# Display sample questions for users to try
st.markdown("""
    <p style='font-style: italic;'>
        Here are some example questions you can ask me about the data or documents:<br>
        - "What are the top-performing franchises?"<br>
        - "Which franchises have the highest operating costs?"<br>
        - "Can you identify any sales trends?"<br>
        - "What does the Yext document say?"<br>
        - "Give me details from the Weekly Metrics Meeting."
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
        context = determine_context_and_response(prompt, csv_df, text_content)

        # Combine the context with the user's prompt for the OpenAI API.
        system_message = (
            "You are a helpful assistant with access to the following documents and business data. "
            "Use the content to answer questions accurately."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{context}\n\n{prompt}"},
        ]

        # Generate a response using the OpenAI API.
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
