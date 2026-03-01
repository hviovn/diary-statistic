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

def process_statistics(source_type, data_dir):
    os.makedirs(data_dir, exist_ok=True)
    sources_file = os.path.join(data_dir, f"sources_{source_type}.csv")
    content_file = os.path.join(data_dir, f"content_{source_type}.csv")
    output_file = os.path.join(data_dir, f"statistics_{source_type}.csv")

    if not os.path.exists(sources_file) or not os.path.exists(content_file):
        print(f"Required files for {source_type} not found.")
        return

    print(f"Calculating statistics for {source_type}...")

    # Load word/char counts from content file
    counts = {}
    with open(content_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row['Content']
            counts[row['Link']] = {
                'word_count': count_words(text),
                'char_count': len(text) if text else 0
            }

    results = []
    with open(sources_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = row['Link']
            stats = counts.get(link, {'word_count': 0, 'char_count': 0})
            results.append({
                'Link': link,
                'Date': row['Date'],
                'Title': row['Title'],
                'Word Count': stats['word_count'],
                'Character Count': stats['char_count']
            })

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Link', 'Date', 'Title', 'Word Count', 'Character Count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Saved to {output_file}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    sources = ['wordpress', 'quartz', 'legacy_html', 'github']
    for source in sources:
        process_statistics(source, data_dir)

if __name__ == "__main__":
    main()
