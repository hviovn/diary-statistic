# Structure of the heatmap generating parser program

This project creates a heatmap of all the days since 1975, organized by years. For each day it indicates events, projects, submissions or activities that are documented on the internet from a list of sources with different categories. Hovering over the day shows the list of things for this day, if any. Once you click on the day the tooltip becomes static and the items can be selected. This will lead to the original source on a webpage, Github, Wordpress or project source.

![example image](docs/assets/example_2025.svg)

## Sources

The file [data/sources.yaml](data/sources.yaml) contains the sources with **source_id**, name, url, type and colors. 

### Manage sources

A program [scripts/manage_sources.py](scripts/manage_sources.py) has an interactive menu to edit the sources. It uses textual for the UI. Example code would be:

```py
from textual.app import App
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Container

class MyApp(App):

    def compose(self):
        yield Header()
        yield Container(
            Static("Select a source:", id="title"),
            Button("GitHub Repo", id="github"),
            Button("WordPress Blog", id="wp"),
            Button("Website", id="web"),
            Button("Execute", id="execute"),
        )
        yield Footer()

    def on_button_pressed(self, event):
        self.log(f"Pressed: {event.button.id}")

if __name__ == "__main__":
    MyApp().run()
```

On opening it shows the sources with their names, pages, words and last parsed. The options below are <add new>, <edit> and <parse>.

```yaml
- id: my_blog
  type: wordpress
  url: https://example.com

- id: my_repo
  type: github
  repo: user/project
```

### Folder structure in JSON

```
data/
├── step1_links/
│   └── <source_id>.json
│
├── step2_content/
│   └── <source_id>/
│       ├── page1.json
│       ├── page2.json
│
├── step3_analysis/
│   └── <source_id>.json
```

## Step 1 - Data acquisition, create sources, discover links - Output: Link Discovery

In the first stage, the given sources are parsed for all relevant files. If it is a legacy html page, all internally linked pages will be parsed and put into a `<source_id>.json` file. This file also includes the last time this page was parsed, and if some of the found pages should be ignored.

``` json
{
  "source_id": "my_blog",
  "type": "wordpress",
  "base_url": "https://example.com",
  "last_checked": "2026-04-09T12:00:00Z",
  "pages": [
    {
      "url": "https://example.com/post1",
      "title": "Post 1",
      "last_seen": "2026-04-09T12:00:00Z",
      "changed": false
    }
  ]
}
```

## Step 2 - Content extraction, fetch + parse content - Output: Parsed Content

Now parse all the `step1_links/<source_id>.json` files and remove irrelevant code, just store the raw extracted text with removed html marks. Also include a list of other files found. Example:

``` json
{
  "url": "https://example.com/post1",
  "fetched_at": "2026-04-09T12:05:00Z",
  "last_modified": "Wed, 08 Apr 2026 10:00:00 GMT",
  "etag": "\"abc123\"",
  "hash": "md5-or-sha256-of-content",
  "text": "Full extracted text...",
  "images": [
    {"url": "...", "type": "png"},
    {"url": "...", "type": "svg"}
  ],
  "files": [
    {"url": "...", "type": "pdf"}
  ]
}
```

## Step 3 - Analysis, analyze text - Output: Analysis

We get a breakdown for each page of the sources, and a summary of each source. This could be used to integrate in a website as current state. Example: 

``` json
{
  "source_id": "my_blog",
  "pages": [
    {
      "url": "...",
      "word_count": 523,
      "sentence_count": 34,
      "char_count": 3100,
      "image_count": 5
    }
  ],
  "totals": {
    "words": 10000,
    "images": 120
  }
}
```

## Step 4 - UI (interactive control + inspection) - Pipeline Design (Python)

Generate heatmaps as SVG, put them into the `docs/assets` folder and link them into the `docs/index.html` file. Include JavaScript and all the relevant information for tooltips to provide links to the visualized events.


