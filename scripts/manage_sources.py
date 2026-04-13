import yaml
import os
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, DataTable, Input, Label
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
SOURCES_FILE = os.path.join(DATA_DIR, 'sources.yaml')

def load_sources():
    if not os.path.exists(SOURCES_FILE):
        return []
    with open(SOURCES_FILE, 'r') as f:
        return yaml.safe_load(f) or []

def save_sources(sources):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SOURCES_FILE, 'w') as f:
        yaml.dump(sources, f, sort_keys=False)

class SourceEditScreen(ModalScreen):
    def __init__(self, source=None):
        super().__init__()
        self.source = source or {"id": "", "type": "wordpress", "url": "", "name": "", "colors": ["#9be9a8", "#40c463", "#30a14e", "#216e39"]}

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("ID (snake_case):"),
            Input(value=self.source.get("id", ""), id="id"),
            Label("Type (wordpress, quartz, legacy_html, github):"),
            Input(value=self.source.get("type", ""), id="type"),
            Label("URL/Username:"),
            Input(value=self.source.get("url", ""), id="url"),
            Label("Name:"),
            Input(value=self.source.get("name", ""), id="name"),
            Horizontal(
                Button("Save", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.source["id"] = self.query_one("#id").value
            self.source["type"] = self.query_one("#type").value
            self.source["url"] = self.query_one("#url").value
            self.source["name"] = self.query_one("#name").value
            self.dismiss(self.source)
        else:
            self.dismiss(None)

class ManageSourcesApp(App):
    CSS = """
    SourceEditScreen {
        align: center middle;
    }
    #dialog {
        padding: 1 2;
        background: $panel;
        border: thick $primary;
        width: 60;
        height: auto;
    }
    DataTable {
        height: 1fr;
    }
    """
    BINDINGS = [
        ("a", "add_source", "Add Source"),
        ("e", "edit_source", "Edit Source"),
        ("d", "delete_source", "Delete Source"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Type", "Name", "URL")
        table.cursor_type = "row"
        self.reload_data()

    def reload_data(self):
        table = self.query_one(DataTable)
        table.clear()
        self.sources = load_sources()
        for s in self.sources:
            table.add_row(s.get("id"), s.get("type"), s.get("name"), s.get("url"))

    def action_add_source(self):
        def check_save(new_source):
            if new_source:
                self.sources.append(new_source)
                save_sources(self.sources)
                self.reload_data()
        self.push_screen(SourceEditScreen(), check_save)

    def action_edit_source(self):
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            source_id = table.get_row_at(table.cursor_row)[0]
            source = next(s for s in self.sources if s['id'] == source_id)
            def check_save(updated_source):
                if updated_source:
                    idx = next(i for i, s in enumerate(self.sources) if s['id'] == source_id)
                    self.sources[idx] = updated_source
                    save_sources(self.sources)
                    self.reload_data()
            self.push_screen(SourceEditScreen(source), check_save)

    def action_delete_source(self):
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            source_id = table.get_row_at(table.cursor_row)[0]
            self.sources = [s for s in self.sources if s['id'] != source_id]
            save_sources(self.sources)
            self.reload_data()

if __name__ == "__main__":
    ManageSourcesApp().run()
