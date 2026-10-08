"""Small versioned JSON store, locally or in a separate GitHub data repository."""
import base64
import hashlib
import json
import os
from pathlib import Path
import threading
from urllib import request, error, parse
from .domain import empty_data, validate_data

LOCK = threading.Lock()


class StorageError(Exception):
    pass


def encoded(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')


class Store:
    def __init__(self, path='data/league.json', github=None):
        self.path = Path(path)
        self.github = github
        if github and (not github.get('repository') or not github.get('token')):
            raise StorageError('GitHub repository and token are required together.')

    def api(self, method, payload=None):
        cfg = self.github
        repo = '/'.join(parse.quote(part, safe='') for part in cfg['repository'].split('/'))
        file_path = parse.quote(cfg.get('path', 'league.json'), safe='/')
        url = f'https://api.github.com/repos/{repo}/contents/{file_path}'
        if method == 'GET':
            url += '?' + parse.urlencode({'ref': cfg.get('branch', 'main')})
        req = request.Request(url, data=json.dumps(payload).encode() if payload else None, method=method,
                              headers={'Authorization': f"Bearer {cfg['token']}", 'Accept': 'application/vnd.github+json',
                                       'Content-Type': 'application/json', 'User-Agent': 'discgolf-league'})
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.load(response)
        except error.HTTPError as exc:
            if exc.code == 404 and method == 'GET':
                raise StorageError('GitHub data file was not found. Upload your local league.json to the configured repository first.') from None
            if exc.code in (409, 422):
                raise StorageError('Data changed since this page loaded. Refresh and try again.') from None
            raise StorageError(f'GitHub storage returned HTTP {exc.code}. Check repository access and configuration.') from None
        except (error.URLError, TimeoutError):
            raise StorageError('Could not reach GitHub storage. No changes were saved.') from None

    def load(self):
        if self.github:
            obj = self.api('GET')
            if 'content' not in obj:
                raise StorageError('GitHub data file is too large for this simple store.')
            raw = base64.b64decode(obj['content'])
            version = obj['sha']
        elif self.path.exists():
            raw = self.path.read_bytes()
            version = hashlib.sha256(raw).hexdigest()
        else:
            return empty_data(), None
        try:
            return validate_data(json.loads(raw)), version
        except (ValueError, KeyError, TypeError) as exc:
            raise StorageError(f'Invalid stored data: {exc}') from None

    def save(self, data, expected_version):
        validate_data(data)
        data['revision'] = data.get('revision', 0) + 1
        raw = encoded(data)
        if self.github and len(raw) >= 1_000_000:
            raise StorageError('Data exceeds this simple GitHub store’s 1 MB limit. Export a backup and switch storage before adding more results.')
        if self.github:
            payload = {'message': f"Save league data revision {data['revision']}",
                       'content': base64.b64encode(raw).decode(), 'branch': self.github.get('branch', 'main')}
            if expected_version:
                payload['sha'] = expected_version
            self.api('PUT', payload)
        else:
            with LOCK:
                current = hashlib.sha256(self.path.read_bytes()).hexdigest() if self.path.exists() else None
                if current != expected_version:
                    raise StorageError('Data changed since this page loaded. Refresh and try again.')
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix('.tmp')
                tmp.write_bytes(raw)
                os.replace(tmp, self.path)
