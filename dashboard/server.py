from flask import Flask, jsonify, request, render_template
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    result = subprocess.run(['systemctl', 'is-active', 'panda'], capture_output=True, text=True)
    panda_running = (result.stdout.strip() == 'active')
    current_task = None
    status_file = STATUS_DIR / 'current.json'
    if status_file.exists(): current_task = json.loads(status_file.read_text())
    return jsonify({'panda_running': panda_running, 'current_task': current_task})

@app.route('/api/tasks/pending')
def api_tasks_pending():
    tasks = []
    for f in sorted(TASKS_DIR.glob('*.json')):
        if f.name.startswith('_'): continue
        try:
            data = json.loads(f.read_text())
            tasks.append({'filename': f.name, 'id': data.get('id',''), 'type': data.get('type',''), 'priority': data.get('priority',10), 'prompt': data.get('prompt','')[:80]})
        except: pass
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
                tasks.append({'filename': f.name, 'id': data.get('id',''), 'type': data.get('type','')})
            except: pass
    return jsonify(tasks)

@app.route('/api/results')
def api_results():
    results = []
    if RESULTS_DIR.exists():
        files = sorted(RESULTS_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:30]
        for f in files:
            try:
                data = json.loads(f.read_text())
                results.append({'filename': f.name, 'task_id': data.get('task_id',''), 'success': data.get('success',False)})
            except: pass
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
    if action not in ['start','stop','restart']: return jsonify({'success':False})
    result = subprocess.run(['sudo','systemctl',action,'panda'], capture_output=True, text=True)
    return jsonify({'success': result.returncode==0})

@app.route('/api/tasks/add', methods=['POST'])
def api_tasks_add():
    data = request.get_json()
    task_id = data.get('id', f'task_{int(time.time())}')
    filename = f"task_{int(time.time())}_{task_id}.json"
    filepath = TASKS_DIR / filename
    task = {'id': task_id, 'type': data.get('type','prompt'), 'priority': data.get('priority',10), 'prompt': data.get('prompt','')}
    if data.get('filepath'): task['filepath'] = data['filepath']
    filepath.write_text(json.dumps(task, indent=2))
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/tasks/pending/<filename>', methods=['DELETE'])
def api_tasks_delete(filename):
    filepath = TASKS_DIR / filename
    if filepath.exists(): filepath.unlink()
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)