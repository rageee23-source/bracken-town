"""Run the Windows recovery check without creating a console."""
from pathlib import Path
import subprocess

if __name__ == '__main__':
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                    '-File',str(Path(__file__).with_name('Open-Town.ps1')),'-Headless'],
                   creationflags=subprocess.CREATE_NO_WINDOW, check=True)
