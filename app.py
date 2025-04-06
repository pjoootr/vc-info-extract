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
st.write("Paste one or more VC websites (comma-separated):")

# Text area for multi-URL input
urls_input = st.text_area("🔗 VC Website URLs", "https://www.credoventures.com/, https://www.beringea.co.uk/")

# Helper: Check if link is internal
def is_internal_link(base_url, link):
    return urlparse(link).netloc in ["", urlparse(base_url).netloc]

# Helper: Extract fund name from title or og:site_name
def get_fund_name(base_url):
    try:
        res = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        og_site_name = soup.find("meta", property="og:site_name")
        if og_site_name and og_site_name.get("content"):
            return og_site_name["content"].strip()

        if soup.title and soup.title.string:
            return soup.title.string.strip().split("|")[0].split("-")[0].strip()
    except:
        pass

    domain = urlparse(base_url).netloc.replace("www.", "")
    return domain.capitalize()

# Helper: Find internal links to scrape
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

# Helper: Extract text and emails from multiple pages
def extract_text_and_email(urls):
    combined_text = ""
    found_emails = set()

    for link in urls:
        try:
            res = requests.get(link, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            page_text = soup.get_text(separator=' ', strip=True)
            combined_text += page_text[:3000] + "\n\n"

            # Extract emails from text
            emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", page_text))
            found_emails.update(email.split("?")[0] for email in emails)

            # Extract emails from mailto
            for mail_link in soup.select('a[href^=mailto]'):
                email = mail_link.get("href").replace("mailto:", "").strip().split("?")[0]
                if "@" in email:
                    found_emails.add(email)

        except Exception:
            continue

    return combined_text[:8000], list(found_emails)

# Extraction trigger
if st.button("🔍 Extract Info"):
    urls = [u.strip() for u in urls_input.split(",") if u.strip()]
    results = []

    for url in urls:
        with st.spinner(f"Processing {url}..."):
            try:
                fund_name = get_fund_name(url)
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
                contact_email = emails[0] if emails else "Not found"

                st.markdown(f"---\n### ✅ Info for **{fund_name}**")
                st.markdown(gpt_output)
                st.markdown(f"- 📧 **Contact Email**: {contact_email}")

                # Save for CSV
                results.append({
                    "Fund Name": fund_name,
                    "Website": url,
                    "Extracted Info": gpt_output,
                    "Contact Email": contact_email,
                })

            except Exception as e:
                st.error(f"❌ Error for {url}: {e}")

    if results:
        df = pd.DataFrame(results)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "vc_info.csv", "text/csv")
