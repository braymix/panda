from flask import Flask, jsonify, request, render_template, send_file, abort
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

PANDA_HOME = Path.home() / "panda"
TASKS_DIR = PANDA_HOME / "tasks"
RESULTS_DIR = PANDA_HOME / "results"
LOGS_DIR = PANDA_HOME / "logs"
STATUS_DIR = PANDA_HOME / "status"
CONFIG_FILE = PANDA_HOME / "config" / "panda.json"
MODELS_STL_DIR = PANDA_HOME / "models" / "stl"
MODELS_SCAD_DIR = PANDA_HOME / "models" / "scad"

# =========================
# HELPERS
# =========================

def _load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def _load_status():
    status_file = STATUS_DIR / "current.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            pass
    return None


def _get_result_for_stl(stl_filename):
    """Cerca il result JSON che ha generato un determinato STL."""
    if not RESULTS_DIR.exists():
        return None
    stl_name = Path(stl_filename).name
    for f in sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            stl_file = data.get("stl_file", "")
            if stl_file and Path(stl_file).name == stl_name:
                return data
        except Exception:
            continue
    return None


def _safe_name(filename):
    """Estrae solo il nome file, prevenendo path traversal."""
    return Path(filename).name

# =========================
# EXISTING ROUTES
# =========================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    result = subprocess.run(['systemctl', 'is-active', 'panda'], capture_output=True, text=True)
    panda_running = (result.stdout.strip() == 'active')
    current_task = _load_status()
    config = _load_config()
    models_count = len(list(MODELS_STL_DIR.glob("*.stl"))) if MODELS_STL_DIR.exists() else 0
    return jsonify({
        'panda_running': panda_running,
        'current_task': current_task,
        'models_count': models_count,
        'last_model': current_task.get('last_model') if current_task else None,
        'ollama_model': config.get('model'),
    })


@app.route('/api/tasks/pending')
def api_tasks_pending():
    tasks = []
    for f in sorted(TASKS_DIR.glob('*.json')):
        if f.name.startswith('_'):
            continue
        try:
            data = json.loads(f.read_text())
            tasks.append({
                'filename': f.name,
                'id': data.get('id', ''),
                'type': data.get('type', ''),
                'priority': data.get('priority', 10),
                'prompt': data.get('prompt', '')[:80],
            })
        except:
            pass
    tasks.sort(key=lambda x: x['priority'])
    return jsonify(tasks)


@app.route('/api/tasks/done')
def api_tasks_done():
    tasks = []
    done_dir = TASKS_DIR / 'done'
    if done_dir.exists():
        files = sorted(done_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:30]
        for f in files:
            try:
                data = json.loads(f.read_text())
                tasks.append({'filename': f.name, 'id': data.get('id', ''), 'type': data.get('type', '')})
            except:
                pass
    return jsonify(tasks)


@app.route('/api/results')
def api_results():
    results = []
    if RESULTS_DIR.exists():
        files = sorted(RESULTS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:30]
        for f in files:
            try:
                data = json.loads(f.read_text())
                results.append({
                    'filename': f.name,
                    'task_id': data.get('task_id', ''),
                    'success': data.get('success', False),
                })
            except:
                pass
    return jsonify(results)


@app.route('/api/logs')
def api_logs():
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f'{today}.log'
    lines = []
    if log_file.exists():
        lines = log_file.read_text().split('\n')[-150:]
    return jsonify({'lines': lines})


@app.route('/api/control/<action>', methods=['POST'])
def api_control(action):
    if action not in ['start', 'stop', 'restart']:
        return jsonify({'success': False})
    result = subprocess.run(['sudo', 'systemctl', action, 'panda'], capture_output=True, text=True)
    return jsonify({'success': result.returncode == 0})


@app.route('/api/tasks/add', methods=['POST'])
def api_tasks_add():
    data = request.get_json()
    task_id = data.get('id', f'task_{int(time.time())}')
    filename = f"task_{int(time.time())}_{task_id}.json"
    filepath = TASKS_DIR / filename
    task = {
        'id': task_id,
        'type': data.get('type', 'prompt'),
        'priority': data.get('priority', 10),
        'prompt': data.get('prompt', ''),
    }
    if data.get('filepath'):
        task['filepath'] = data['filepath']
    filepath.write_text(json.dumps(task, indent=2))
    return jsonify({'success': True, 'filename': filename})


