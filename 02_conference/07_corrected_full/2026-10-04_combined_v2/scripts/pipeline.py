"""Run both weather batches, overlapping TMYx model training with DSY simulations."""
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def launch(script, name, *args):
    log = (ROOT / 'logs' / f'{name}.log').open('a')
    proc = subprocess.Popen([sys.executable, '-B', str(ROOT / 'scripts' / script), *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    print(f'START {name} PID={proc.pid}', flush=True)
    return proc


def wait(proc, name):
    while proc.poll() is None:
        time.sleep(10)
    if proc.returncode != 0:
        raise RuntimeError(f'{name} exited {proc.returncode}; inspect logs, do not claim completion')
    print(f'COMPLETE {name}', flush=True)


if __name__ == '__main__':
    first = launch('simulate.py', 'simulation_TMYx', 'TMYx', '--workers', '8')
    wait(first, 'simulation_TMYx')
    learning = launch('train_models.py', 'models_TMYx', 'TMYx', '--workers', '3')
    second = launch('simulate.py', 'simulation_DSY1', 'DSY1', '--workers', '8')
    wait(second, 'simulation_DSY1')
    wait(learning, 'models_TMYx')
    final = launch('train_models.py', 'models_DSY1', 'DSY1', '--workers', '3')
    wait(final, 'models_DSY1')
    print('BOTH CORRECTED WEATHER DATASETS AND MODEL EVALUATIONS COMPLETE', flush=True)
