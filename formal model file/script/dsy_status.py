"""Read-only progress display for independent DSY weather experiments."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', default='Z1_DSY1_2030s_HIGH50_CIBSE_v1.1')
    parser.add_argument('--mode', choices=['pilot', 'full'], default='full')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    folder = root / '02_conference/03_data/weather_scenarios' / args.scenario / args.mode
    print(f'Output: {folder}')
    if not (folder / 'protocol.json').exists():
        print('NOT STARTED (no protocol found)')
        return
    protocol = json.loads((folder / 'protocol.json').read_text())
    expected = 2 * len(protocol['run_ids'])
    rows = []
    if (folder / 'results.csv').exists():
        with (folder / 'results.csv').open() as stream:
            rows = list(csv.DictReader(stream))
    ok = sum(row['status'] == 'ok' for row in rows)
    print(f'Aggregate CSV: {len(rows)}/{expected}; passed: {ok}; failed: {len(rows)-ok}')
    checkpoints = []
    for arch in ('detached', 'semi'):
        completed = []
        invalid = 0
        for rid in protocol['run_ids']:
            saved = folder / 'runs' / arch / rid / 'result.json'
            if saved.exists():
                try:
                    record = json.loads(saved.read_text())
                    if record.get('archetype') != arch or record.get('run_id') != rid:
                        raise ValueError('Checkpoint identity mismatch')
                    completed.append(record)
                except (ValueError, OSError):
                    invalid += 1
        passed = sum(r.get('status') == 'ok' for r in completed)
        print(f'{arch} checkpoints: {len(completed)}/{len(protocol["run_ids"])}; '
              f'passed: {passed}; failed: {len(completed)-passed}; unreadable: {invalid}')
        checkpoints.extend(completed)
    print(f'Total case checkpoints: {len(checkpoints)}/{expected}')
    if len(checkpoints) != len(rows):
        print('WARNING: aggregate CSV is behind case checkpoints. Final aggregation/verification is pending.')
    print('Checkpoint counts report saved audit status; they do not rehash or revalidate every output.')
    complete = folder / 'completion.json'
    if complete.exists():
        print('Completion record:', json.loads(complete.read_text()))
    else:
        print('INCOMPLETE: no completion marker. This alone does not prove a process is running.')
        execution = folder / 'execution.json'
        if execution.exists():
            start = datetime.fromisoformat(json.loads(execution.read_text())['started_utc'])
            print(f'Minutes since latest launch: {(datetime.now(timezone.utc)-start).total_seconds()/60:.1f}')
    for row in [r for r in rows if r['status'] != 'ok'][:5]:
        print('Failure:', row['archetype'], row['run_id'], row.get('error'))
    evaluation = folder / 'evaluation'
    if (evaluation / 'protocol.json').exists():
        ep = json.loads((evaluation / 'protocol.json').read_text())
        done = sum((evaluation / a / f'seed_{s}/complete.json').exists()
                   for a in ('detached', 'semi') for s in ep['seeds'])
        print(f'Model evaluation: {done}/{2*len(ep["seeds"])} archetype/split tasks complete')
        print('Model aggregate complete:', (evaluation / 'complete.json').exists())
        print('Independent model verification complete:', (evaluation / 'verification.json').exists())


if __name__ == '__main__':
    main()
