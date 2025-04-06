import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
import os

# Set your OpenAI API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# Set up the Streamlit page
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste a VC firm website and get their investment details:")

# Input field for VC firm website
url = st.text_input("🔗 VC Website URL", "https://example-vc.com")

# Button to extract info
if st.button("Extract Info"):
    try:
        # Fetch and parse website content
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=' ', strip=True)

        # Limit input text to avoid token overload
        clean_text = text[:5000]

        # Construct prompt for LLM
        prompt = f"""
        From the following VC website text, extract the following info in clear bullet points:
        - Ticket size (e.g., $100K–$1M)
        - Investment stage (e.g., Seed, Series A)
        - Geography (e.g., US, Europe, Global)
        - Sectors (e.g., Fintech, SaaS)

        Website Content:
        {clean_text}
        """

        # Send request to OpenAI chat API
        chat_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.2,
        )

        answer = chat_response.choices[0].message.content.strip()

        # Display result
        st.success("📋 Extracted Info:")
        st.text_area("Output", value=answer, height=250)

    except Exception as e:
        st.error(f"❌ Error: {e}")
