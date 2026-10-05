"""Live local HTTP smoke test; no host-agent effectiveness claim."""
from pathlib import Path
import json
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from start_app import choose_python, APP_ROOT

def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([str(choose_python(False)), '-m','uvicorn','app.main:app',
        '--host','127.0.0.1','--port',str(port)], cwd=APP_ROOT,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    base=f'http://127.0.0.1:{port}'
    records=[]
    try:
        for _ in range(50):
            try:
                with urllib.request.urlopen(base+'/health',timeout=1) as response:
                    assert response.status==200
                break
            except (urllib.error.URLError,ConnectionError):
                time.sleep(.1)
        else: raise RuntimeError('Local HTTP test server did not start')
        boundary='rtk-smoke-test'
        content=(f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="sample.txt"\r\n'
                 'Content-Type: text/plain\r\n\r\nTLIVE=100\n0\t4\n1\t5\n'
                 f'\r\n--{boundary}--\r\n').encode()
        req=urllib.request.Request(base+'/api/inspect',data=content,
            headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
        with urllib.request.urlopen(req) as response:
            body=json.loads(response.read())
            assert body['files'][0]['live_time_s']==100
            records.append({'case':'multipart-inspect','status':response.status})
        req=urllib.request.Request(base+'/api/inspect',data=b'x',headers={'Content-Length':str(65*1024*1024)})
        try: urllib.request.urlopen(req,timeout=3)
        except urllib.error.HTTPError as exc:
            assert exc.code==413, exc.code
            records.append({'case':'request-size-limit','status':exc.code})
        else: raise AssertionError('Oversize request was not blocked')
        print(json.dumps({'status':'passed','checks':records}))
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return 0

if __name__=='__main__':
    raise SystemExit(main())
