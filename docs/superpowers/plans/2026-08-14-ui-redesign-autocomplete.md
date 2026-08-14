# UI Redesign & CPU/GPU Autocomplete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `templates/index.html` a real visual design (dark "Tech Dashboard" style) and add browser-native autocomplete (with free-text fallback) to the CPU/GPU fields, backed by two new curated model-name lists.

**Architecture:** Two new flat JSON data files (`data/cpu_models.json`, `data/gpu_models.json`) hold curated lists of common CPU/GPU model names. `app.py` loads them once at import time and passes them to the template. `templates/index.html` gains `<datalist>` elements wired to the CPU/GPU `<input list="...">` fields (native browser autocomplete, no JS), plus a `<style>` block implementing the approved dark color palette. The CLI is untouched — autocomplete is web-only.

**Tech Stack:** Flask/Jinja2 (already in use), plain CSS (no build step, no JS framework), HTML5 `<datalist>`.

---

## File Structure

```
pc-rachat/
├── app.py                       # MODIFIED: loads cpu_models.json/gpu_models.json, passes to template (Task 2)
├── templates/
│   └── index.html               # MODIFIED: datalist wiring (Task 2), full CSS restyle (Task 3)
├── data/
│   ├── cpu_models.json          # NEW: curated list of common CPU model names (Task 1)
│   └── gpu_models.json          # NEW: curated list of common GPU model names (Task 1)
└── tests/
    └── test_app.py              # MODIFIED: datalist test (Task 2), stylesheet-presence test (Task 3)
```

---

### Task 1: CPU/GPU model data files

**Files:**
- Create: `data/cpu_models.json`
- Create: `data/gpu_models.json`

- [ ] **Step 1: Create `data/cpu_models.json`**

```json
[
  "i3-10100",
  "i3-12100",
  "i5-9400F",
  "i5-10400",
  "i5-10400F",
  "i5-11400",
  "i5-11400F",
  "i5-12400",
  "i5-12400F",
  "i5-13400",
  "i5-13400F",
  "i5-13600K",
  "i5-14400F",
  "i5-14600K",
  "i7-8700",
  "i7-9700K",
  "i7-9700F",
  "i7-10700",
  "i7-10700K",
  "i7-10700F",
  "i7-11700",
  "i7-11700K",
  "i7-12700",
  "i7-12700K",
  "i7-12700F",
  "i7-13700K",
  "i7-13700F",
  "i7-14700K",
  "i9-9900K",
  "i9-10900K",
  "i9-11900K",
  "i9-12900K",
  "i9-13900K",
  "i9-14900K",
  "Ryzen 3 3100",
  "Ryzen 3 3300X",
  "Ryzen 5 1600",
  "Ryzen 5 2600",
  "Ryzen 5 3600",
  "Ryzen 5 3600X",
  "Ryzen 5 5500",
  "Ryzen 5 5600",
  "Ryzen 5 5600X",
  "Ryzen 5 5600G",
  "Ryzen 5 7600",
  "Ryzen 5 7600X",
  "Ryzen 7 2700X",
  "Ryzen 7 3700X",
  "Ryzen 7 3800X",
  "Ryzen 7 5700X",
  "Ryzen 7 5700X3D",
  "Ryzen 7 5800X",
  "Ryzen 7 5800X3D",
  "Ryzen 7 7700X",
  "Ryzen 7 7800X3D",
  "Ryzen 9 3900X",
  "Ryzen 9 5900X",
  "Ryzen 9 5950X",
  "Ryzen 9 7900X",
  "Ryzen 9 7950X",
  "Ryzen 9 7950X3D"
]
```

- [ ] **Step 2: Create `data/gpu_models.json`**

```json
[
  "GTX 1050 Ti",
  "GTX 1060",
  "GTX 1070",
  "GTX 1070 Ti",
  "GTX 1080",
  "GTX 1080 Ti",
  "GTX 1650",
  "GTX 1650 Super",
  "GTX 1660",
  "GTX 1660 Super",
  "GTX 1660 Ti",
  "RTX 2060",
  "RTX 2060 Super",
  "RTX 2070",
  "RTX 2070 Super",
  "RTX 2080",
  "RTX 2080 Super",
  "RTX 2080 Ti",
  "RTX 3050",
  "RTX 3060",
  "RTX 3060 Ti",
  "RTX 3070",
  "RTX 3070 Ti",
  "RTX 3080",
  "RTX 3080 Ti",
  "RTX 3090",
  "RTX 3090 Ti",
  "RTX 4060",
  "RTX 4060 Ti",
  "RTX 4070",
  "RTX 4070 Ti",
  "RTX 4070 Ti Super",
  "RTX 4070 Super",
  "RTX 4080",
  "RTX 4080 Super",
  "RTX 4090",
  "RTX 5070",
  "RTX 5070 Ti",
  "RTX 5080",
  "RTX 5090",
  "RX 570",
  "RX 580",
  "RX 590",
  "RX 5500 XT",
  "RX 5600 XT",
  "RX 5700",
  "RX 5700 XT",
  "RX 6600",
  "RX 6600 XT",
  "RX 6650 XT",
  "RX 6700 XT",
  "RX 6750 XT",
  "RX 6800",
  "RX 6800 XT",
  "RX 6900 XT",
  "RX 6950 XT",
  "RX 7600",
  "RX 7700 XT",
  "RX 7800 XT",
  "RX 7900 GRE",
  "RX 7900 XT",
  "RX 7900 XTX"
]
```

