"""Expose only the anonymous play-counter port. Refresh the public address on reconnect."""
import re,shutil,subprocess,time
from village import upload

def run(cfg):
    exe=shutil.which('cloudflared')
    if not exe:return
    import tempfile
    from pathlib import Path
    config=Path(tempfile.gettempdir())/'bracken-play-counter.yml'
    config.write_text('protocol: http2\n',encoding='ascii')
    while True:
        proc=subprocess.Popen([exe,'tunnel','--config',str(config),'--protocol','http2','--url','http://127.0.0.1:8799','--no-autoupdate'],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            for line in proc.stdout:
                match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com\b',line)
                if match:
                    upload(cfg['repo'],'counter.json',{'url':match[0]})
        finally:
            proc.terminate();proc.wait()
        time.sleep(60)
