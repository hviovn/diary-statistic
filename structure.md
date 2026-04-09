# Structure of the heatmap generating parser program

This project creates a heatmap of all the days since 1975, organized by years. For each day it indicates events, projects, submissions or activities that are documented on the internet. Hovering over the day shows the list of things for this day, if any. Once you click on the day the tooltip becomes static and the items can be selected. This will lead to the original source on a webpage, Github, Wordpress or project source.

## Sources

The file `sources.json` contains the sources

## Stage 1

create sources

## Stage 2

Parse sources

## Stage 3

parse content

## Stage 4

Generate heatmaps

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