- [ ] **Step 3: Validate both files parse as JSON**

Run: `python -c "import json; a=json.load(open('data/cpu_models.json', encoding='utf-8')); b=json.load(open('data/gpu_models.json', encoding='utf-8')); print(len(a), len(b))"`
Expected: prints two integers (CPU count, GPU count), no error — e.g. `55 60` (exact counts depend on the lists above; the point is no JSON parse error)

- [ ] **Step 4: Run the full test suite to confirm nothing broke**

Run: `pytest -v`
Expected: all existing tests still pass (this task adds no code, just data files)

- [ ] **Step 5: Commit**

```bash
git add data/cpu_models.json data/gpu_models.json
git commit -m "feat: add curated CPU/GPU model lists for autocomplete"
```

---

### Task 2: Wire CPU/GPU autocomplete into app.py and the template

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_app.py

def test_index_get_shows_cpu_and_gpu_datalists_with_options():
    client = flask_app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'list="cpu-models"' in response.data
    assert b'list="gpu-models"' in response.data
    assert b'<datalist id="cpu-models">' in response.data
    assert b'<datalist id="gpu-models">' in response.data
    assert "Ryzen 7 5700X".encode("utf-8") in response.data
    assert "RTX 4060".encode("utf-8") in response.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -v -k datalist`
Expected: FAIL — `list="cpu-models"` not found in response (the current template has plain `<input type="text" name="cpu_model" ...>` with no `list` attribute, and no `<datalist>` elements at all)

- [ ] **Step 3: Load the model lists in `app.py`**

In `app.py`, right after the existing `DATA_DIR = Path(__file__).parent / "data"` line, add:

```python
CPU_MODELS = cli_helpers.load_json(DATA_DIR / "cpu_models.json")
GPU_MODELS = cli_helpers.load_json(DATA_DIR / "gpu_models.json")
```

Then find the `render_template(...)` call at the end of the `index()` function and add two new keyword arguments (`cpu_models` and `gpu_models`) so the full call becomes:

```python
    return render_template(
        "index.html",
        result=result,
        buy_grid=buy_grid,
        resale_target=resale_target,
        new_pc_price=new_pc_price,
        error=error,
        form_values=form_values,
        cpu_models=CPU_MODELS,
        gpu_models=GPU_MODELS,
    )
```

- [ ] **Step 4: Wire the datalists into `templates/index.html`**

Find this block (the CPU field):

```html
    <label>Modèle CPU (ex: i5-10400)
      <input type="text" name="cpu_model" value="{{ form_values.cpu_model if form_values else '' }}">
    </label><br>
```

Replace it with:

```html
    <label>Modèle CPU (ex: i5-10400)
      <input type="text" name="cpu_model" list="cpu-models" value="{{ form_values.cpu_model if form_values else '' }}">
      <datalist id="cpu-models">
        {% for model in cpu_models %}
          <option value="{{ model }}">
        {% endfor %}
      </datalist>
    </label><br>
```

Find this block (the GPU field):

```html
    <label>Modèle GPU (laisser vide si intégré)
      <input type="text" name="gpu_model" value="{{ form_values.gpu_model if form_values else '' }}">
    </label><br>
```

Replace it with:

```html
    <label>Modèle GPU (laisser vide si intégré)
      <input type="text" name="gpu_model" list="gpu-models" value="{{ form_values.gpu_model if form_values else '' }}">
      <datalist id="gpu-models">
        {% for model in gpu_models %}
          <option value="{{ model }}">
        {% endfor %}
      </datalist>
    </label><br>
```

Do not change anything else in the file at this step — no styling yet, that's Task 3.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_app.py -v`
Expected: all `test_app.py` tests pass, including the new one

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: 0 failures (this task doesn't touch estimator/ebay_client/retailers/cli logic, only app.py's rendering context and the template)

- [ ] **Step 7: Commit**

