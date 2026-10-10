#!/usr/bin/env python3
"""Check declared shot contracts, not the contents of generated images or video."""
import argparse
import json
import math
import sys

BOUNDARY = ('location', 'camera_heading', 'camera_height', 'framing', 'lens_feel',
            'motion_direction', 'speed_class', 'subject_phase', 'visible_asset_states', 'lighting')


def lint(plan):
    errors, warnings = [], []
    shots = plan.get('shots', [])
    if not isinstance(shots, list) or not shots:
        return {'errors': ['shots must be a nonempty list'], 'warnings': []}
    seen = set()
    for i, s in enumerate(shots):
        name = s.get('id', f'index-{i}')
        if name in seen: errors.append(f'{name}: duplicate ID')
        seen.add(name)
        for k in ('purpose', 'primary_camera_move', 'conditioning', 'entry', 'exit', 'join_after'):
            if not s.get(k): errors.append(f'{name}: missing {k}')
        usable, generated = s.get('usable_seconds'), s.get('generation_seconds')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in (usable, generated)):
            errors.append(f'{name}: durations must be positive finite numbers')
        elif usable > generated:
            errors.append(f'{name}: usable duration exceeds generation duration')
        elif usable == generated and s.get('join_after') == 'continuous':
            warnings.append(f'{name}: no generation handles budgeted; inspect boundary ramps carefully')
        for which in ('entry', 'exit'):
            state = s.get(which, {})
            for k in BOUNDARY:
                if k not in state: errors.append(f'{name}: {which} lacks {k}')
        join = s.get('join_after')
        if join not in ('continuous', 'match_action', 'occlusion', 'cutaway', 'cut', 'end'):
            errors.append(f'{name}: invalid join_after')
        if join == 'continuous':
            if s.get('exit', {}).get('speed_class') == 'stopped':
                errors.append(f'{name}: continuous moving handoff declares a stopped exit; use an intentional cut/hold or revise it')
            if s.get('conditioning') == 'image_to_video':
                warnings.append(f'{name}: an image does not carry incoming motion; test the seam or prefer video continuation')
            if i + 1 == len(shots):
                errors.append(f'{name}: continuous join has no next shot')
            else:
                for k in BOUNDARY:
                    if s.get('exit', {}).get(k) != shots[i+1].get('entry', {}).get(k):
                        errors.append(f'{name} -> {shots[i+1].get("id")}: {k} handoff differs')
        if join == 'end' and i != len(shots)-1:
            errors.append(f'{name}: end appears before the final shot')
    warnings.append('Declared state agreement is not visual verification. Review actual clips and seams.')
    return {'errors': errors, 'warnings': warnings}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('plan'); a = p.parse_args()
    try:
        with open(a.plan) as f: result = lint(json.load(f))
        print(json.dumps(result, indent=2)); return bool(result['errors'])
    except (ValueError, TypeError, KeyError, OSError, AttributeError) as e:
        print('Invalid plan: ' + str(e), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
