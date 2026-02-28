import sys
import urllib.request
import re
import html
import math

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def strip_html(text):
    if not text:
        return ""
    # Remove script and style tags and their content
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove other HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Unescape common entities
    text = html.unescape(text)
    return text

def count_images(html_content):
    if not html_content:
        return 0
    return len(re.findall(r'<img\s+[^>]*src="([^"]+)"', html_content, re.IGNORECASE))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/parse_website_words.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Fetching content from: {url}")

    raw_html = fetch_url(url)
    if raw_html is None:
        sys.exit(1)

    image_count = count_images(raw_html)
    cleaned_text = strip_html(raw_html)

    words = re.findall(r'\w+', cleaned_text)
    word_count = len(words)
    char_count = len(cleaned_text)

    reading_time_minutes = math.ceil(word_count / 200)

    print("\n--- Statistics ---")
    print(f"Words: {word_count}")
    print(f"Characters: {char_count}")
    print(f"Images: {image_count}")
    print(f"Estimated reading time: {reading_time_minutes} min")

if __name__ == "__main__":
    main()