```bash
git add app.py templates/index.html tests/test_app.py
git commit -m "feat: wire CPU/GPU autocomplete datalists into the web form"
```

---

### Task 3: Dark "Tech Dashboard" visual restyle

**Files:**
- Modify: `templates/index.html`
- Test: `tests/test_app.py`

## Context

This task replaces the ENTIRE `templates/index.html` file with a styled version. The Jinja logic (variable names, loops, conditionals, the exact `<option value="ddr5" {{ "selected" if ... else "" }}>` pattern used by the existing dropdown-persistence test, and all user-facing text strings like "Modèle CPU", "Total estimé", "Grille d'achat", "Prix de revente visé") must stay byte-for-byte identical to what's already there — only the surrounding HTML structure and a new `<style>` block are added. This preserves every existing `test_app.py` assertion (they check for these exact substrings in the response, e.g. `assert "Modèle CPU".encode("utf-8") in response.data`).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_app.py

def test_index_get_includes_dark_theme_stylesheet():
    client = flask_app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"<style>" in response.data
    assert b"#1a2233" in response.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -v -k dark_theme`
Expected: FAIL — no `<style>` tag exists in the current template

- [ ] **Step 3: Replace `templates/index.html` in full**

```html
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>pc-rachat</title>
  <style>
    :root {
      --bg: #1a2233;
      --bg-field: #0f1521;
      --border: #2d3a52;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --accent: #f59e0b;
    }
    * { box-sizing: border-box; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', system-ui, sans-serif;
      margin: 0;
      padding: 32px 16px;
    }
    .page {
      max-width: 560px;
      margin: 0 auto;
    }
    h1 {
      font-size: 22px;
      margin-bottom: 24px;
    }
    h2 {
      font-size: 16px;
      color: var(--accent);
      margin: 24px 0 8px;
    }
    .card {
      background: var(--bg-field);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
    }
    .field {
      margin-bottom: 14px;
    }
    .field label {
      display: block;
      font-size: 12px;
      color: var(--text-muted);
      letter-spacing: 0.5px;
      margin-bottom: 6px;
      text-transform: uppercase;
    }
    .field input, .field select {
      width: 100%;
      background: var(--bg-field);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px 12px;
      color: var(--text);
      font-size: 14px;
    }
    .field input:focus, .field select:focus {
      outline: none;
      border-color: var(--accent);
    }
    .field-row {
      display: flex;
      gap: 12px;
    }
    .field-row .field {
      flex: 1;
    }
    button {
      width: 100%;
      background: var(--accent);
      color: var(--bg);
      font-weight: 700;
      border: none;
      border-radius: 6px;
      padding: 12px;
      font-size: 14px;
      cursor: pointer;
      margin-top: 8px;
    }
    button:hover {
      opacity: 0.9;
    }
    .error {
      color: #fca5a5;
      background: #3f1d1d;
      border: 1px solid #7f1d1d;
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 16px;
      font-size: 13px;
    }
    .result-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .result-list li {
      background: var(--bg-field);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 6px;
      font-size: 13px;
    }
    .total {
      font-weight: 700;
      font-size: 15px;
      margin-top: 10px;
    }
    .warning {
      color: var(--accent);
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="page">
    <h1>Estimation de rachat PC</h1>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}

    <div class="card">
      <form method="post">
        <div class="field">
          <label>Modèle CPU (ex: i5-10400)</label>
          <input type="text" name="cpu_model" list="cpu-models" value="{{ form_values.cpu_model if form_values else '' }}">
          <datalist id="cpu-models">
            {% for model in cpu_models %}
              <option value="{{ model }}">
            {% endfor %}
          </datalist>
        </div>

        <div class="field-row">
          <div class="field">
            <label>RAM (Go)</label>
            <input type="text" name="ram_go" value="{{ form_values.ram_go if form_values else '' }}">
          </div>
          <div class="field">
            <label>Type RAM</label>
            <select name="ram_type">
              <option value="ddr3" {{ "selected" if form_values and form_values.ram_type == "ddr3" else "" }}>DDR3</option>
              <option value="ddr4" {{ "selected" if form_values and form_values.ram_type == "ddr4" else "" }}>DDR4</option>
              <option value="ddr5" {{ "selected" if form_values and form_values.ram_type == "ddr5" else "" }}>DDR5</option>
            </select>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Stockage (Go)</label>
            <input type="text" name="storage_go" value="{{ form_values.storage_go if form_values else '' }}">
          </div>
          <div class="field">
            <label>Type stockage</label>
            <select name="storage_type">
              <option value="hdd" {{ "selected" if form_values and form_values.storage_type == "hdd" else "" }}>HDD</option>
              <option value="ssd" {{ "selected" if form_values and form_values.storage_type == "ssd" else "" }}>SSD</option>
              <option value="nvme" {{ "selected" if form_values and form_values.storage_type == "nvme" else "" }}>NVMe</option>
            </select>
          </div>
        </div>

        <div class="field">
          <label>Modèle GPU (laisser vide si intégré)</label>
          <input type="text" name="gpu_model" list="gpu-models" value="{{ form_values.gpu_model if form_values else '' }}">
          <datalist id="gpu-models">
            {% for model in gpu_models %}
              <option value="{{ model }}">
            {% endfor %}
          </datalist>
        </div>

        <button type="submit">Estimer</button>
      </form>
    </div>

    {% if new_pc_price is not none %}
      <h2>Grille d'achat</h2>
      <div class="card">
        <p>Prix neuf équivalent estimé : {{ "%.2f"|format(new_pc_price) }}€</p>
        <ul class="result-list">
          {% for tier in buy_grid %}
            <li>
              {% if tier.is_last %}
                au-delà de {{ "%.2f"|format(tier.max_price) }}€ {{ tier.emoji }} {{ tier.label }}
              {% else %}
                jusqu'à {{ "%.2f"|format(tier.max_price) }}€ {{ tier.emoji }} {{ tier.label }}
              {% endif %}
            </li>
          {% endfor %}
        </ul>
      </div>

      <h2>Prix de revente visé</h2>
      <div class="card">
        <p>{{ "%.2f"|format(resale_target.min) }}€ – {{ "%.2f"|format(resale_target.max) }}€</p>
      </div>
    {% elif result %}
      <p class="warning">Grille d'achat non disponible — aucun PC neuf comparable trouvé.</p>
    {% endif %}

    {% if result %}
      <h2>Détail par composant</h2>
      <div class="card">
        <ul class="result-list">
          {% for key, label in [("cpu", "CPU"), ("ram", "RAM"), ("storage", "Stockage"), ("gpu", "GPU")] %}
            <li>
              {% if result.breakdown[key] %}
                {{ label }} : {{ "%.2f"|format(result.breakdown[key].value) }}€ ({{ result.breakdown[key].method }})
              {% elif key == "gpu" and key not in result.missing %}
                {{ label }} : non renseigné
              {% else %}
                {{ label }} : prix inconnu ⚠
              {% endif %}
            </li>
          {% endfor %}
        </ul>
        <p class="total">Total estimé : {{ "%.2f"|format(result.total) }}€</p>
        {% if result.missing %}
          <p class="warning">⚠ estimation incomplète — composants inconnus : {{ result.missing|join(", ") }}</p>
        {% endif %}
      </div>
    {% endif %}
  </div>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py -v`
Expected: all `test_app.py` tests pass, including the new stylesheet test — and critically, ALL pre-existing tests too (`test_index_get_shows_the_form`, `test_index_post_shows_component_breakdown`, `test_index_post_shows_buy_grid_when_new_pc_price_found`, `test_index_post_with_invalid_number_reshows_form_with_error`, `test_index_post_with_validation_error_keeps_ram_type_selected`, and Task 2's new datalist test)

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: 0 failures

- [ ] **Step 6: Commit**

```bash
git add templates/index.html tests/test_app.py
git commit -m "feat: apply dark Tech Dashboard visual style to the web form"
```

---

### Task 4: Manual end-to-end verification

**Files:** none (manual verification only)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: all tests pass, 0 failed

- [ ] **Step 2: Start the app and check the rendered page**

Run: `python app.py` in the background, then check the response:
```bash
curl -s http://127.0.0.1:5000/
```
Expected: the HTML response contains `<style>`, `#1a2233`, `list="cpu-models"`, `list="gpu-models"`, `<datalist id="cpu-models">` with `<option value="Ryzen 7 5700X">` somewhere inside it, and `<datalist id="gpu-models">` with `<option value="RTX 4060">` somewhere inside it.

- [ ] **Step 3: Submit the form and check the styled result renders**

```bash
curl -s -X POST http://127.0.0.1:5000/ -d "cpu_model=i5-10400&ram_go=16&ram_type=ddr4&storage_go=512&storage_type=ssd&gpu_model=gtx 1660"
```
Expected: HTTP 200, response contains `class="card"`, `Total estimé`, no server error/traceback.

- [ ] **Step 4: Stop the server**

Make sure no `python app.py` process is left running (check with your platform's process listing tool and kill it if needed).

- [ ] **Step 5: Commit any fixes discovered**

```bash
git add -A
git commit -m "fix: address issues found during manual UI verification"
```

(Skip this commit if no fixes were needed.)