@app.route('/api/tasks/pending/<filename>', methods=['DELETE'])
def api_tasks_delete(filename):
    filepath = TASKS_DIR / _safe_name(filename)
    if filepath.exists():
        filepath.unlink()
    return jsonify({'success': True})


@app.route('/api/tasks/import', methods=['POST'])
def api_tasks_import():
    data = request.get_json()
    tasks = data.get('tasks', [])
    filenames = []
    for t in tasks:
        task_id = t.get('id', f'task_{int(time.time())}')
        filename = f"task_{int(time.time())}_{task_id}.json"
        filepath = TASKS_DIR / filename
        filepath.write_text(json.dumps(t, indent=2))
        filenames.append(filename)
        time.sleep(0.01)
    return jsonify({'success': True, 'imported': len(filenames), 'filenames': filenames})

# =========================
# 3D MODEL ROUTES
# =========================

@app.route('/api/models')
def api_models():
    if not MODELS_STL_DIR.exists():
        return jsonify([])
    models = []
    for stl in sorted(MODELS_STL_DIR.glob('*.stl'), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = stl.stat()
        scad_path = MODELS_SCAD_DIR / (stl.stem + '.scad')
        result_data = _get_result_for_stl(stl.name)
        task_id = result_data.get('task_id', '') if result_data else ''
        models.append({
            'filename': stl.name,
            'stl_path': str(stl),
            'scad_path': str(scad_path) if scad_path.exists() else None,
            'size_kb': round(stat.st_size / 1024, 2),
            'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'task_id': task_id,
        })
    return jsonify(models)


@app.route('/api/models/<filename>/download')
def api_models_download(filename):
    stl_path = MODELS_STL_DIR / _safe_name(filename)
    if not stl_path.exists():
        abort(404)
    return send_file(
        stl_path,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=stl_path.name,
    )


@app.route('/api/models/<filename>/scad')
def api_models_scad(filename):
    stem = Path(_safe_name(filename)).stem
    scad_path = MODELS_SCAD_DIR / (stem + '.scad')
    if not scad_path.exists():
        abort(404)
    return send_file(
        scad_path,
        mimetype='text/plain',
        as_attachment=True,
        download_name=scad_path.name,
    )


@app.route('/api/models/<filename>/info')
def api_models_info(filename):
    safe_name = _safe_name(filename)
    stl_path = MODELS_STL_DIR / safe_name
    if not stl_path.exists():
        abort(404)
    stat = stl_path.stat()
    scad_path = MODELS_SCAD_DIR / (stl_path.stem + '.scad')
    result_data = _get_result_for_stl(safe_name)
    task_id = result_data.get('task_id', '') if result_data else ''
    compile_log = result_data.get('compile_log', '') if result_data else ''
    return jsonify({
        'filename': safe_name,
        'size_kb': round(stat.st_size / 1024, 2),
        'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'task_id': task_id,
        'scad_available': scad_path.exists(),
        'scad_path': str(scad_path) if scad_path.exists() else None,
        'compile_log': compile_log,
    })


@app.route('/api/models/<filename>', methods=['DELETE'])
def api_models_delete(filename):
    safe_name = _safe_name(filename)
    stl_path = MODELS_STL_DIR / safe_name
    if not stl_path.exists():
        return jsonify({'success': False, 'error': 'File non trovato'})
    stl_path.unlink()
    scad_path = MODELS_SCAD_DIR / (stl_path.stem + '.scad')
    scad_deleted = False
    if scad_path.exists():
        scad_path.unlink()
        scad_deleted = True
    return jsonify({'success': True, 'scad_deleted': scad_deleted})


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json() or {}
    description = data.get('description', '').strip()
    if not description:
        return jsonify({'success': False, 'error': 'description richiesta'}), 400
    task_id = f"gen3d_{int(time.time())}"
    filename = f"task_{int(time.time())}_{task_id}.json"
    task = {
        'id': task_id,
        'type': 'generate_3d',
        'description': description,
        'parameters': data.get('parameters', {}),
        'object_type': data.get('object_type', 'simple'),
        'quality': data.get('quality', 'medium'),
        'priority': data.get('priority', 1),
    }
    TASKS_DIR.mkdir(exist_ok=True)
    (TASKS_DIR / filename).write_text(json.dumps(task, indent=2))
    return jsonify({'success': True, 'task_id': task_id, 'filename': filename})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
