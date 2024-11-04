import importlib
from pathlib import Path

scan_dir = Path(__file__).parent

for module in scan_dir.glob('*.py'):
    if module.stem == '__init__':
        continue
    importlib.import_module(f'.{module.stem}', 'muxer.tasks')
