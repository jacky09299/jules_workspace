import requests
import time
import os
import sys

# To translate titles
try:
    from deep_translator import GoogleTranslator
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator"])
    from deep_translator import GoogleTranslator

TARGET_TOTAL = 30000

CATEGORIES = {
    "哲學與思想": ["philosophy", "religion", "ethics", "logic", "aesthetics"],
    "科學與數學": ["mathematics", "physics", "chemistry", "biology", "astronomy", "geology", "medicine", "botany", "zoology", "oceanography", "meteorology", "ecology", "astrophysics"],
    "文學與藝術": ["literature", "poetry", "art", "music", "architecture", "photography", "cinema", "theater", "mythology", "folklore"],
    "歷史與社會": ["history", "geography", "sociology", "psychology", "economics", "political_science", "law", "education", "anthropology", "archaeology"],
    "電腦科學與技術": ["engineering", "computer_science", "agriculture", "technology", "bioinformatics", "robotics", "nanotechnology"]
}

def load_existing_urls():
    existing_urls = set()
    total_count = 0
    for category in CATEGORIES.keys():
        filepath = os.path.join(category, "書單.md")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if " - https://" in line:
                        url = line.split(" - ")[-1].strip()
                        existing_urls.add(url)
                        total_count += 1
    return existing_urls, total_count

def ensure_directories():
    for category in CATEGORIES.keys():
        os.makedirs(category, exist_ok=True)

def fetch_and_translate():
    ensure_directories()
    existing_urls, existing_count = load_existing_urls()
    books_added = 0

    if existing_count >= TARGET_TOTAL:
        print("Target already reached.")
        return

    print(f"Starting at count: {existing_count}, need {TARGET_TOTAL - existing_count} more books.")

    global_book_index = existing_count + 1

    translator_instance = GoogleTranslator(source='auto', target='zh-TW')

    for category, subjects in CATEGORIES.items():
        filepath = os.path.join(category, "書單.md")

        for subject in subjects:
            print(f"Fetching subject: {subject} for category: {category}...")
            offset = 0
            limit = 50

            # Fetch up to 1000 items per subject
            while offset < 1000:
                if (existing_count + books_added) >= TARGET_TOTAL:
                    print(f"Target of {TARGET_TOTAL} reached!")
                    return

                try:
                    url = f"https://openlibrary.org/subjects/{subject}.json?limit={limit}&offset={offset}"
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        print(f"Error {response.status_code} fetching {subject}. Retrying after delay...")
                        time.sleep(5)
                        continue

                    data = response.json()
                    works = data.get('works', [])

                    if not works:
                        print(f"No more works found for {subject}.")
                        break

                    with open(filepath, "a", encoding="utf-8") as f:
                        for work in works:
                            if (existing_count + books_added) >= TARGET_TOTAL:
                                print(f"Target of {TARGET_TOTAL} reached!")
                                return

                            key = work.get('key', '')
                            link = f"https://openlibrary.org{key}" if key else "Link Unavailable"

                            # Skip if we already have this book
                            if link in existing_urls:
                                continue

                            eng_title = work.get('title', 'Unknown Title')
                            authors = [a.get('name') for a in work.get('authors', [])]
                            author_str = ", ".join(authors) if authors else "Unknown Author"

                            # Perform translation
                            try:
                                zh_title = translator_instance.translate(eng_title)
                                if not zh_title or "Error 500" in zh_title or "<html" in zh_title.lower():
                                    zh_title = "翻譯失敗"
                            except Exception as e:
                                print(f"Translation failed: {e}. Taking a 60s break to reset limits...")
                                time.sleep(60)
                                zh_title = "翻譯失敗"

                            line = f"{global_book_index}. {zh_title} ({eng_title}) by {author_str} - {link}\n"
                            f.write(line)

                            existing_urls.add(link)
                            global_book_index += 1
                            books_added += 1

                            if books_added % 50 == 0:
                                print(f"Progress: Added {existing_count + books_added} books so far...")

                            time.sleep(0.5) # Prevent translation rate limit

                    offset += limit

                except Exception as e:
                    print(f"Exception occurred: {e}. Retrying after delay...")
                    time.sleep(10)

if __name__ == "__main__":
    fetch_and_translate()
    print("Done fetching and translating books.")
