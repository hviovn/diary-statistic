import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
LINKS_DIR = os.path.join(DATA_DIR, 'step1_links')
CONTENT_DIR = os.path.join(DATA_DIR, 'step2_content')
ANALYSIS_DIR = os.path.join(DATA_DIR, 'step3_analysis')

def count_words(text):
    if not text: return 0
    return len(re.findall(r'\w+', text))

def count_sentences(text):
    if not text: return 0
    return len(re.split(r'[.!?]+', text))

def main():
    if not os.path.exists(CONTENT_DIR):
        print("Content extraction (Step 2) not found.")
        return

    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    for filename in os.listdir(LINKS_DIR):
        if not filename.endswith('.json'): continue

        with open(os.path.join(LINKS_DIR, filename), 'r') as f:
            link_data = json.load(f)

        sid = link_data['source_id']
        stype = link_data['type']
        print(f"\nAnalyzing {sid}...")

        pages_analysis = []
        url_to_meta = {p['url']: p for p in link_data['pages']}

        if stype == 'github':
            github_path = os.path.join(CONTENT_DIR, f"{sid}.json")
            if os.path.exists(github_path):
                with open(github_path, 'r') as f:
                    entries = json.load(f)
                for entry in entries:
                    text = entry.get('text', '')
                    meta = url_to_meta.get(entry['url'], {})
                    pages_analysis.append({
                        'url': entry['url'],
                        'date': meta.get('date'),
                        'title': meta.get('title'),
                        'word_count': count_words(text),
                        'sentence_count': count_sentences(text),
                        'char_count': len(text),
                        'image_count': len(entry.get('images', []))
                    })
        else:
            source_content_dir = os.path.join(CONTENT_DIR, sid)
            if os.path.exists(source_content_dir):
                for page_file in os.listdir(source_content_dir):
                    with open(os.path.join(source_content_dir, page_file), 'r') as f:
                        entry = json.load(f)
                    text = entry.get('text', '')
                    meta = url_to_meta.get(entry['url'], {})
                    pages_analysis.append({
                        'url': entry['url'],
                        'date': meta.get('date'),
                        'title': meta.get('title'),
                        'word_count': count_words(text),
                        'sentence_count': count_sentences(text),
                        'char_count': len(text),
                        'image_count': len(entry.get('images', []))
                    })

        totals = {
            'words': sum(p['word_count'] for p in pages_analysis),
            'sentences': sum(p['sentence_count'] for p in pages_analysis),
            'chars': sum(p['char_count'] for p in pages_analysis),
            'images': sum(p['image_count'] for p in pages_analysis),
            'pages': len(pages_analysis)
        }

        output = {
            "source_id": sid,
            "pages": pages_analysis,
            "totals": totals
        }

        with open(os.path.join(ANALYSIS_DIR, f"{sid}.json"), 'w') as f:
            json.dump(output, f, indent=2)
        print(f"  Analysis complete for {sid}")

if __name__ == "__main__":
    main()
