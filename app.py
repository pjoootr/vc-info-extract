import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
import os

# Get your OpenAI key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste a VC firm website and get their investment details:")

url = st.text_input("🔗 VC Website URL", "https://example-vc.com")

if st.button("Extract Info"):
    try:
        # Step 1: Get and clean website content
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=' ', strip=True)

        # Step 2: Ask GPT to extract info
        prompt = f"""
        From the following website text, extract:
        - Ticket size (e.g., $100K–$1M)
        - Investment stage (e.g., Seed, Series A)
        - Geography (e.g., US, Europe, Global)
        - Sectors (e.g., Fintech, SaaS)

        Website Text:
        {text[:5000]}
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.choices[0].message["content"]
        st.success("📋 Extracted Info:")
        st.text_area("Output", value=answer.strip(), height=200)

    except Exception as e:
        st.error(f"❌ Error: {e}")
