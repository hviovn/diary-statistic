import csv
import os
import re
import sys

# Increase the CSV field size limit for large content
csv.field_size_limit(sys.maxsize)

def count_words(text):
    if not text:
        return 0
    words = re.findall(r'\w+', text)
    return len(words)

def process_statistics(source_type):
    os.makedirs('data', exist_ok=True)
    sources_file = os.path.join('data', f"sources_{source_type}.csv")
    content_file = os.path.join('data', f"content_{source_type}.csv")
    output_file = os.path.join('data', f"statistics_{source_type}.csv")

    if not os.path.exists(sources_file) or not os.path.exists(content_file):
        print(f"Required files for {source_type} not found.")
        return

    print(f"Calculating statistics for {source_type}...")

    # Load titles from sources_file
    titles = {}
    with open(sources_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            titles[row['Link']] = row['Title']

    results = []
    with open(content_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = row['Link']
            date = row['Date']
            text = row['Cleaned Text']

            word_count = count_words(text)
            char_count = len(text) if text else 0
            title = titles.get(link, "Unknown Title")

            results.append({
                'Link': link,
                'Date': date,
                'Title': title,
                'Word Count': word_count,
                'Character Count': char_count
            })

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Link', 'Date', 'Title', 'Word Count', 'Character Count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Saved to {output_file}")

def main():
    sources = ['wordpress', 'quartz', 'legacy_html', 'github']
    for source in sources:
        process_statistics(source)

if __name__ == "__main__":
    main()
