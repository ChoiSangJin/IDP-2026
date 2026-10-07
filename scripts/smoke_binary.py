"""Launch a built executable and exercise its embedded UI + export endpoint."""
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
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
    except Exception:
        detail = traceback.format_exc()
        print("::error::"+detail.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"))
        raise
    finally:
        if os.name == "nt" and proc.poll() is None:
            # PyInstaller onefile spawns a child. Killing only its bootloader leaves
            # the child serving HTTP and holding the temporary log open on Windows.
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], check=True, capture_output=True)
        elif proc.poll() is None:
            proc.terminate()
        proc.wait(timeout=15)
