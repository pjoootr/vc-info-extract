import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
import csv
import pandas as pd
from io import StringIO
from openai import OpenAI

# Load OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Streamlit UI setup
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste VC firm website URLs below (comma-separated) to get investment details:")

urls_input = st.text_area("🔗 VC Website URLs (comma-separated)", "https://example-vc.com")

# Helper function to check if a link is internal
def is_internal_link(base_url, link):
    return urlparse(link).netloc in ["", urlparse(base_url).netloc]

# Function to find internal links with relevant keywords
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

        # Deduplicate and limit the number of pages to scrape
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

# Function to extract text and emails from multiple pages
def extract_text_and_email(urls):
    combined_text = ""
    found_emails = set()

    for link in urls:
        try:
            res = requests.get(link, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text(separator=' ', strip=True)
            combined_text += page_text[:3000] + "\n\n"

            # Extract email addresses from the text
            emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", page_text))
            found_emails.update(emails)

            # Extract emails from mailto links and strip any query parameters after the email address
            for mail_link in soup.select('a[href^=mailto]'):
                email = mail_link.get("href").replace("mailto:", "").strip()
                if "@" in email:
                    # Strip out any query parameters after the email address (like ?subject=Hello)
                    email = email.split('?')[0]
                    found_emails.add(email)

        except Exception:
            continue

    return combined_text[:8000], list(found_emails)

# Function to convert extracted data to CSV format
def convert_to_csv(data):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["URL", "About the Fund", "Ticket Size", "Stage", "Geography", "Sectors", "Contact Email"])
    
    for row in data:
        writer.writerow(row)
    
    return output.getvalue()

if st.button("Extract Info"):
    try:
        urls = [url.strip() for url in urls_input.split(",")]
        keywords = ["about", "investment", "focus", "team", "criteria", "approach", "contact"]

        extracted_data = []

        for url in urls:
            pages_to_scrape = [url] + get_relevant_internal_pages(url, keywords)
            scraped_text, emails = extract_text_and_email(pages_to_scrape)

            # Prompt for GPT to process the extracted text
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

            # Send prompt to GPT and get a response
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500,
            )

            gpt_output = response.choices[0].message.content.strip()

            # Add extracted email to the output
            if emails:
                email_section = f"\n- 📧 **Contact Email**: {emails[0]}"
            else:
                email_section = "\n- 📧 **Contact Email**: Not found"

            # Prepare the data to be included in the CSV
            extracted_data.append([url, gpt_output, "", "", "", email_section])

        # Display the formatted output using st.markdown for each URL
        st.success("📋 Extracted VC Info:")

        for data in extracted_data:
            st.markdown(f"### {data[0]}")
            st.markdown(data[1] + data[6])

        # Allow the user to download the CSV file
        csv_data = convert_to_csv(extracted_data)
        st.download_button(
            label="Download as CSV",
            data=csv_data,
            file_name="vc_info.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"❌ Error: {e}")
