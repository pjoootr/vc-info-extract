import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
from openai import OpenAI

# Load the API key from Streamlit secrets
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Streamlit UI
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste a VC firm website and get their investment details:")

url = st.text_input("🔗 VC Website URL", "https://example-vc.com")

if st.button("Extract Info"):
    try:
        # Scrape the website
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=' ', strip=True)

        # Trim the input for token limits
        clean_text = text[:5000]

        # Create the prompt
        prompt = f"""
        From the following VC website text, extract the following info in clear bullet points:
        - Ticket size (e.g., $100K–$1M)
        - Investment stage (e.g., Seed, Series A)
        - Geography (e.g., US, Europe, Global)
        - Sectors (e.g., Fintech, SaaS)

        Website Content:
        {clean_text}
        """

        # Call OpenAI chat API (new format)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
        )

        answer = response.choices[0].message.content.strip()
        st.success("📋 Extracted Info:")
        st.text_area("Output", value=answer, height=250)

    except Exception as e:
        st.error(f"❌ Error: {e}")
