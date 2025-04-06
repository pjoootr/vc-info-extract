import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
from openai import OpenAI

# Load OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Streamlit UI
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste a VC firm website and get their investment details:")

url = st.text_input("🔗 VC Website URL", "https://example-vc.com")

def is_internal_link(base_url, link):
    return urlparse(link).netloc in ["", urlparse(base_url).netloc]

def get_relevant_internal_pages(base_url, keywords, max_pages=3):
    try:
        response = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        all_links = soup.find_all("a", href=True)

        internal_links = []
        for a_tag in all_links:
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            if is_internal_link(base_url, full_url):
                for keyword in keywords:
                    if keyword in href.lower():
                        internal_links.append(full_url)
                        break

        # Deduplicate and limit
        seen = set()
        filtered = []
        for link in internal_links:
            if link not in seen:
                filtered.append(link)
                seen.add(link)
            if len(filtered) >= max_pages:
                break

        return filtered
    except:
        return []

def extract_text_and_email(urls):
    combined_text = ""
    found_emails = set()

    for link in urls:
        try:
            res = requests.get(link, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text(separator=' ', strip=True)
            combined_text += page_text[:3000] + "\n\n"

            # Extract email addresses
            emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", page_text))
            found_emails.update(emails)

            # Also look for mailto links
            for mail_link in soup.select('a[href^=mailto]'):
                email = mail_link.get("href").replace("mailto:", "").strip()
                if "@" in email:
                    found_emails.add(email)

        except Exception:
            continue

    return combined_text[:8000], list(found_emails)

if st.button("Extract Info"):
    try:
        keywords = ["about", "investment", "focus", "team", "criteria", "approach", "contact"]
        pages_to_scrape = [url] + get_relevant_internal_pages(url, keywords)
        scraped_text, emails = extract_text_and_email(pages_to_scrape)

        prompt = f"""
        You are an assistant that extracts startup-relevant VC info from website text.

        From the following text, extract:
        - A short 2–3 sentence description **about the fund**
        - Typical **ticket size**
        - **Investment stage** (e.g., Seed, Series A)
        - **Geography** (e.g., US, Europe, Global)
        - Preferred **sectors** (e.g., SaaS, Fintech)

        Format the answer in clean bullet points.

        VC Website Text:
        {scraped_text}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500,
        )

        gpt_output = response.choices[0].message.content.strip()

        # Add extracted email if found
        if emails:
            email_section = f"\n- 📧 **Contact Email**: {emails[0]}"
        else:
            email_section = "\n- 📧 **Contact Email**: Not found"

        st.success("📋 Extracted VC Info:")
        st.text_area("Output", value=gpt_output + email_section, height=350)

    except Exception as e:
        st.error(f"❌ Error: {e}")
