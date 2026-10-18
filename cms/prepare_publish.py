"""Copy the explicitly reviewed source folders into a history-preserving staging clone.

Does not read private runtime data, perform a commit or push to GitHub.
"""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'.publish-repo'
if not (TARGET/'.git').is_dir():raise RuntimeError('Clone the existing repository into .publish-repo first.')
files=[]
for pattern in ('*.md','*.txt','*.py','*.ps1','*.cmd'):
    files.extend(ROOT.glob(pattern))
files.extend(ROOT/name for name in ('.gitignore','.dockerignore','Dockerfile','requirements.txt'))
for folder in ('pages','guides','assets','cms','templates','tests','google-apps-script','docs'):
    for file in (ROOT/folder).rglob('*'):
        relative=file.relative_to(ROOT)
        if file.is_file() and not any(part in ('__pycache__','Aluva_Nest_Global_Villa','Kumbalangi_Villa') for part in relative.parts) and file.suffix!='.pyc':files.append(file)
total=0
for file in sorted(set(files)):
    relative=file.relative_to(ROOT);dest=TARGET/relative
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest);total+=file.stat().st_size
# Retire only verified obsolete files from the old flat layout in this staging checkout.
# Git preserves their history; no runtime data or unrecognised files are removed.
for folder,pattern in (('pages','*.html'),('guides','*.md')):
    for current in (ROOT/folder).glob(pattern):
        previous=TARGET/current.name
        if previous.is_file():
            if previous.read_bytes()!=current.read_bytes():
                raise RuntimeError('Old staging file differs; review before relocating: '+previous.name)
            previous.unlink()
print(f'Prepared {len(set(files))} source files ({total/1024/1024:.1f} MB). No runtime database, credentials, uploads or screenshots copied.')
