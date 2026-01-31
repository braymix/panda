import time, pathlib
base = pathlib.Path('~/panda/factory').expanduser()
files = base.joinpath('work/files.txt').read_text().splitlines()
out = base.joinpath('output')
out.mkdir(exist_ok=True)
for f in files:
    time.sleep(10)
    (out / (pathlib.Path(f).stem + '_done.txt')).write_text(f'OK {f}\n')
print('BATCH_DONE')