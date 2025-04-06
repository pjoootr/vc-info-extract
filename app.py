import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import os
import csv
from openai import OpenAI
from io import StringIO

# Load OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Streamlit UI setup
st.set_page_config(page_title="VC Info Extractor", layout="centered")
st.title("🔎 VC Info Extractor")
st.write("Paste a VC firm website and get their investment details:")

url = st.text_input("🔗 VC Website URL", "https://example-vc.com")

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

            # Extract emails from mailto links
            for mail_link in soup.select('a[href^=mailto]'):
                email = mail_link.get("href").replace("mailto:", "").strip()
                if "@" in email:
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
        keywords = ["about", "investment", "focus", "team", "criteria", "approach", "contact"]
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

        # Parse the GPT output into individual components
        about_fund = "Not found"
        ticket_size = "Not found"
        stage = "Not found"
        geography = "Not found"
        sectors = "Not found"
        email = "Not found"

        # Split the output by bullet points
        lines = gpt_output.split("\n")
        for line in lines:
            if line.lower().startswith("about the fund"):
                about_fund = line.split(":")[-1].strip()
            elif line.lower().startswith("ticket size"):
                ticket_size = line.split(":")[-1].strip()
            elif line.lower().startswith("stage"):
                stage = line.split(":")[-1].strip()
            elif line.lower().startswith("geography"):
                geography = line.split(":")[-1].strip()
            elif line.lower().startswith("sectors"):
                sectors = line.split(":")[-1].strip()

        # Add extracted email to the output
        if emails:
            email = emails[0]

        # Prepare data for CSV download
        extracted_data = [[url, about_fund, ticket_size, stage, geography, sectors, email]]

        # Provide a download button for the CSV file
        csv_data = convert_to_csv(extracted_data)
        st.download_button(
            label="Download as CSV",
            data=csv_data,
            file_name="vc_info.csv",
            mime="text/csv",
        )

        # Display the formatted output using st.markdown
        st.success("📋 Extracted VC Info:")

        # Render the output with markdown formatting
        st.markdown(f"""
        **About the Fund**: {about_fund}
        **Ticket Size**: {ticket_size}
        **Stage**: {stage}
        **Geography**: {geography}
        **Sectors**: {sectors}
        **Contact Email**: {email}
        """)

        # Optionally show raw text output in a collapsible section
        with st.expander("📄 View raw output"):
            st.text_area("Raw Text", value=gpt_output, height=350)

    except Exception as e:
        st.error(f"❌ Error: {e}")
