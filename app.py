import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
import os

# Set OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Set up the Streamlit page configuration
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste a VC firm website and get their investment details:")

# Input for VC website URL
url = st.text_input("🔗 VC Website URL", "https://example-vc.com")

# Button to trigger the extraction process
if st.button("Extract Info"):
    try:
        # Step 1: Fetch and clean website content
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=' ', strip=True)

        # Step 2: Construct the prompt to send to OpenAI
        prompt = f"""
        From the following website text, extract:
        - Ticket size (e.g., $100K–$1M)
        - Investment stage (e.g., Seed, Series A)
        - Geography (e.g., US, Europe, Global)
        - Sectors (e.g., Fintech, SaaS)

        Website Text:
        {text[:5000]}  # Only send the first 5000 characters to avoid exceeding the token limit
        """

        # Step 3: Send request to OpenAI API (updated to use new API)
        response = openai.completions.create(
            model="gpt-3.5-turbo",  # Specify your model
            prompt=prompt,  # Pass the prompt
            max_tokens=1500,  # Limit the number of tokens in the response
            n=1,  # Number of completions to generate
            stop=None,  # Optional: you can specify stop sequences, if needed
        )

        # Step 4: Extract and display the output
        answer = response['choices'][0]['text'].strip()
        st.success("📋 Extracted Info:")
        st.text_area("Output", value=answer, height=200)

    except Exception as e:
        st.error(f"❌ Error: {e}")
