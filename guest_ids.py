"""Encrypted ID images with authenticated access; never public media."""
import io
import json
import os
import secrets
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from flask import request, jsonify, abort, send_file
from cryptography.fernet import Fernet
from PIL import Image, ImageOps, UnidentifiedImageError

RELATIONSHIPS=('Self','Spouse','Father','Mother','Son','Daughter','Brother','Sister','Grandfather','Grandmother','Grandson','Granddaughter','Uncle','Aunt','Niece','Nephew','Cousin','Friend','Legal ward','Other relative')
def local_day():return datetime.now(ZoneInfo('Asia/Kolkata')).date()

def install(app,db,admin_required,text,now,record,data_dir):
    key_path=Path(data_dir)/'private-id-key'
    supplied=os.environ.get('BRITSMAID_ID_ENCRYPTION_KEY')
    if supplied:key=supplied.encode()
    else:
        if not key_path.exists():
            with app.app_context():
                exists=db().execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='guest_documents'").fetchone()
                if exists and db().execute('SELECT 1 FROM guest_documents LIMIT 1').fetchone():raise RuntimeError('Restore the original guest ID encryption key before starting; encrypted documents already exist.')
            key_path.write_bytes(Fernet.generate_key())
        key=key_path.read_bytes().strip()
    cipher=Fernet(key)
    with app.app_context():
        db().execute('CREATE TABLE IF NOT EXISTS guest_documents(id TEXT PRIMARY KEY,booking_id TEXT NOT NULL REFERENCES bookings(id),guest_index INTEGER NOT NULL,content BLOB NOT NULL,created_at TEXT NOT NULL,delete_after TEXT NOT NULL)');db().commit()

    def prepare(data,count):
        manifest=data.get('guest_manifest',[])
        if not isinstance(manifest,list) or len(manifest)>60:raise ValueError('Enter a valid check-in guest list.')
        if not manifest:
            if request.files:raise ValueError('Provide the guest details for your ID uploads.')
            return [],[]
        if len(manifest)!=count:raise ValueError('Include every checking-in guest, including the lead guest.')
        if data.get('id_consent') is not True:raise ValueError('Confirm permission to submit guest details and private IDs.')
        guests=[];documents=[]
        for i,raw in enumerate(manifest):
            if not isinstance(raw,dict):raise ValueError('Invalid guest details.')
            name=text(raw.get('name',''),120);minor=raw.get('minor') is True;relation=raw.get('relationship')
            if not name or relation not in RELATIONSHIPS:raise ValueError('Each guest needs a name and selected relationship.')
            if i==0 and (minor or relation!='Self'):raise ValueError('The lead guest must be an adult and select Self.')
            guest=dict(name=name,minor=minor,relationship=relation,review_status='pending',review_note='')
            if minor:
                guardian=text(raw.get('guardian_name',''),120);guardian_relation=raw.get('guardian_relationship')
                if not guardian or guardian_relation not in ('Father','Mother','Legal guardian') or data.get('guardian_consent') is not True:raise ValueError('Minors need parent/legal guardian details and permission. Staff must verify these details.')
                guest.update(guardian_name=guardian,guardian_relationship=guardian_relation,guardian_permission_declared=True)
            upload=request.files.get('id_'+str(i))
            if not upload:raise ValueError('Add an ID image for each guest, or leave guest registration for later.')
            raw_bytes=upload.read(2*1024*1024+1)
            if len(raw_bytes)>2*1024*1024:raise ValueError('Each ID image must be 2 MB or smaller.')
            try:
                image=Image.open(io.BytesIO(raw_bytes))
                if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>20_000_000:raise ValueError('Use a JPEG, PNG or WebP ID image under 20 megapixels.')
                image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((2000,2000));out=io.BytesIO();image.save(out,format='JPEG',quality=90)
            except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ValueError('Upload a valid JPEG, PNG or WebP ID image.')
            identifier=secrets.token_hex(20);guest['document_id']=identifier;documents.append((identifier,i,cipher.encrypt(out.getvalue())));guests.append(guest)
        if set(request.files)-{'id_'+str(i) for i in range(count)}:raise ValueError('Unexpected guest ID upload.')
        return guests,documents

    def save(booking_id,documents,checkout):
        expiry=min(date.fromisoformat(checkout)+timedelta(days=30),local_day()+timedelta(days=30)).isoformat()
        db().executemany('INSERT INTO guest_documents VALUES(?,?,?,?,?,?)',[(identifier,booking_id,index,content,now(),expiry) for identifier,index,content in documents])

    def retention(booking_id,checkout,status):
        # Pending/cancelled documents have a short lifetime; confirmed stays retain up to checkout+30 days.
        expiry=(date.fromisoformat(checkout)+timedelta(days=30) if status=='confirmed' else local_day()+timedelta(days=30)).isoformat()
        db().execute('UPDATE guest_documents SET delete_after=? WHERE booking_id=?',(expiry,booking_id))

    def purge():
        db().execute('DELETE FROM guest_documents WHERE delete_after<?',(local_day().isoformat(),));db().commit()

    @app.get('/admin/api/guest-documents/<identifier>')
    @admin_required
    def view_document(identifier):
        row=db().execute('SELECT * FROM guest_documents WHERE id=?',(identifier,)).fetchone()
        if not row or row['delete_after']<local_day().isoformat():abort(404)
        record('guest ID viewed',row['booking_id']);db().commit()
        response=send_file(io.BytesIO(cipher.decrypt(row['content'])),mimetype='image/jpeg',download_name='guest-id.jpg',max_age=0)
        response.headers['Cache-Control']='no-store, private';response.headers['Cross-Origin-Resource-Policy']='same-origin';return response

    @app.post('/admin/api/bookings/<identifier>/guest-review')
    @admin_required
    def review_guests(identifier):
        d=request.get_json(silent=True) or {};conn=db();conn.execute('BEGIN IMMEDIATE')
        try:
            row=conn.execute('SELECT data,version FROM bookings WHERE id=?',(identifier,)).fetchone()
            if not row:abort(404)
            if d.get('version')!=row['version']:conn.rollback();return jsonify(error='This booking changed. Refresh first.'),409
            b=json.loads(row['data']);guests=b.get('guest_manifest',[]);index=d.get('guest_index');state=d.get('review_status')
            if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(guests) or state not in ('pending','verified','needs_attention'):raise ValueError('Choose a guest and review outcome.')
            if state=='verified' and not conn.execute('SELECT 1 FROM guest_documents WHERE id=? AND delete_after>=?',(guests[index].get('document_id'),local_day().isoformat())).fetchone():raise ValueError('This ID is unavailable or expired; it cannot be marked verified.')
            guests[index].update(review_status=state,review_note=text(d.get('review_note',''),1000),reviewed_at=now())
            conn.execute('UPDATE bookings SET data=?,version=version+1,updated_at=? WHERE id=?',(json.dumps(b,ensure_ascii=False),now(),identifier))
            conn.execute('INSERT INTO booking_events(booking_id,actor,action,data,created_at) VALUES(?,?,?,?,?)',(identifier,__import__('flask').session.get('email','admin'),'guest registration reviewed',json.dumps({'guest_number':index+1,'review_status':state,'note':guests[index]['review_note']}),now()))
            record('guest registration '+state,identifier);conn.commit();return jsonify(saved=True)
        except Exception:conn.rollback();raise

    @app.post('/admin/api/bookings/<identifier>/delete-ids')
    @admin_required
    def delete_ids(identifier):
        if not db().execute('SELECT 1 FROM bookings WHERE id=?',(identifier,)).fetchone():abort(404)
        db().execute('DELETE FROM guest_documents WHERE booking_id=?',(identifier,))
        db().execute('INSERT INTO booking_events(booking_id,actor,action,data,created_at) VALUES(?,?,?,?,?)',(identifier,__import__('flask').session.get('email','admin'),'guest ID images deleted','{}',now()))
        record('guest IDs deleted',identifier);db().commit();return jsonify(saved=True)

    app.extensions['britsmaid_guest_ids']=dict(prepare=prepare,save=save,retention=retention,purge=purge)
