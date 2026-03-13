import requests
import json
import time

TARGET_TOTAL = 30000
STARTING_COUNT = 70
BOOKS_NEEDED = TARGET_TOTAL - STARTING_COUNT
OUTPUT_FILE = "civilization_library.md"

# A broad list of topics to ensure we cover "all of human civilization"
SUBJECTS = [
    "mathematics", "physics", "chemistry", "biology", "astronomy", "geology",
    "medicine", "engineering", "computer_science", "agriculture",
    "philosophy", "religion", "history", "geography", "sociology",
    "psychology", "economics", "political_science", "law",
    "literature", "poetry", "art", "music", "architecture", "photography",
    "cinema", "theater", "sports", "cooking", "travel", "biography",
    "language", "linguistics", "education", "mythology", "folklore",
    "technology", "ethics", "logic", "aesthetics", "botany", "zoology",
    "oceanography", "meteorology", "ecology", "anthropology", "archaeology"
]

def fetch_books():
    books_added = 0
    current_number = STARTING_COUNT + 1

    with open(OUTPUT_FILE, "a") as f:
        # Loop through subjects
        for subject in SUBJECTS:
            print(f"Fetching subject: {subject}...")
            # We fetch up to 1000 items per subject to ensure we hit our target (47 subjects * ~600 = ~30000)
            offset = 0
            limit = 100

            # Continue fetching for this subject until we run out of unique results or we hit our global target
            while True:
                if books_added >= BOOKS_NEEDED:
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
                        break # Move to next subject

                    for work in works:
                        if books_added >= BOOKS_NEEDED:
                            return

                        title = work.get('title', 'Unknown Title')
                        authors = [a.get('name') for a in work.get('authors', [])]
                        author_str = ", ".join(authors) if authors else "Unknown Author"
                        key = work.get('key', '')
                        link = f"https://openlibrary.org{key}" if key else "Link Unavailable"

                        f.write(f"{current_number}. {title} by {author_str} - {link}\n")
                        current_number += 1
                        books_added += 1

                        if books_added % 1000 == 0:
                            print(f"Progress: Added {books_added} books so far...")

                    offset += limit
                    time.sleep(0.5) # Be polite to the API

                except Exception as e:
                    print(f"Exception occurred: {e}. Retrying after delay...")
                    time.sleep(5)

if __name__ == "__main__":
    fetch_books()
    print("Done fetching books.")
