#!/usr/bin/env python3
"""Offline, transactional production ledger. No network calls or credential handling."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

VERSION = 1
SECRET_KEYS = {'authorization', 'api_key', 'apikey', 'fal_key', 'access_token', 'secret', 'password', 'credentials'}


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ValueError('IDs must be 1–128 letters, digits, dots, underscores or hyphens')
    return value


def no_secrets(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k.lower().replace('-', '_') in SECRET_KEYS:
                raise ValueError('Credential field forbidden in ledger: ' + k)
            no_secrets(v)
    elif isinstance(value, list):
        for v in value:
            no_secrets(v)


def evidence(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('A real decision, display or provider evidence reference is required')
    return value


class Ledger:
    def __init__(self, project, config=None):
        self.root = Path(project).resolve()
        if config is None and not (self.root / 'production.sqlite').is_file():
            raise ValueError('Project has no ledger; initialize it first')
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / 'production.sqlite', timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=30000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS nodes(
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL,
            path TEXT, sha256 TEXT, status TEXT NOT NULL DEFAULT 'draft',
            stale INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS edges(
            child TEXT REFERENCES nodes(id), parent TEXT REFERENCES nodes(id),
            PRIMARY KEY(child,parent), CHECK(child<>parent));
          CREATE TABLE IF NOT EXISTS aliases(name TEXT PRIMARY KEY, node TEXT REFERENCES nodes(id));
          CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, shot TEXT NOT NULL, spec TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'planned', provider_id TEXT,
            output TEXT REFERENCES nodes(id), shown TEXT);
          CREATE TABLE IF NOT EXISTS job_refs(
            job TEXT REFERENCES jobs(id), node TEXT REFERENCES nodes(id), PRIMARY KEY(job,node));
          CREATE TABLE IF NOT EXISTS events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, type TEXT NOT NULL, data TEXT NOT NULL);
        ''')
        with self.tx():
            row = self.db.execute("SELECT value FROM meta WHERE key='version'").fetchone()
            if row is None:
                if config is None:
                    raise ValueError('Missing project configuration')
                no_secrets(config)
                if not isinstance(config.get('show_before_regeneration'), bool):
                    raise ValueError('config.show_before_regeneration must be boolean')
                self.db.execute('INSERT INTO meta VALUES (?,?)', ('version', str(VERSION)))
                self.db.execute('INSERT INTO meta VALUES (?,?)', ('config', encode(config)))
                self.event('init', config)
            elif int(row[0]) != VERSION:
                raise ValueError('Unsupported ledger version; do not overwrite or silently migrate')
            elif config is not None:
                raise ValueError('Project already exists; init cannot overwrite its policy')

    def close(self):
        self.db.close()

    @contextmanager
    def tx(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def event(self, kind, data):
        self.db.execute('INSERT INTO events(at,type,data) VALUES (?,?,?)',
                        (datetime.now(timezone.utc).isoformat(), kind, encode(data)))

    def node(self, key):
        row = self.db.execute('SELECT * FROM nodes WHERE id=?', (key,)).fetchone()
        if row is None:
            raise ValueError('Unknown node: ' + key)
        return row

    def fresh(self, key, accepted=False):
        row = self.node(key)
        if row['stale'] or (accepted and row['status'] != 'accepted'):
            raise ValueError('Stale or unaccepted reference: ' + key)
        # Validate all ancestor files as well as the immediate reference.
        ancestors = self.db.execute('''WITH RECURSIVE a(id) AS (
          SELECT ? UNION SELECT e.parent FROM edges e JOIN a ON e.child=a.id)
          SELECT n.* FROM nodes n JOIN a ON a.id=n.id''', (key,)).fetchall()
        for n in ancestors:
            if n['stale']:
                raise ValueError('Stale ancestor: ' + n['id'])
            if n['path']:
                path = (self.root / n['path']).resolve()
                if not path.is_relative_to(self.root) or not path.is_file() or digest(path) != n['sha256']:
                    raise ValueError('Missing or modified immutable asset: ' + n['id'])
        return row

    def put_node(self, spec):
        key = identifier(spec['id'])
        no_secrets(spec)
        parents = spec.get('parents', [])
        if not isinstance(parents, list) or len(parents) != len(set(parents)):
            raise ValueError('parents must be a unique list of node IDs')
        for parent in parents:
            if parent in self.superseded():
                raise ValueError('Cannot create a new dependency on a superseded reference: ' + parent)
            self.fresh(parent)
        path = sha = None
        if spec.get('file'):
            src = Path(spec['file']).resolve(strict=True)
            if not src.is_file():
                raise ValueError('Asset must be a regular file')
            folder = self.root / 'assets'
            folder.mkdir(exist_ok=True)
            # Hash the copied bytes, not a source which may change during copying.
            with tempfile.NamedTemporaryFile(dir=folder, prefix='.import-', delete=False) as tmp:
                temp = Path(tmp.name)
            try:
                shutil.copyfile(src, temp)
                with temp.open('rb') as durable:
                    os.fsync(durable.fileno())
                sha = digest(temp)
                suffix = src.suffix.lower() if re.fullmatch(r'\.[a-zA-Z0-9]{1,10}', src.suffix) else ''
                target = folder / (sha + suffix)
                if target.exists():
                    if digest(target) != sha:
                        raise ValueError('Content-addressed store was modified')
                else:
                    temp.replace(target)
                    if os.name == 'posix':
                        fd = os.open(folder, os.O_RDONLY)
                        try:
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                path = str(target.relative_to(self.root))
            finally:
                temp.unlink(missing_ok=True)
        self.db.execute('INSERT INTO nodes(id,kind,data,path,sha256,created) VALUES (?,?,?,?,?,?)',
                        (key, spec['kind'], encode(spec.get('data', {})), path, sha,
                         datetime.now(timezone.utc).isoformat()))
        for parent in parents:
            self.db.execute('INSERT INTO edges VALUES (?,?)', (key, parent))
        self.event('node', {'id': key, 'parents': parents, 'sha256': sha})
        return key

    def add(self, spec):
        with self.tx():
            return self.put_node(spec)

    def review(self, key, decision, source):
        evidence(source)
        if decision not in ('accepted', 'rejected'):
            raise ValueError('Decision must be accepted or rejected')
        with self.tx():
            row = self.fresh(key) if decision == 'accepted' else self.node(key)
            if row['status'] != 'draft':
                raise ValueError('Review is immutable; create a new version for a new decision')
            if decision == 'accepted':
                for p in self.db.execute('SELECT parent FROM edges WHERE child=?', (key,)):
                    self.fresh(p[0], accepted=True)
                jobs = self.db.execute('SELECT * FROM jobs WHERE output=?', (key,)).fetchall()
                if self.config()['show_before_regeneration'] and any(not j['shown'] for j in jobs):
                    raise ValueError('Present output before accepting it under this project policy')
            self.db.execute('UPDATE nodes SET status=? WHERE id=?', (decision, key))
            self.event('review', {'id': key, 'decision': decision, 'source': source})

    def alias(self, name, key, source):
        identifier(name)
        evidence(source)
        with self.tx():
            self.fresh(key, accepted=True)
            old = self.db.execute('SELECT node FROM aliases WHERE name=?', (name,)).fetchone()
            if old and old[0] != key:
                # Descendants, not the old node itself, need revalidation. The old
                # asset remains a valid historical record and is never overwritten.
                self.db.execute('''WITH RECURSIVE d(id) AS (
                  SELECT child FROM edges WHERE parent=?
                  UNION SELECT e.child FROM edges e JOIN d ON e.parent=d.id)
                   , a(id) AS (SELECT ? UNION SELECT e.parent FROM edges e JOIN a ON e.child=a.id),
                  kept(id) AS (SELECT ? UNION SELECT e.child FROM edges e JOIN kept ON e.parent=kept.id)
                  UPDATE nodes SET stale=1 WHERE id IN (SELECT id FROM d)
                  AND id NOT IN (SELECT id FROM a UNION SELECT id FROM kept)''', (old[0], key, key))
                # Jobs also see direct replacements, including jobs with no output yet.
                self.db.execute('''INSERT INTO events(at,type,data) VALUES (?,?,?)''',
                                (datetime.now(timezone.utc).isoformat(), 'superseded',
                                 encode({'old': old[0], 'new': key, 'alias': name})))
            self.db.execute('INSERT INTO aliases VALUES (?,?) ON CONFLICT(name) DO UPDATE SET node=excluded.node', (name, key))
            self.event('alias', {'name': name, 'id': key, 'source': source})

    def config(self):
        return json.loads(self.db.execute("SELECT value FROM meta WHERE key='config'").fetchone()[0])

    def policy(self, config, source):
        evidence(source); no_secrets(config)
        if not isinstance(config.get('show_before_regeneration'), bool):
            raise ValueError('config.show_before_regeneration must be boolean')
        with self.tx():
            self.db.execute("UPDATE meta SET value=? WHERE key='config'", (encode(config),))
            self.event('policy', {'source': source, 'config': config})

    def superseded(self):
        return {json.loads(r[0])['old'] for r in self.db.execute("SELECT data FROM events WHERE type='superseded'")}

    def refs_ready(self, job):
        spec = json.loads(job['spec'])
        outdated = self.superseded()
        for key in spec['parents']:
            if key in outdated:
                raise ValueError('Reference was superseded; prepare a reviewed new attempt: ' + key)
            self.fresh(key, accepted=True)

    def create_job(self, spec):
        for field in ('id', 'shot', 'endpoint', 'input', 'parents', 'authorization_source', 'capability_source', 'capability_checked_at'):
            if field not in spec:
                raise ValueError('Missing job field: ' + field)
        identifier(spec['id']); identifier(spec['shot']); no_secrets(spec)
        evidence(spec['authorization_source']); evidence(spec['capability_source'])
        date.fromisoformat(spec['capability_checked_at'])
        if not isinstance(spec['input'], dict) or not isinstance(spec['parents'], list) or not spec['parents']:
            raise ValueError('input must be an object; parents must include the accepted shot plan')
        with self.tx():
            self.refs_ready({'spec': encode(spec)})
            if not any(self.node(k)['kind'] in ('plan', 'shot_plan') for k in spec['parents']):
                raise ValueError('Include an accepted plan or shot_plan node among job parents')
            self.db.execute('INSERT INTO jobs(id,shot,spec) VALUES (?,?,?)', (spec['id'], spec['shot'], encode(spec)))
            for p in set(spec['parents']):
                self.db.execute('INSERT INTO job_refs VALUES (?,?)', (spec['id'], p))
            self.event('job', {'id': spec['id'], 'spec_sha256': hashlib.sha256(encode(spec).encode()).hexdigest()})

    def job(self, key):
        row = self.db.execute('SELECT * FROM jobs WHERE id=?', (key,)).fetchone()
        if row is None:
            raise ValueError('Unknown job: ' + key)
        return row

    def claim(self, key):
        with self.tx():
            job = self.job(key)
            if job['state'] != 'planned':
                raise ValueError('Job already claimed; recover its outcome, never repeat submission blindly')
            self.refs_ready(job)
            checked = date.fromisoformat(json.loads(job['spec'])['capability_checked_at'])
            age = (datetime.now(timezone.utc).date() - checked).days
            if not 0 <= age <= 7:
                raise ValueError('Capability check is future-dated or older than 7 days; reverify and create a new job spec')
            siblings = self.db.execute('SELECT * FROM jobs WHERE shot=? AND id<>?', (job['shot'], key)).fetchall()
            if any(j['state'] in ('submitting', 'submitted') for j in siblings):
                raise ValueError('Reconcile the existing in-flight attempt first')
            if self.config()['show_before_regeneration'] and any(j['output'] and not j['shown'] for j in siblings):
                raise ValueError('Show the existing output before creative regeneration')
            self.db.execute("UPDATE jobs SET state='submitting' WHERE id=?", (key,))
            self.event('claim', {'id': key})
            return json.loads(job['spec'])

    def submitted(self, key, provider_id):
        evidence(provider_id)
        with self.tx():
            j = self.job(key)
            if j['state'] == 'submitted' and j['provider_id'] == provider_id:
                return
            if j['state'] != 'submitting':
                raise ValueError('Only a claimed job can record a submission')
            self.db.execute("UPDATE jobs SET state='submitted',provider_id=? WHERE id=?", (provider_id, key))
            self.event('submitted', {'id': key, 'provider_id': provider_id})

    def fail(self, key, outcome, source):
        evidence(source)
        with self.tx():
            j = self.job(key)
            valid = {'planned': {'abandoned'}, 'submitting': {'not_submitted'},
                     'submitted': {'failed', 'canceled'}}
            if outcome not in valid.get(j['state'], set()):
                raise ValueError('Outcome incompatible with job state; unresolved/time-out is not a terminal outcome')
            self.db.execute("UPDATE jobs SET state='failed' WHERE id=?", (key,))
            self.event('failed', {'id': key, 'outcome': outcome, 'source': source})

    def complete(self, key, output_id, file):
        with self.tx():
            j = self.job(key)
            if j['state'] != 'submitted':
                raise ValueError('Record the provider ID before completion; use add for legacy imports')
            spec = json.loads(j['spec'])
            # Preserve a completed paid output even when its sources became stale.
            # Insert without parents first, then attach the immutable historical edges.
            self.put_node({'id': output_id, 'kind': 'generation', 'file': file, 'data': {'job': key}})
            for p in spec['parents']:
                self.db.execute('INSERT INTO edges VALUES (?,?)', (output_id, p))
            try:
                self.refs_ready(j)
            except ValueError:
                self.db.execute('UPDATE nodes SET stale=1 WHERE id=?', (output_id,))
            self.db.execute("UPDATE jobs SET state='completed',output=? WHERE id=?", (output_id, key))
            self.event('complete', {'id': key, 'output': output_id})

    def shown(self, key, source):
        evidence(source)
        with self.tx():
            j = self.job(key)
            if j['state'] != 'completed':
                raise ValueError('Only a completed output can be presented')
            self.db.execute('UPDATE jobs SET shown=? WHERE id=?', (source, key))
            self.event('shown', {'id': key, 'source': source})

    def resume(self):
        with self.tx():
            nodes = [dict(r) for r in self.db.execute('SELECT * FROM nodes ORDER BY created,id')]
            problems = []
            for n in nodes:
                try:
                    self.fresh(n['id'])
                except ValueError as e:
                    problems.append(str(e))
                n['data'] = json.loads(n['data'])
            jobs = []
            for row in self.db.execute('SELECT * FROM jobs ORDER BY rowid'):
                j = dict(row)
                # Payloads may contain private signed URLs; resume only emits routing metadata.
                spec = json.loads(j.pop('spec'))
                j.update(endpoint=spec['endpoint'], parents=spec['parents'])
                try:
                    self.refs_ready(row)
                    j['references_ready'] = True
                except ValueError as e:
                    j['references_ready'] = False
                    j['reference_problem'] = str(e)
                if j['state'] == 'submitting':
                    j['next_action'] = 'Recover submission outcome; do not POST again'
                elif j['state'] == 'submitted':
                    j['next_action'] = 'Poll saved provider ID and archive output'
                elif j['state'] == 'completed' and not j['shown']:
                    j['next_action'] = 'Inspect and present existing output'
                elif j['state'] == 'planned' and j['references_ready']:
                    j['next_action'] = 'Run coordinator preflight before claim'
                else:
                    j['next_action'] = 'Review decision and dependency state'
                jobs.append(j)
            return {'schema_version': VERSION, 'config': self.config(), 'nodes': nodes,
                    'aliases': dict(self.db.execute('SELECT name,node FROM aliases')),
                    'jobs': jobs, 'problems': problems,
                    'recent_events': [dict(r) for r in self.db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 25')]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('init', 'add', 'job'):
        s = sub.add_parser(name); s.add_argument('--spec' if name != 'init' else '--config', required=True)
    for name in ('claim', 'submitted', 'fail', 'shown', 'review', 'complete'):
        s = sub.add_parser(name); s.add_argument('id')
        if name in ('fail', 'shown', 'review'): s.add_argument('--evidence', required=True)
        if name == 'fail': s.add_argument('--outcome', choices=['abandoned', 'not_submitted', 'failed', 'canceled'], required=True)
        if name == 'submitted': s.add_argument('--provider-id', required=True)
        if name == 'review': s.add_argument('--decision', choices=['accepted', 'rejected'], required=True)
        if name == 'complete': s.add_argument('--output-id', required=True); s.add_argument('--file', required=True)
    s = sub.add_parser('alias'); s.add_argument('name'); s.add_argument('id'); s.add_argument('--evidence', required=True)
    s = sub.add_parser('policy'); s.add_argument('--config', required=True); s.add_argument('--evidence', required=True)
    sub.add_parser('resume')
    args = p.parse_args()
    ledger = None
    try:
        ledger = Ledger(args.project, read_json(args.config) if args.cmd == 'init' else None)
        c = args.cmd
        result = {'ok': True}
        if c == 'add': result['id'] = ledger.add(read_json(args.spec))
        elif c == 'job': ledger.create_job(read_json(args.spec))
        elif c == 'claim':
            # Never echo the API payload or signed URLs into a tool transcript.
            ledger.claim(args.id); result['id'] = args.id; result['state'] = 'submitting'
        elif c == 'submitted': ledger.submitted(args.id, args.provider_id)
        elif c == 'fail': ledger.fail(args.id, args.outcome, args.evidence)
        elif c == 'shown': ledger.shown(args.id, args.evidence)
        elif c == 'review': ledger.review(args.id, args.decision, args.evidence)
        elif c == 'complete': ledger.complete(args.id, args.output_id, args.file)
        elif c == 'alias': ledger.alias(args.name, args.id, args.evidence)
        elif c == 'policy': ledger.policy(read_json(args.config), args.evidence)
        elif c == 'resume': result = ledger.resume()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as e:
        print('Error: ' + str(e), file=sys.stderr)
        return 2
    finally:
        if ledger: ledger.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
