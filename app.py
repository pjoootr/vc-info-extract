import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
import pandas as pd
from openai import OpenAI

# Load OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Streamlit UI setup
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste one or more VC firm websites (comma-separated):")

url_input = st.text_area("🔗 VC Website URLs", "https://example-vc.com, https://example2.com")

# Helper function to check if a link is internal
def is_internal_link(base_url, link):
    return urlparse(link).netloc in ["", urlparse(base_url).netloc]

# Find relevant internal pages
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

# Scrape pages and extract emails/text
def extract_text_and_email(urls):
    combined_text = ""
    found_emails = set()

    for link in urls:
        try:
            res = requests.get(link, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text(separator=' ', strip=True)
            combined_text += page_text[:3000] + "\n\n"

            # Emails from text
            emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", page_text))
            found_emails.update(emails)

            # Emails from mailto links
            for mail_link in soup.select('a[href^=mailto]'):
                email = mail_link.get("href").replace("mailto:", "").strip()
                if "@" in email:
                    email = email.split("?")[0]
                    found_emails.add(email)

        except Exception:
            continue

    return combined_text[:8000], list(found_emails)

# Extract individual bullet from GPT output
def extract_field(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "Not found"

# Main action
if st.button("Extract Info"):
    urls = [u.strip() for u in url_input.split(",") if u.strip()]
    results = []

    for url in urls:
        try:
            st.write(f"🔍 Processing: {url}")

            keywords = ["about", "investment", "focus", "team", "criteria", "approach", "contact"]
            pages_to_scrape = [url] + get_relevant_internal_pages(url, keywords)
            scraped_text, emails = extract_text_and_email(pages_to_scrape)

            prompt = f"""
            You are an assistant that extracts startup-relevant VC info from website text.

            From the following text, extract:
            - A short 2–3 sentence description **About the Fund**
            - Typical **Ticket Size**
            - **Stage** (e.g., Seed, Series A)
            - **Geography** (e.g., US, Europe, Global)
            - Preferred **Sectors** (e.g., SaaS, Fintech)

            Format the answer in clean bullet points using markdown:

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

            about_fund = extract_field(r"\*\*About the Fund\*\*:\s*(.*)", gpt_output)
            ticket_size = extract_field(r"\*\*Ticket Size\*\*:\s*(.*)", gpt_output)
            stage = extract_field(r"\*\*Stage\*\*:\s*(.*)", gpt_output)
            geography = extract_field(r"\*\*Geography\*\*:\s*(.*)", gpt_output)
            sectors = extract_field(r"\*\*Sectors\*\*:\s*(.*)", gpt_output)
            email = emails[0] if emails else "Not found"

            # Add to results list
            results.append({
                "Website": url,
                "About the Fund": about_fund,
                "Ticket Size": ticket_size,
                "Stage": stage,
                "Geography": geography,
                "Sectors": sectors,
                "Contact Email": email,
            })

            # Show each block
            st.markdown(f"### ✅ Info for {url}")
            st.markdown(gpt_output + f"\n- 📧 **Contact Email**: {email}")

        except Exception as e:
            st.error(f"❌ Error with {url}: {e}")

    # Show and allow CSV download
    if results:
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Combined CSV", csv, "vc_info_all.csv", "text/csv")

