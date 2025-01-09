import os
import re
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from notion_client import Client
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Load API key and database ID from .env file
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Initialize Notion client
notion = Client(auth=NOTION_API_KEY)

# Selenium driver setup
driver = webdriver.Chrome()

# Ensure batch folder exists
batch_folder = "batch"
if not os.path.exists(batch_folder):
    os.makedirs(batch_folder)

# Function to create a Notion page
def create_notion_page(data):
    properties = {
        "Company Name": {"title": [{"text": {"content": data.get("company_name", "Untitled")}}]},
        "Position/Task": {"rich_text": [{"text": {"content": data.get("position", "") or ""}}]},
        "Apply Period": {"rich_text": [{"text": {"content": data.get("apply_period", "") or ""}}]},
        "School Name": {"rich_text": [{"text": {"content": data.get("school_name", "") or ""}}]},
        "Department": {"rich_text": [{"text": {"content": data.get("department", "") or ""}}]},
        "GPA (Obtained)": {"number": float(data["gpa_obtained"]) if "gpa_obtained" in data and data["gpa_obtained"] else None},
         "GPA (Base)": {
            "number": float(data["gpa_base"]) if data.get("gpa_base") else 4.5
        },
        "Specification": {"rich_text": [{"text": {"content": data.get("spec_text", "None") or ""}}]},
        "URL": {"url": data.get("URL", None)},
    }

    # Add Q1~Q8 fields
    for i in range(1, 9):
        q_key = f"Q{i}"
        properties[q_key] = {
            "rich_text": [{"text": {"content": data.get(q_key, "") or ""}}]
        }

    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties
        )
        print("Notion 페이지 생성 완료!")
    except Exception as e:
        print("Notion 페이지 생성 실패:", e)

# Function to split text into Q fields
def split_text_into_questions(text, max_length=2000):
    """Split text into chunks of max_length and return as a list."""
    questions = []
    while len(text) > max_length:
        questions.append(text[:max_length].strip())
        text = text[max_length:]
    if text:  # Add remaining text as the last chunk
        questions.append(text.strip())
    return questions

# Function to process content into Q fields
def process_article_content(article_elem):
    """Process article content to populate Q fields."""
    if not article_elem:
        return ["" for _ in range(8)]  # Return 8 empty strings if no content

    full_text = article_elem.get_text(separator="\n", strip=True)

    # Initialize question fields
    q_fields = [""] * 8

    # Check if the text starts with "1."
    if "1." in full_text:
        # Split by numbered sections (e.g., 1., 2., 3.)
        pattern = r"(\d\..*?)(?=\n\d\.|$)"
        matches = re.findall(pattern, full_text, flags=re.DOTALL)

        for idx, match in enumerate(matches[:8]):  # Map to Q1 ~ Q8
            q_fields[idx] = match.strip()
    else:
        # Extract content after "공유\n" if "1." is missing
        split_key = "공유\n"
        if split_key in full_text:
            full_text = full_text.split(split_key, 1)[-1].strip()

        # Process text, identifying sections based on "2.", "3.", etc.
        pattern = r"(\d\..*?)(?=\n\d\.|$)"  # Matches numbered sections (e.g., "2.", "3.")
        matches = re.finditer(pattern, full_text, flags=re.DOTALL)

        start_idx = 0
        current_field = 0
        for match in matches:
            if current_field >= 8:  # Stop if all Q fields are filled
                break

            # Extract the section before the current match
            end_idx = match.start()
            section = full_text[start_idx:end_idx].strip()

            # Assign the section to the current Q field
            q_fields[current_field] = section
            current_field += 1

            # Update start index for the next section
            start_idx = match.start()

        # Process the remaining text after the last match
        if current_field < 8 and start_idx < len(full_text):
            q_fields[current_field] = full_text[start_idx:].strip()

    # Handle fields exceeding 2000 characters
    max_length = 2000
    adjusted_fields = []
    for text in q_fields:
        while len(text) > max_length:
            # Take up to max_length characters and add to the current field
            adjusted_fields.append(text[:max_length].strip())
            text = text[max_length:].strip()
        if text:  # Add remaining text if any
            adjusted_fields.append(text)

    # Ensure adjusted_fields has exactly 8 fields
    while len(adjusted_fields) < 8:
        adjusted_fields.append("")  # Fill with empty strings
    return adjusted_fields[:8]


