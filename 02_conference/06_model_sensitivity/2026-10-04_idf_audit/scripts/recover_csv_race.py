"""Preserve and recover only the observed ReadVarsESO working-directory race."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from run_sensitivity import EXPERIMENT, atomic_json, digest, execute, require

SNAPSHOT = EXPERIMENT / 'backup/execution_v1'
RUNNER = EXPERIMENT / 'scripts/run_sensitivity.py'


def snapshot():
    completion = json.loads((EXPERIMENT / 'results/full_completion.json').read_text())
    require(completion['runs'] == 1440 and not completion['all_ok'], 'Initial full stage must have completed with a failure')
    require(not SNAPSHOT.exists(), 'Snapshot already exists')
    SNAPSHOT.mkdir()
    for path in [RUNNER, EXPERIMENT / 'protocol.json', EXPERIMENT / 'results/full_completion.json', EXPERIMENT / 'results/full_results.csv']:
        shutil.copy2(path, SNAPSHOT / path.name)
    print('Preserved initial runner, protocol, failure summary and all initial results.')


def retry():
    old = (SNAPSHOT / RUNNER.name).read_text()
    before = 'stdout=stdout, stderr=stderr, timeout=180)'
    after = 'stdout=stdout, stderr=stderr, cwd=folder, timeout=180)'
    require(old.count(before) == 1 and RUNNER.read_text() == old.replace(before, after), 'Only the working-directory execution fix is allowed')
    initial = json.loads((SNAPSHOT / 'protocol.json').read_text())
    current = json.loads((EXPERIMENT / 'protocol.json').read_text())
    require(initial == current, 'Unexpected protocol change before recovery')
    failed = []
    for result in (EXPERIMENT / 'runs').glob('*/*/*/*/result.json'):
        record = json.loads(result.read_text())
        if record['status'] != 'ok':
            errors = (result.parent / 'eplusout.err').read_text()
            severe = [line for line in errors.splitlines() if '** Severe' in line]
            require(len(severe) == 1 and 'readvars.audit' in severe[0] and 'No such file or directory' in severe[0], 'Failure is not the known CSV audit-file race')
            failed.append((result.parent, record))
    require(len(failed) > 0, 'No known failures to recover')
    current['script_hashes'][str(RUNNER)] = digest(RUNNER)
    current['execution_history'] = {
        'initial_protocol': str(SNAPSHOT / 'protocol.json'),
        'initial_protocol_sha256': digest(SNAPSHOT / 'protocol.json'),
        'initial_runner_sha256': digest(SNAPSHOT / RUNNER.name),
        'initial_full_results_sha256': digest(SNAPSHOT / 'full_results.csv'),
        'initial_failed_runs': len(failed),
        'fix': 'subprocess cwd is the individual run folder, avoiding shared readvars.audit; no IDF/weather/metric changes',
        'fix_utc': datetime.now(timezone.utc).isoformat(),
        'recovery_script_sha256': digest(Path(__file__)),
        'successful_initial_runs_reused': True,
    }
    atomic_json(EXPERIMENT / 'protocol.json', current)
    for folder, record in failed:
        dest = EXPERIMENT / 'backup/failed_attempts' / folder.relative_to(EXPERIMENT / 'runs')
        dest.parent.mkdir(parents=True, exist_ok=True)
        require(not dest.exists(), 'Preserved failed attempt already exists')
        shutil.move(str(folder), str(dest))
    # All successful outputs are hash-checked and reused; only failed runs execute.
    execute('full', 1)
    for folder, record in failed:
        result = folder / 'result.json'
        recovered = json.loads(result.read_text())
        require(recovered['status'] == 'ok', 'Recovery did not complete')
        recovered['recovered_from'] = str(EXPERIMENT / 'backup/failed_attempts' / folder.relative_to(EXPERIMENT / 'runs'))
        recovered['recovery_script_sha256'] = digest(Path(__file__))
        atomic_json(result, recovered)
    completion_path = EXPERIMENT / 'results/full_completion.json'
    completion = json.loads(completion_path.read_text())
    completion['initial_failures'] = len(failed)
    completion['recovered_with_isolated_workdirs'] = len(failed)
    atomic_json(completion_path, completion)
    print(f'Recovered {len(failed)} failed runs, preserving original failure records.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['snapshot', 'retry'])
    args = parser.parse_args()
    snapshot() if args.stage == 'snapshot' else retry()
