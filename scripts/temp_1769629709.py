import time, pathlib

base = pathlib.Path('~/panda/factory').expanduser()
files_path = base/'work'/'files.txt'
files = files_path.read_text().splitlines() if files_path.exists() else []
out = base/'output'
out.mkdir(exist_ok=True)
# Batch: crea un output per ogni file
for f in files:
    time.sleep(2)
    (out / (pathlib.Path(f).stem + '_done.txt')).write_text(f'OK {f}\n')
print('BATCH_DONE')