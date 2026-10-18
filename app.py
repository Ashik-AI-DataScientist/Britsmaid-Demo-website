"""Britsmaid content manager. Run: python app.py (local); waitress for hosting."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if (ROOT / '.local-deps').exists():
    sys.path.insert(0, str(ROOT / '.local-deps'))
import argparse
import functools
import hashlib
import html
import io
import json
import mimetypes
import os
import re
import secrets
from review_ratings import rating_value, rating_summary
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from flask import Flask, abort, g, jsonify, redirect, render_template, render_template_string, request, send_from_directory, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image, ImageOps, UnidentifiedImageError
mimetypes.add_type('image/webp','.webp')
mimetypes.add_type('text/css','.css')
mimetypes.add_type('application/javascript','.js')

DATA = Path(os.environ.get('BRITSMAID_DATA_DIR', ROOT / '.data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'uploads').mkdir(exist_ok=True)
PRODUCTION = os.environ.get('BRITSMAID_ENV') == 'production'
secret_path = DATA / 'session-secret'
if not secret_path.exists():
    secret_path.write_text(secrets.token_hex(48), encoding='utf-8')
app = Flask(__name__, static_folder=None)
if os.environ.get('BRITSMAID_TRUST_PROXY')=='1':
    app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=0)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secret_path.read_text().strip(), MAX_CONTENT_LENGTH=24*1024*1024,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=PRODUCTION,
                  PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
Image.MAX_IMAGE_PIXELS = 40_000_000
DEFAULT_SETTINGS = dict(site_name='Britsmaid', site_url='', hero_title='Exceptional homes.', hero_emphasis='Expertly cared for.',
    hero_intro='UK-standard hospitality management for villas and holiday homes across Kerala — guest bookings, upkeep and reporting, handled end to end.',
    hero_image='/assets/villa-exterior.jpg', whatsapp='919747083777', email='contact@britsmaid.in', phone='+91 97470 83777',
    home_seo_title='Britsmaid — Villas & Property Management in Kerala', home_seo_description='Discover private villas in Aluva and Kumbalangi, Kochi. Thoughtful stays and complete property management in Kerala with Britsmaid.')

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATA / 'britsmaid.sqlite3', timeout=20)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    if 'db' in g:
        g.db.close()

def settings():
    return {**DEFAULT_SETTINGS, **{r['key']:json.loads(r['value']) for r in db().execute('SELECT * FROM settings')}}

def initialise():
    with app.app_context():
        db().executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS properties(id TEXT PRIMARY KEY,slug TEXT UNIQUE NOT NULL,data TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,property_id TEXT REFERENCES properties(id),data TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,url TEXT NOT NULL,alt TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,record_id TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS login_attempts(address TEXT PRIMARY KEY,attempts INTEGER,started REAL);
        ''')
        if not db().execute('SELECT 1 FROM admins').fetchone():
            email = os.environ.get('ADMIN_EMAIL', 'owner@britsmaid.local')
            password = os.environ.get('ADMIN_PASSWORD')
            if PRODUCTION and (not password or len(password) < 12):
                raise RuntimeError('Set ADMIN_EMAIL and ADMIN_PASSWORD (12+ characters) before first production start.')
            if not password:
                password = secrets.token_urlsafe(18)
                (DATA / 'local-login.txt').write_text(f'Local admin URL: http://127.0.0.1:8000/admin\nEmail: {email}\nPassword: {password}\n', encoding='utf-8')
            db().execute('INSERT INTO admins(email,password) VALUES(?,?)', (email.lower(), generate_password_hash(password)))
        if not db().execute('SELECT 1 FROM properties').fetchone():
            seed = json.loads((ROOT / 'cms' / 'seed.json').read_text(encoding='utf-8'))
            for p in seed:
                db().execute('INSERT INTO properties(id,slug,data,updated_at) VALUES(?,?,?,?)', (p['id'],p['slug'],json.dumps(p,ensure_ascii=False),now()))
        db().commit()

def csrf():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return session['csrf']

@app.before_request
def protect_mutations():
    if request.path.startswith('/admin') and request.method not in ('GET','HEAD','OPTIONS'):
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf')
        if not token or not secrets.compare_digest(token, session.get('csrf','')):
            abort(403, 'Your session expired. Reload the page and try again.')
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            abort(403)

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='SAMEORIGIN'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src https://script.google.com https://*.googleusercontent.com; base-uri 'self'; form-action 'self'; object-src 'none'"
    if request.path.startswith('/admin'):
        response.headers['Cache-Control']='no-store'
        response.headers['X-Robots-Tag']='noindex, nofollow'
    elif response.content_type.startswith('text/html') and not settings().get('site_url'):
        response.headers['X-Robots-Tag']='noindex, nofollow'
    return response

def admin_required(fn):
    @functools.wraps(fn)
    def wrapped(*args,**kwargs):
        if session.get('admin'):
            account=db().execute('SELECT password FROM admins WHERE id=?',(session['admin'],)).fetchone()
            tag=hashlib.sha256(account['password'].encode()).hexdigest() if account else ''
            if not tag or not secrets.compare_digest(tag,session.get('auth_tag','')): session.clear()
        if not session.get('admin'):
            if request.path.startswith('/admin/api/'):
                abort(401)
            return redirect('/admin/login')
        return fn(*args,**kwargs)
    return wrapped

def record(action, identifier):
    db().execute('INSERT INTO audit_log(actor,action,record_id,created_at) VALUES(?,?,?,?)', (session.get('email','system'),action,identifier,now()))

def property_rows(include_drafts=False):
    rows=[]
    for r in db().execute('SELECT * FROM properties ORDER BY updated_at DESC'):
        p=json.loads(r['data']);p['version']=r['version'];p['updated_at']=r['updated_at']
        if include_drafts or p['status']=='published': rows.append(p)
    return sorted(rows,key=lambda p:(not p.get('featured'),p.get('name','')))

def reviews_for(property_id=None, all_reviews=False):
    result=[]
    for row in db().execute('SELECT * FROM reviews ORDER BY updated_at DESC'):
        r=json.loads(row['data']);r['id']=row['id'];r['property_id']=row['property_id']
        try:r['rating']=rating_value(r.get('rating'))
        except ValueError:r['rating']=None
        if (all_reviews or r.get('status')=='published' and r.get('permission') is True) and (not property_id or r['property_id']==property_id and r.get('experience_type','guest')=='guest'): result.append(r)
    return result

def text(value, limit=2000):
    if not isinstance(value,str) or len(value)>limit: raise ValueError('Please shorten the text to the field limit.')
    return value.strip()

def media_url(value):
    if not isinstance(value,str) or not re.fullmatch(r'/(?:assets/[a-zA-Z0-9_./-]+|media/[a-f0-9]+\.webp)',value) or '..' in value:
        raise ValueError('Choose a photo from the media library.')
    if value.startswith('/assets/') and not (ROOT / value.lstrip('/')).is_file(): raise ValueError('Photo does not exist.')
    if value.startswith('/media/') and not (DATA / 'uploads' / value.split('/')[-1]).is_file(): raise ValueError('Photo does not exist.')
    return value

def validate_property(data, existing=None):
    p={k:text(data.get(k,''),limit) for k,limit in [('name',140),('slug',100),('location',200),('summary',400),('description',18000),('seo_title',70),('seo_description',180),('category',60)]}
    if not p['name'] or not p['location'] or not p['summary']: raise ValueError('Name, location and short description are required.')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['slug']): raise ValueError('Use a URL name with lowercase letters, numbers and hyphens.')
    if existing and p['slug']!=existing['slug']: raise ValueError('Keep the URL name unchanged to preserve existing links. Use a new listing for a different property.')
    for k,lo,hi in [('bedrooms',1,30),('beds',1,60),('bathrooms',1,30),('guests',1,60)]:
        raw=data.get(k)
        if isinstance(raw,bool) or not str(raw).isdigit() or not lo<=int(raw)<=hi: raise ValueError(f'{k.capitalize()} must be between {lo} and {hi}.')
        p[k]=int(raw)
    raw=data.get('nightly_rate','')
    if raw not in ('',None):
        try: price=float(raw)
        except (ValueError,TypeError): raise ValueError('Enter a valid nightly rate.')
        if not 0<price<=1000000: raise ValueError('Nightly rate must be positive and under 1,000,000.')
        p['nightly_rate']=round(price)
    else: p['nightly_rate']=None
    p['status']=data.get('status','draft')
    if p['status'] not in ('draft','published','archived'): raise ValueError('Choose a valid publication status.')
    p['featured']=bool(data.get('featured'))
    amenities=data.get('amenities',[])
    if not isinstance(amenities,list) or len(amenities)>30: raise ValueError('Use up to 30 amenities.')
    p['amenities']=[text(x,120) for x in amenities if isinstance(x,str) and x.strip()]
    photos=data.get('photos',[])
    if not isinstance(photos,list) or len(photos)>40: raise ValueError('Use up to 40 photos.')
    p['photos']=[{'url':media_url(x.get('url')),'alt':text(x.get('alt',''),220)} for x in photos if isinstance(x,dict)]
    if p['status']=='published' and (not p['photos'] or not p['description'] or any(not x['alt'] for x in p['photos'])):
        raise ValueError('Before publishing, add a full description and at least one photo. Give every photo descriptive alt text.')
    p['id']=existing['id'] if existing else secrets.token_hex(12)
    return p

@app.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)),400

@app.errorhandler(413)
def too_large(error):
    return jsonify(error='Upload is too large. Property photos: 12 MB each. Guest IDs: 2 MB each and under 24 MB total.'),413

@app.get('/admin/login')
def login_page():
    if session.get('admin'): return redirect('/admin')
    return render_template('login.html',csrf=csrf(),error=None)

@app.post('/admin/login')
def login():
    address=request.remote_addr or 'unknown'; stamp=time.time()
    row=db().execute('SELECT * FROM login_attempts WHERE address=?',(address,)).fetchone()
    if row and row['attempts']>=8 and stamp-row['started']<900:
        return render_template('login.html',csrf=csrf(),error='Too many attempts. Try again in 15 minutes.'),429
    user=db().execute('SELECT * FROM admins WHERE email=?',(request.form.get('email','').strip().lower(),)).fetchone()
    if not user or not check_password_hash(user['password'],request.form.get('password','')):
        attempts=row['attempts']+1 if row and stamp-row['started']<900 else 1
        started=row['started'] if attempts>1 else stamp
        db().execute('INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)',(address,attempts,started));db().commit()
        return render_template('login.html',csrf=csrf(),error='Email or password not recognised.'),401
    db().execute('DELETE FROM login_attempts WHERE address=?',(address,));db().commit()
    session.clear();session.permanent=True;session['admin']=user['id'];session['email']=user['email'];session['auth_tag']=hashlib.sha256(user['password'].encode()).hexdigest();csrf()
    return redirect('/admin')

@app.post('/admin/logout')
@admin_required
def logout():
    session.clear();return redirect('/admin/login')

@app.get('/admin')
@admin_required
def admin_page():
    return render_template('admin.html',csrf=csrf(),email=session['email'])

@app.get('/admin/api/content')
@admin_required
def content():
    return jsonify(properties=property_rows(True),reviews=reviews_for(all_reviews=True),settings=settings(),
        media=[dict(r) for r in db().execute('SELECT * FROM media ORDER BY created_at DESC')],
        activity=[dict(r) for r in db().execute('SELECT action,record_id,created_at FROM audit_log ORDER BY id DESC LIMIT 20')])

@app.post('/admin/api/properties')
@admin_required
def save_property():
    data=request.get_json(silent=True) or {};existing=None
    if data.get('id'):
        row=db().execute('SELECT * FROM properties WHERE id=?',(data['id'],)).fetchone()
        if not row: abort(404)
        existing=json.loads(row['data'])
        if data.get('version')!=row['version']: return jsonify(error='This property changed in another tab. Reload before editing.'),409
    p=validate_property(data,existing)
    try:
        if existing:
            cur=db().execute('UPDATE properties SET data=?,version=version+1,updated_at=? WHERE id=? AND version=?',(json.dumps(p,ensure_ascii=False),now(),p['id'],data['version']))
            if not cur.rowcount: db().rollback();return jsonify(error='A newer edit exists. Reload before editing.'),409
        else: db().execute('INSERT INTO properties(id,slug,data,updated_at) VALUES(?,?,?,?)',(p['id'],p['slug'],json.dumps(p,ensure_ascii=False),now()))
        record('property '+p['status'],p['id']);db().commit()
    except sqlite3.IntegrityError:
        db().rollback();return jsonify(error='That URL name is already used.'),409
    return jsonify(saved=True,id=p['id'])

@app.post('/admin/api/reviews')
@admin_required
def save_review():
    d=request.get_json(silent=True) or {}; identifier=d.get('id') or secrets.token_hex(12)
    if d.get('id') and not db().execute('SELECT 1 FROM reviews WHERE id=?',(identifier,)).fetchone(): abort(404)
    old=db().execute('SELECT data FROM reviews WHERE id=?',(identifier,)).fetchone()
    r=json.loads(old['data']) if old else {}
    r['rating']=rating_value(d.get('rating',r.get('rating')))
    r.update({k:text(d.get(k,''),limit) for k,limit in [('name',100),('quote',2000),('source',80),('source_url',500),('stay_month',7)]})
    if not r['name'] or not r['quote']: raise ValueError('Guest display name and review text are required.')
    if r['source_url'] and (urlparse(r['source_url']).scheme!='https' or not urlparse(r['source_url']).netloc): raise ValueError('Review source links must use https://.')
    if r['stay_month'] and not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',r['stay_month']): raise ValueError('Choose a valid stay month.')
    r['status']=d.get('status','draft');r['permission']=d.get('permission') is True
    if r['status'] not in ('draft','published','archived'): raise ValueError('Choose a valid publication status.')
    if r['status']=='published' and not r['permission']: raise ValueError('Confirm permission to publish before showing a guest review.')
    property_id=d.get('property_id') or None
    if property_id and not db().execute('SELECT 1 FROM properties WHERE id=?',(property_id,)).fetchone(): raise ValueError('Choose an existing property.')
    db().execute('INSERT INTO reviews(id,property_id,data,updated_at) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET property_id=excluded.property_id,data=excluded.data,updated_at=excluded.updated_at',(identifier,property_id,json.dumps(r,ensure_ascii=False),now()))
    record('review '+r['status'],identifier);db().commit();return jsonify(saved=True,id=identifier)

@app.post('/admin/api/settings')
@admin_required
def save_settings():
    d=request.get_json(silent=True) or {};s={k:text(d.get(k,str(v)),1800) for k,v in DEFAULT_SETTINGS.items()}
    if not re.fullmatch(r'\d{7,15}',s['whatsapp']): raise ValueError('WhatsApp must contain 7–15 digits including country code.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',s['email']): raise ValueError('Enter a valid email.')
    if not all(s[k] for k in ['hero_title','hero_emphasis','hero_intro','phone','site_name']): raise ValueError('Complete the required website fields.')
    if len(s['home_seo_title'])>70 or len(s['home_seo_description'])>180: raise ValueError('SEO title: up to 70 characters. Description: up to 180.')
    if s['site_url']:
        parsed=urlparse(s['site_url'])
        if parsed.scheme!='https' or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.path not in ('','/'):
            raise ValueError('Enter the final HTTPS website origin, such as https://britsmaid.in, with no path or login details.')
        s['site_url']=s['site_url'].rstrip('/')
    s['hero_image']=media_url(s['hero_image'])
    for k,v in s.items(): db().execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,json.dumps(v,ensure_ascii=False)))
    record('website settings','site');db().commit();return jsonify(saved=True)

@app.post('/admin/api/password')
@admin_required
def password():
    d=request.get_json(silent=True) or {};p=d.get('password','')
    user=db().execute('SELECT * FROM admins WHERE id=?',(session['admin'],)).fetchone()
    if not check_password_hash(user['password'],d.get('current','')): raise ValueError('Current password is incorrect.')
    if not isinstance(p,str) or not 12<=len(p)<=200: raise ValueError('Use a password of 12–200 characters.')
    db().execute('UPDATE admins SET password=? WHERE id=?',(generate_password_hash(p),session['admin']));record('password updated','admin');db().commit()
    session.clear();return jsonify(saved=True)

@app.post('/admin/api/media')
@admin_required
def upload():
    photo=request.files.get('photo');alt=text(request.form.get('alt',''),220)
    if not photo or not alt: raise ValueError('Select a photo and enter descriptive alt text.')
    try:
        with Image.open(photo.stream) as source:
            if source.format not in ('JPEG','PNG','WEBP'): raise ValueError('Upload a JPEG, PNG or WebP photo.')
            if source.width*source.height>40_000_000: raise ValueError('Choose a photograph under 40 megapixels.')
            if getattr(source,'is_animated',False): raise ValueError('Use a still property photograph.')
            image=ImageOps.exif_transpose(source).convert('RGB');image.thumbnail((2000,1600))
            identifier=secrets.token_hex(16);target=DATA/'uploads'/f'{identifier}.webp'
            image.save(target,'WEBP',quality=84,method=5)
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning): raise ValueError('The photo could not be read. Choose a smaller valid image.')
    url=f'/media/{identifier}.webp'
    db().execute('INSERT INTO media VALUES(?,?,?,?)',(identifier,url,alt,now()));record('photo uploaded',identifier);db().commit()
    return jsonify(id=identifier,url=url,alt=alt)

@app.get('/admin/backup')
@admin_required
def backup():
    response=jsonify(properties=property_rows(True),reviews=reviews_for(all_reviews=True),settings=settings(),exported_at=now())
    response.headers['Content-Disposition']='attachment; filename=britsmaid-content-backup.json';return response

@app.get('/api/properties')
def public_properties():
    return jsonify(properties=property_rows())

@app.get('/media/<filename>')
def media(filename):
    if not re.fullmatch(r'[a-f0-9]{32}\.webp',filename): abort(404)
    return send_from_directory(DATA/'uploads',filename,mimetype='image/webp',max_age=31536000)

@app.get('/assets/<path:filename>')
def assets(filename):
    if filename.split('/')[0] in ('Aluva_Nest_Global_Villa','Kumbalangi_Villa'): abort(404)
    return send_from_directory(ROOT/'assets',filename)

def description_blocks(value):
    blocks=[];paragraph=[]
    def flush():
        if paragraph: blocks.append({'kind':'p','text':' '.join(paragraph)});paragraph.clear()
    for line in value.splitlines():
        line=line.strip()
        if not line: flush()
        elif line.startswith('## '): flush();blocks.append({'kind':'h2','text':line[3:]})
        elif line.startswith('- '): flush();blocks.append({'kind':'li','text':line[2:]})
        else: paragraph.append(line)
    flush();return blocks

def shell_parts():
    source=(ROOT/'pages'/'index.html').read_text(encoding='utf-8')
    return re.search(r'<header>.*?</header>',source,re.S).group(),re.search(r'<footer.*?</footer>',source,re.S).group()

def seo_document(source,title,description,canonical,image=None,schema=None):
    source=re.sub(r'<title>.*?</title>',lambda m:'<title>'+html.escape(title)+'</title>',source,count=1,flags=re.S)
    source=re.sub(r'<meta name="description"[^>]*>',lambda m:'<meta name="description" content="'+html.escape(description,quote=True)+'">',source,count=1)
    source=re.sub(r'<link rel="canonical"[^>]*>','',source)
    tags=''
    if canonical: tags+='<link rel="canonical" href="'+html.escape(canonical,quote=True)+'">'
    for key,value in [('og:title',title),('og:description',description),('og:type','website'),('og:url',canonical),('og:image',image or '')]:
        if value: tags+='<meta property="'+key+'" content="'+html.escape(value,quote=True)+'">'
    if schema: tags+='<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')+'</script>'
    return source.replace('</head>',tags+'</head>')

def contacts(source,s):
    feedback_link='<a href="/feedback">Leave feedback</a>'
    source=source.replace('>Cookies</a>','>Cookies</a> &middot; '+feedback_link)
    source=source.replace('</body>','<script src="/assets/privacy.js"></script></body>')
    source=source.replace('</head>','<link rel="stylesheet" href="/assets/privacy.css"></head>')
    source=source.replace('<script src="/assets/guest.js">','<script src="/assets/guest-registration.js"></script><script src="/assets/guest.js">')
    source=source.replace('<script src="/assets/enquiries.js">','<script>window.BritsmaidConfig=Object.assign(window.BritsmaidConfig||{},{leadEndpoint:"/api/leads",appsScriptUrl:null});</script><script src="/assets/lead-client.js"></script><script src="/assets/enquiries.js">')
    source=source.replace('<span>BRITSMAID<small>','<span>'+html.escape(s['site_name'].upper())+'<small>')
    source=source.replace('https://wa.me/919747083777','https://wa.me/'+s['whatsapp']).replace('tel:+919747083777','tel:+'+s['whatsapp']).replace('+91 97470 83777',html.escape(s['phone'])).replace('contact@britsmaid.in',html.escape(s['email']))
    config=json.dumps({'whatsapp':s['whatsapp'],'email':s['email']}).replace('<','\\u003c')
    return source.replace('</head>',f'<script>window.BritsmaidContact={config};</script></head>')

def root_paths(source):
    # Root-relative links keep nested property URLs and media paths reliable.
    return re.sub(r'(href|src)="(?![a-z]+:|/|#)([^"?]+)([^\"]*)"',r'\1="/\2\3"',source)

def replace_collection(source, replacement):
    start=source.find('<div class="properties">')
    if start<0: return source
    depth=0
    for tag in re.finditer(r'</?div\b[^>]*>',source[start:]):
        depth+=-1 if tag.group().startswith('</') else 1
        if depth==0: return source[:start]+replacement+source[start+tag.end():]
    raise RuntimeError('The property collection markup is incomplete.')

def render_public(name):
    s=settings();source=(ROOT/'pages'/name).read_text(encoding='utf-8');props=property_rows()
    public_reviews=reviews_for()
    for p in props:p['review_summary']=rating_summary([r for r in public_reviews if r['property_id']==p['id']])
    cards=render_template('cards.html',properties=props)
    if name in ('index.html','stay.html'):
        source=replace_collection(source,cards)
        source=source.replace('Two villas under management today, with more onboarding soon.','Private homes. Personal attention. Find a stay that feels like yours.')
        if name=='stay.html':
            options=''.join('<option value="'+html.escape(p['location'],quote=True)+'">'+html.escape(p['location'])+'</option>' for p in {p['location']:p for p in props}.values())
            source=re.sub(r'(<select id="f-location">).*?</select>',lambda m:m[1]+'<option value="">All locations</option>'+options+'</select>',source,flags=re.S)
        if name=='index.html':
            source=source.replace('Exceptional homes.',html.escape(s['hero_title'])).replace('Expertly cared for.',html.escape(s['hero_emphasis'])).replace(DEFAULT_SETTINGS['hero_intro'],html.escape(s['hero_intro']))
            source=source.replace('<section class="hero home-hero no-border">','<section class="hero home-hero no-border" style="--hero-photo:url(\''+html.escape(s['hero_image'],quote=True)+'\')">')
            review_section=render_template('reviews.html',reviews=public_reviews[:6],properties=props)
            source=source.replace('<section id="management">',review_section+'<section id="management">')
            base=s['site_url'];schema={'@context':'https://schema.org','@type':'Organization','name':s['site_name'],'email':s['email'],'telephone':s['phone']}
            if base: schema.update(url=base,logo=base+'/assets/britsmaid-mark.png')
            source=seo_document(source,s['home_seo_title'],s['home_seo_description'],base+'/' if base else '',base+s['hero_image'] if base else '',schema)
    if name!='index.html':
        title=re.search(r'<title>(.*?)</title>',source,re.S).group(1);desc=re.search(r'<meta name="description" content="(.*?)"',source)
        source=seo_document(source,html.unescape(title),html.unescape(desc.group(1)) if desc else '',s['site_url']+'/'+name if s['site_url'] else '')
    return contacts(root_paths(source),s)

@app.get('/')
@app.get('/index.html')
def home(): return render_public('index.html')

@app.get('/stays/<slug>')
def villa(slug):
    p=next((x for x in property_rows() if x['slug']==slug),None)
    if not p: abort(404)
    s=settings();header,footer=shell_parts();base=s['site_url'];canonical=base+'/stays/'+slug if base else ''
    reviews=reviews_for(p['id']);p['review_summary']=rating_summary(reviews)
    source=render_template('villa.html',p=p,header=header,footer=footer,blocks=description_blocks(p['description']),reviews=reviews)
    schema={'@context':'https://schema.org','@type':'LodgingBusiness','name':p['name'],'description':p['summary'],'numberOfRooms':p['bedrooms'],'address':{'@type':'PostalAddress','addressLocality':p['location'],'addressCountry':'IN'}}
    if base: schema.update(url=canonical,image=[base+x['url'] for x in p['photos']])
    source=seo_document(source,p.get('seo_title') or p['name']+' | Britsmaid',p.get('seo_description') or p['summary'],canonical,base+p['photos'][0]['url'] if base and p['photos'] else '',schema)
    return contacts(root_paths(source),s)

@app.get('/<name>.html')
def pages(name):
    legacy={'aluva-villa':'aluva-villa','kumbalangi-villa':'kumbalangi-villa','property-detail':'aluva-villa'}
    if name in legacy: return redirect('/stays/'+legacy[name],code=301)
    if name not in ('stay','property-management','partner-with-us','sell-your-property','privacy-policy','terms','cookie-policy'): abort(404)
    return render_public(name+'.html')

@app.get('/robots.txt')
def robots():
    base=settings()['site_url'];body='User-agent: *\nDisallow: /\n' if not base else 'User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nSitemap: '+base+'/sitemap.xml\n'
    return app.response_class(body,mimetype='text/plain')

@app.get('/sitemap.xml')
def sitemap():
    base=settings()['site_url'];paths=['/','/stay.html','/property-management.html','/partner-with-us.html','/sell-your-property.html']+['/stays/'+p['slug'] for p in property_rows()]
    items=''.join('<url><loc>'+html.escape(base+p)+'</loc></url>' for p in paths) if base else ''
    return app.response_class('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+items+'</urlset>',mimetype='application/xml')

@app.get('/health')
def health():
    db().execute('SELECT 1');return jsonify(ok=True)

initialise()
from operations import install, start_calendar_worker
install(app, db, admin_required, settings, property_rows, text, now, record, csrf, shell_parts, contacts, root_paths)
from guest_ids import install as install_guest_ids
install_guest_ids(app,db,admin_required,text,now,record,DATA)

if __name__=='__main__':
    from waitress import serve
    print('Britsmaid local preview: http://127.0.0.1:8000 | Admin: /admin',flush=True)
    if (DATA/'local-login.txt').exists(): print('Local login details are in .data/local-login.txt (never publish this file).',flush=True)
    start_calendar_worker(app)
    serve(app,host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','8000')))
