"""Copy the explicitly reviewed source folders into a history-preserving staging clone.

Does not read private runtime data, perform a commit or push to GitHub.
"""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'.publish-repo'
if not (TARGET/'.git').is_dir():raise RuntimeError('Clone the existing repository into .publish-repo first.')
files=[]
for pattern in ('*.html','*.md','*.py','*.ps1'):
    files.extend(ROOT.glob(pattern))
files.extend(ROOT/name for name in ('.gitignore','.dockerignore','Dockerfile','requirements.txt'))
for folder in ('assets','cms','templates','tests','google-apps-script'):
    for file in (ROOT/folder).rglob('*'):
        relative=file.relative_to(ROOT)
        if file.is_file() and not any(part in ('__pycache__','Aluva_Nest_Global_Villa','Kumbalangi_Villa') for part in relative.parts) and file.suffix!='.pyc':files.append(file)
total=0
for file in sorted(set(files)):
    relative=file.relative_to(ROOT);dest=TARGET/relative
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest);total+=file.stat().st_size
print(f'Prepared {len(set(files))} source files ({total/1024/1024:.1f} MB). No runtime database, credentials, uploads or screenshots copied.')
