"""Create a consistent SQLite+media backup without copying live WAL files."""
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as cms

folder=cms.DATA/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
folder.mkdir(parents=True)
target=folder/'britsmaid.sqlite3'
with sqlite3.connect(cms.DATA/'britsmaid.sqlite3') as source, sqlite3.connect(target) as backup:
    source.backup(backup)
archive=folder/'britsmaid-backup.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(target,'britsmaid.sqlite3')
    if (cms.DATA/'private-id-key').exists():z.write(cms.DATA/'private-id-key','private-id-key')
    for photo in (cms.DATA/'uploads').glob('*.webp'):z.write(photo,'uploads/'+photo.name)
print(archive)