# Function to save data to JSON and upload to Notion
def save_and_upload(data, batch_number):
    json_filename = os.path.join(batch_folder, f"batch_{batch_number}.json")
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {json_filename}")

    for item in data:
        create_notion_page(item)

# Main loop for scraping and Notion integration
batch_size = 2
batch_number = 1
batch_data = []

gpa_pattern = r"학점\s*(\d+(?:\.\d+)?)(?:\s*/\s*(\d+(?:\.\d+)?))?"

start_page = 1
max_page = 683
for page in range(start_page, max_page + 1):
    print(f"Processing page {page}/{max_page}...")
    site = f"https://linkareer.com/cover-letter/33999?page={page}&sort=PASSED_AT&tab=all"
    
    driver.get(site)
    time.sleep(3)

    href_list = []

    for i in range(1, 21):
        xpath = f'//*[@id="__next"]/div[1]/div[4]/div/div[2]/div[2]/div/div[2]/div[{i}]/a'
        try:
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            href_value = element.get_attribute("href")
            href_list.append(href_value)
            print(f"  Found href for item {i}: {href_value}")
        except Exception as e:
            print(f"  {i}번째 href를 찾을 수 없습니다: {e}")

    for idx, url in enumerate(href_list, start=1):
        print(f"  Processing item {idx}/{len(href_list)} from page {page}...")
        driver.get(url)
        time.sleep(2)

        content_dict = {"URL": url}

        try:
            h1_element = driver.find_element(By.XPATH, '//h1[contains(@class, "MuiTypography-root")]')
            title_text = h1_element.text.strip()
            splitted = title_text.split(" / ")
            content_dict["company_name"] = splitted[0] if len(splitted) > 0 else ""
            content_dict["position"] = splitted[1] if len(splitted) > 1 else ""
            content_dict["apply_period"] = splitted[2] if len(splitted) > 2 else ""
        except Exception as e:
            print(f"  [Error] Title 출수 실패: {e}")

        
        try:
            h3_element = driver.find_element(By.XPATH, '//h3[contains(@class, "MuiTypography-root")]')
            spec_text = h3_element.text.strip()
            split_text = spec_text.split(" / ")

            content_dict["school_name"] = split_text[0].strip() if len(split_text) > 0 else ""
            content_dict["department"] = split_text[1].strip() if len(split_text) > 1 else ""

            match = re.search(gpa_pattern, spec_text)
            if match:
                content_dict["gpa_obtained"] = match.group(1)
                content_dict["gpa_base"] = match.group(2) if match.group(2) else 4.5
                spec_text = re.sub(gpa_pattern, "", spec_text)

            if len(split_text) > 0:
                spec_text = spec_text.replace(split_text[0], "").strip()
            if len(split_text) > 1:
                spec_text = spec_text.replace(split_text[1], "").strip()

            # Remove leading `/` in the first 7 characters and extra spaces
            spec_text = re.sub(r"^(\s*/\s*)+", "", spec_text)
            spec_text = spec_text.strip()

            content_dict["spec_text"] = spec_text
        except Exception as e:
            print(f"  [Error] Spec Text 추출 실패: {e}")

        try:
            html_source = driver.page_source
            soup = BeautifulSoup(html_source, "html.parser")
            article_elem = soup.find("article", {"id": "coverLetterContent"})
            q_fields = process_article_content(article_elem)
            for i in range(1, 9):
                content_dict[f"Q{i}"] = q_fields[i - 1]
        except Exception as e:
            print(f"  [Error] CV 출수 실패: {e}")
            for i in range(1, 9):
                content_dict[f"Q{i}"] = ""

        batch_data.append(content_dict)

    if page % batch_size == 0 or page == max_page:
        print(f"Uploading batch {batch_number} to Notion...")
        save_and_upload(batch_data, batch_number)
        batch_data = []
        batch_number += 1

driver.quit()
