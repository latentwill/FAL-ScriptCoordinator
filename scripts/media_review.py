#!/usr/bin/env python3
"""Probe local footage and make a silent seam preview. Never edits source files."""
import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def run(args):
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout


def probe(path):
    source = Path(path).resolve(strict=True)
    data = json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                           '-show_format', '-of', 'json', str(source)]))
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError('No video stream')
    fps = Fraction(video['avg_frame_rate'])
    nominal = Fraction(video['r_frame_rate'])
    frames = int(video['nb_read_frames'])
    if fps <= 0 or frames < 1:
        raise ValueError('Invalid frame rate or count')
    return {'file': str(source), 'fps': str(fps), 'nominal_fps': str(nominal),
            'frames': frames, 'duration_seconds': float(video.get('duration', data['format']['duration'])),
            'width': video['width'], 'height': video['height'],
            'audio_streams': sum(s['codec_type'] == 'audio' for s in data['streams'])}


def bounds(a, b, out_frame, in_frame, seconds):
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Window must be positive and finite')
    if not 1 <= out_frame <= a['frames'] or not 0 <= in_frame < b['frames']:
        raise ValueError('Edit points are outside the source; A-out is exclusive, B-in inclusive')
    # Frame-index trims remain correct for VFR. The preview is normalized to CFR;
    # a VFR window duration based on average fps is approximate and is labelled so.
    acount = max(1, round(seconds * float(Fraction(a['fps']))))
    bcount = max(1, round(seconds * float(Fraction(b['fps']))))
    return max(0, out_frame-acount), out_frame, in_frame, min(b['frames'], in_frame+bcount)


def seam(left, right, output, out_frame=None, in_frame=0, seconds=2, fps='24'):
    a, b = probe(left), probe(right)
    target = Path(output).resolve()
    if target in (Path(a['file']), Path(b['file'])) or target.exists():
        raise ValueError('Output must be a new file distinct from both sources')
    rate = Fraction(fps)
    if rate <= 0 or rate > 240:
        raise ValueError('Preview fps must be >0 and <=240')
    starta, enda, startb, endb = bounds(a, b, a['frames'] if out_frame is None else out_frame, in_frame, seconds)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Pad instead of stretching; normalize timebase, pixel format and sample aspect.
    common = f'setpts=PTS-STARTPTS,fps={rate},scale=trunc(iw*sar/2)*2:trunc(ih/2)*2,setsar=1,scale=960:540:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,settb=AVTB'
    filters = (f'[0:v:0]trim=start_frame={starta}:end_frame={enda},{common}[a];'
               f'[1:v:0]trim=start_frame={startb}:end_frame={endb},{common}[b];'
               '[a][b]concat=n=2:v=1:a=0[v]')
    run(['ffmpeg', '-v', 'error', '-n', '-i', a['file'], '-i', b['file'], '-filter_complex', filters,
         '-map', '[v]', '-an', '-c:v', 'libx264', '-crf', '18', '-movflags', '+faststart', str(target)])
    return {'preview': str(target), 'left': a, 'right': b, 'source_frame_ranges': [starta, enda, startb, endb],
            'range_convention': 'zero-based; start inclusive, end exclusive',
            'preview_fps': str(rate), 'audio': 'intentionally omitted for visual seam review',
            'vfr_note': 'Window duration is approximate for variable-frame-rate input; frame trims are exact',
            'review_required': 'Watch at normal speed; this tool does not certify visual or velocity continuity'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest='cmd', required=True)
    x = s.add_parser('probe'); x.add_argument('file')
    x = s.add_parser('seam'); x.add_argument('left'); x.add_argument('right'); x.add_argument('output')
    x.add_argument('--a-out', type=int); x.add_argument('--b-in', type=int, default=0)
    x.add_argument('--seconds', type=float, default=2); x.add_argument('--fps', default='24')
    a = p.parse_args()
    try:
        result = probe(a.file) if a.cmd == 'probe' else seam(a.left, a.right, a.output, a.a_out, a.b_in, a.seconds, a.fps)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, StopIteration, OSError, subprocess.CalledProcessError, ZeroDivisionError) as e:
        print('Media review failed: ' + str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
