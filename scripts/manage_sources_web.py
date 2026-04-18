import yaml
import os
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
SOURCES_FILE = os.path.join(DATA_DIR, 'sources.yaml')

def load_sources():
    if not os.path.exists(SOURCES_FILE):
        return []
    with open(SOURCES_FILE, 'r') as f:
        try:
            return yaml.safe_load(f) or []
        except Exception:
            return []

def save_sources(sources):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SOURCES_FILE, 'w') as f:
        yaml.dump(sources, f, sort_keys=False, default_flow_style=False)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manage Sources</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; background-color: #f8f9fa; }
        .card { margin-bottom: 20px; }
        .color-box { width: 20px; height: 20px; display: inline-block; border: 1px solid #dee2e6; margin-right: 4px; vertical-align: middle; border-radius: 3px; }
        .type-badge { font-size: 0.8em; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Manage Sources</h1>
            <button class="btn btn-primary" onclick="showAddModal()">+ Add Source</button>
        </div>

        <div class="card shadow-sm">
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0" id="sourcesTable">
                        <thead class="table-light">
                            <tr>
                                <th>Name / ID</th>
                                <th>Type</th>
                                <th>URL / Username</th>
                                <th>Colors</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="sourcesBody">
                            <!-- Data will be populated here -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal -->
    <div class="modal fade" id="sourceModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="modalTitle">Add Source</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="sourceForm">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">ID (snake_case)</label>
                                <input type="text" class="form-control" id="sourceId" required placeholder="e.g. my_blog">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Type</label>
                                <select class="form-select" id="sourceType" required onchange="toggleGithubOptions()">
                                    <option value="wordpress">WordPress</option>
                                    <option value="quartz">Quartz</option>
                                    <option value="legacy_html">Legacy HTML</option>
                                    <option value="github">GitHub</option>
                                </select>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Display Name</label>
                                <input type="text" class="form-control" id="sourceName" required placeholder="e.g. My Awesome Blog">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label" id="urlLabel">URL</label>
                                <input type="text" class="form-control" id="sourceUrl" required placeholder="https://example.com">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Colors (4 hex codes, one per line or comma separated)</label>
                            <textarea class="form-control" id="sourceColors" rows="2" placeholder="#9be9a8&#10;#40c463&#10;#30a14e&#10;#216e39"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Exclude (URLs or repo names, one per line)</label>
                            <textarea class="form-control" id="sourceExclude" rows="3"></textarea>
                        </div>
                        <div class="mb-3 form-check" id="githubOptions" style="display:none;">
                            <input type="checkbox" class="form-check-input" id="sourceExcludeForks">
                            <label class="form-check-label">Exclude Forks</label>
                        </div>
                        <input type="hidden" id="editIndex" value="-1">
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveSource()">Save Source</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let sources = [];
        const modalEl = document.getElementById('sourceModal');
        const modal = new bootstrap.Modal(modalEl);

        async function fetchSources() {
            try {
                const res = await fetch('/api/sources');
                sources = await res.json();
                renderTable();
            } catch (err) {
                console.error('Failed to fetch sources:', err);
            }
        }

        function renderTable() {
            const body = document.getElementById('sourcesBody');
            body.innerHTML = '';
            sources.forEach((s, index) => {
                const colorsHtml = (s.colors || []).map(c => `<span class="color-box" style="background-color: ${c}" title="${c}"></span>`).join('');
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <div class="fw-bold">${s.name || 'No Name'}</div>
                        <div class="text-muted small">${s.id}</div>
                    </td>
                    <td><span class="badge bg-secondary type-badge">${s.type}</span></td>
                    <td class="text-truncate" style="max-width: 250px;">
                        <a href="${s.type === 'github' ? 'https://github.com/' + s.url : s.url}" target="_blank" class="text-decoration-none">${s.url}</a>
                    </td>
                    <td>${colorsHtml}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editSource(${index})">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteSource(${index})">Delete</button>
                    </td>
                `;
                body.appendChild(row);
            });
        }

        function toggleGithubOptions() {
            const type = document.getElementById('sourceType').value;
            const githubOptions = document.getElementById('githubOptions');
            const urlLabel = document.getElementById('urlLabel');
            const urlInput = document.getElementById('sourceUrl');

            if (type === 'github') {
                githubOptions.style.display = 'block';
                urlLabel.innerText = 'GitHub Username';
                urlInput.placeholder = 'e.g. octocat';
            } else {
                githubOptions.style.display = 'none';
                urlLabel.innerText = 'URL';
                urlInput.placeholder = 'https://example.com';
            }
        }

        function showAddModal() {
            document.getElementById('modalTitle').innerText = 'Add Source';
            document.getElementById('sourceForm').reset();
            document.getElementById('editIndex').value = '-1';
            toggleGithubOptions();
            modal.show();
        }

        function editSource(index) {
            const s = sources[index];
            document.getElementById('modalTitle').innerText = 'Edit Source';
            document.getElementById('sourceId').value = s.id || '';
            document.getElementById('sourceType').value = s.type || 'wordpress';
            document.getElementById('sourceName').value = s.name || '';
            document.getElementById('sourceUrl').value = s.url || '';
            document.getElementById('sourceColors').value = (s.colors || []).join('\\n');
            document.getElementById('sourceExclude').value = (s.exclude || []).join('\\n');
            document.getElementById('sourceExcludeForks').checked = !!s.exclude_forks;
            document.getElementById('editIndex').value = index;
            toggleGithubOptions();
            modal.show();
        }

        async function saveSource() {
            const index = parseInt(document.getElementById('editIndex').value);
            const source = {
                id: document.getElementById('sourceId').value,
                type: document.getElementById('sourceType').value,
                name: document.getElementById('sourceName').value,
                url: document.getElementById('sourceUrl').value,
                colors: document.getElementById('sourceColors').value.split(/[\\n,]+/).map(c => c.trim()).filter(c => c),
                exclude: document.getElementById('sourceExclude').value.split(/[\\n,]+/).map(c => c.trim()).filter(c => c),
                exclude_forks: document.getElementById('sourceExcludeForks').checked
            };

            if (!source.id || !source.type || !source.name || !source.url) {
                alert('Please fill in all required fields.');
                return;
            }

            let method = 'POST';
            let url = '/api/sources';

            if (index !== -1) {
                method = 'PUT';
                url = `/api/sources/${index}`;
            }

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(source)
                });

                if (res.ok) {
                    modal.hide();
                    fetchSources();
                } else {
                    const data = await res.json();
                    alert('Error saving source: ' + (data.error || 'Unknown error'));
                }
            } catch (err) {
                alert('Network error while saving source');
            }
        }

        async function deleteSource(index) {
            if (confirm('Are you sure you want to delete this source?')) {
                try {
                    const res = await fetch(`/api/sources/${index}`, { method: 'DELETE' });
                    if (res.ok) {
                        fetchSources();
                    } else {
                        alert('Error deleting source');
                    }
                } catch (err) {
                    alert('Network error while deleting source');
                }
            }
        }

        fetchSources();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sources', methods=['GET'])
def get_sources():
    return jsonify(load_sources())

@app.route('/api/sources', methods=['POST'])
def add_source():
    sources = load_sources()
    data = request.json
    # Basic validation for duplicate ID
    if any(s.get('id') == data.get('id') for s in sources):
        return jsonify({"error": f"Source with ID '{data.get('id')}' already exists"}), 400

    sources.append(data)
    save_sources(sources)
    return jsonify({"status": "ok"})

@app.route('/api/sources/<int:index>', methods=['PUT'])
def update_source(index):
    sources = load_sources()
    if 0 <= index < len(sources):
        sources[index] = request.json
        save_sources(sources)
        return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404

@app.route('/api/sources/<int:index>', methods=['DELETE'])
def delete_source(index):
    sources = load_sources()
    if 0 <= index < len(sources):
        sources.pop(index)
        save_sources(sources)
        return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404

if __name__ == '__main__':
    # Use port 5000 as requested (standard for Flask)
    app.run(host='0.0.0.0', port=5000)
