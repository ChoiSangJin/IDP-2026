"""Launch a built executable and exercise its embedded UI + export endpoint."""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

binary = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as temp:
    log = Path(temp)/"startup.log"
    with log.open("w") as output:
        proc = subprocess.Popen([binary, "serve", "--port", "0", "--no-browser"], stdout=output, stderr=output)
    try:
        url = None
        for _ in range(120):
            text = log.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if "http://127.0.0.1:" in line:
                    url = line[line.index("http://127.0.0.1:"):].strip()
            if url:
                break
            if proc.poll() is not None:
                raise RuntimeError(text)
            time.sleep(0.25)
        if not url:
            raise RuntimeError("No startup URL")
        base, fragment = url.split("#token=")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        assert b"Auto-DD" in opener.open(base).read()
        assert b"connection-form" in opener.open(base).read()
        assert b"drawDiagram" in opener.open(base+"assets/app.js").read()
        request = urllib.request.Request(base+"api/sample", headers={"X-Auto-DD-Token": fragment})
        data = json.load(opener.open(request))
        assert len(data["tables"]) == 3
        request = urllib.request.Request(base+"api/export/xlsx", data=json.dumps(data).encode(), headers={"X-Auto-DD-Token":fragment,"Content-Type":"application/json"})
        assert opener.open(request).read().startswith(b"PK")
        print("Frozen executable: UI, embedded assets, metadata and Excel export passed")
    finally:
        proc.terminate()
        proc.wait(timeout=15)
