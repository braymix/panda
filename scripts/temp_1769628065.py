import time, pathlib

files = pathlib.Path('~/panda/factory/work/file_list.txt').expanduser().read_text().splitlines()
out = pathlib.Path('~/panda/factory/output').expanduser()
out.mkdir(exist_ok=True)

for f in files:
    time.sleep(5)
    p = out / (pathlib.Path(f).stem + '_processed.txt')
    p.write_text(f'PROCESSED: {f}\n')

print('BATCH_COMPLETED')