"""Moderated public feedback, manual booking operations, and private OTA calendars."""
import hashlib
import io
import ipaddress
import json
import os
import re
import secrets
import socket
import sqlite3
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo
from flask import abort, jsonify, request, session, render_template
from icalendar import Calendar, Event
import recurring_ical_events

INDIA=ZoneInfo('Asia/Kolkata')
SYNC_MINUTES=15
ALLOWED_OTA_HOSTS=('airbnb.com','booking.com','vrbo.com','homeaway.com','lodgify.com','smoobu.com','guesty.com')
_sync_lock=threading.Lock()
_worker_started=False

def today():return datetime.now(INDIA).date()

def parse_date(value):
    try:
        if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError()
        return date.fromisoformat(value)
    except (ValueError,TypeError):raise ValueError('Use a valid calendar date.')

def validate_feed_url(url,resolve=True):
    if not isinstance(url,str) or len(url)>2000:raise ValueError('Enter a valid private iCal URL.')
    p=urlparse(url)
    try:port=p.port
    except ValueError:raise ValueError('Invalid calendar address.')
    host=(p.hostname or '').lower().rstrip('.')
    extra=tuple(x.strip().lower() for x in os.environ.get('ICAL_ALLOWED_HOSTS','').split(',') if x.strip())
    if p.scheme!='https' or not host or p.username or p.password or p.fragment or port not in (None,443):raise ValueError('Use a direct HTTPS calendar URL without login credentials in the address.')
    if not any(host==suffix or host.endswith('.'+suffix) for suffix in ALLOWED_OTA_HOSTS+extra):
        raise ValueError('This calendar provider is not enabled. Ask the developer to add its exact trusted hostname to ICAL_ALLOWED_HOSTS.')
    if resolve:
        try:addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        except socket.gaierror:raise ValueError('Calendar provider could not be reached.')
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise ValueError('Calendar address must resolve to a public internet service.')
    return url

class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def fetch_ics(url):
    # Only trusted OTA domains, public addresses and direct URLs. No private-network URLs or redirects.
    validate_feed_url(url)
    opener=build_opener(NoRedirects())
    with opener.open(Request(url,headers={'User-Agent':'BritsmaidCalendar/1.0','Accept':'text/calendar'}),timeout=12) as response:
        if response.status!=200:raise ValueError('Calendar provider did not return a valid feed.')
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('Calendar feed exceeds the 2 MB import limit.')
    return raw

def extract_blocks(raw,start=None,end=None):
    if not raw.lstrip().startswith(b'BEGIN:VCALENDAR'):raise ValueError('The address did not return an iCalendar feed.')
    start=start or today()-timedelta(days=1);end=end or today()+timedelta(days=731)
    cal=Calendar.from_ical(raw)
    # Bound recurrence frequency to accommodation dates and prevent pathological expansion.
    events=cal.walk('VEVENT')
    if len(events)>5000:raise ValueError('This calendar contains too many events.')
    for item in events:
        rule=item.get('RRULE')
        if rule and str(rule.get('FREQ',[''])[0]).upper() not in ('DAILY','WEEKLY','MONTHLY','YEARLY'):
            raise ValueError('Calendar recurrence must be daily or less frequent.')
        if rule and any(len(rule.get(k,[]))>1 for k in ('BYSECOND','BYMINUTE','BYHOUR')):raise ValueError('Sub-daily calendar recurrence is not supported.')
    if sum(bool(x.get('RRULE')) for x in events)>10:raise ValueError('This feed contains too many recurring series.')
    expanded=recurring_ical_events.of(cal).between(start,end)
    if len(expanded)>10000:raise ValueError('Calendar recurrence exceeds the import limit.')
    blocks=[]
    def as_day(value):
        if isinstance(value,datetime):return value.astimezone(INDIA).date() if value.tzinfo else value.date()
        if isinstance(value,date):return value
        raise ValueError('Invalid calendar event date.')
    for event in expanded:
        if str(event.get('STATUS','')).upper()=='CANCELLED' or str(event.get('TRANSP','')).upper()=='TRANSPARENT':continue
        if not event.get('DTSTART'):raise ValueError('Calendar event is missing its start date.')
        begin=as_day(event.decoded('DTSTART'))
        if event.get('DTEND'):finish=as_day(event.decoded('DTEND'))
        elif event.get('DURATION'):finish=as_day(event.decoded('DTSTART')+event.decoded('DURATION'))
        else:finish=begin+timedelta(days=1)
        if finish<=begin:finish=begin+timedelta(days=1)
        if finish<start or begin>end:continue
        uid=hashlib.sha256((str(event.get('UID',''))+'|'+str(begin)+'|'+str(finish)).encode()).hexdigest()
        blocks.append((uid,begin.isoformat(),finish.isoformat()))
    return sorted(set(blocks))

def install(app,db,admin_required,settings,properties,text,now,record,csrf,shell_parts,contacts,root_paths):
    with app.app_context():
        db().executescript('''
        CREATE TABLE IF NOT EXISTS bookings(id TEXT PRIMARY KEY,property_id TEXT NOT NULL REFERENCES properties(id),data TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS public_requests(id TEXT PRIMARY KEY,kind TEXT NOT NULL,digest TEXT NOT NULL,receipt TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS public_limits(key TEXT PRIMARY KEY,attempts INTEGER NOT NULL,started REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS calendar_feeds(id TEXT PRIMARY KEY,property_id TEXT NOT NULL REFERENCES properties(id),name TEXT NOT NULL,url TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,last_success TEXT,last_attempt TEXT,error TEXT,version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS calendar_blocks(feed_id TEXT NOT NULL REFERENCES calendar_feeds(id),uid TEXT NOT NULL,starts TEXT NOT NULL,ends TEXT NOT NULL,PRIMARY KEY(feed_id,uid));
        CREATE TABLE IF NOT EXISTS calendar_tokens(property_id TEXT PRIMARY KEY REFERENCES properties(id),token TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS booking_events(id INTEGER PRIMARY KEY,booking_id TEXT NOT NULL REFERENCES bookings(id),actor TEXT NOT NULL,action TEXT NOT NULL,data TEXT NOT NULL,created_at TEXT NOT NULL);
        ''');db().commit()

    def one_property(identifier,public=False):
        p=next((p for p in properties(not public) if p['id']==identifier),None)
        if not p:abort(404)
        return p

    def blocks_for(identifier,exclude_booking=None):
        blocks=[]
        for r in db().execute('SELECT id,data FROM bookings WHERE property_id=?',(identifier,)):
            b=json.loads(r['data'])
            if r['id']!=exclude_booking and b['status']=='confirmed':blocks.append({'start':b['check_in'],'end':b['check_out'],'source':'Direct booking','reference':r['id']})
        for r in db().execute('SELECT b.starts,b.ends,f.name FROM calendar_blocks b JOIN calendar_feeds f ON f.id=b.feed_id WHERE f.property_id=? AND f.enabled=1',(identifier,)):
            blocks.append({'start':r['starts'],'end':r['ends'],'source':r['name']})
        return blocks

    def overlaps(identifier,start,end,exclude=None):return [x for x in blocks_for(identifier,exclude) if x['start']<end and x['end']>start]

    def feed_summary(identifier):
        rows=db().execute('SELECT * FROM calendar_feeds WHERE property_id=? AND enabled=1',(identifier,)).fetchall()
        stamp=datetime.now(timezone.utc)
        stale=[r for r in rows if not r['last_success'] or r['error'] or (stamp-datetime.fromisoformat(r['last_success'])).total_seconds()>1800]
        return {'configured':bool(rows),'needs_review':bool(stale),'last_success':min((r['last_success'] for r in rows if r['last_success']),default=None),'feed_count':len(rows)}

    def booking_rows():
        result=[]
        for r in db().execute('SELECT * FROM bookings ORDER BY updated_at DESC'):
            b=json.loads(r['data']);b.update(id=r['id'],property_id=r['property_id'],version=r['version'],updated_at=r['updated_at'])
            b['history']=[{**dict(e),'data':json.loads(e['data'])} for e in db().execute('SELECT actor,action,data,created_at FROM booking_events WHERE booking_id=? ORDER BY id',(r['id'],))]
            for guest in b.get('guest_manifest',[]):
                guest['document_available']=bool(db().execute('SELECT 1 FROM guest_documents WHERE id=? AND delete_after>=?',(guest.get('document_id'),today().isoformat())).fetchone())
            b['conflicts']=overlaps(r['property_id'],b['check_in'],b['check_out'],r['id']) if b['status'] not in ('cancelled','declined') else []
            result.append(b)
        return result

    def enforce_public():
        expected=session.get('csrf','');provided=request.headers.get('X-CSRF-Token','')
        if not expected or not secrets.compare_digest(expected,provided):abort(403)
        origin=request.headers.get('Origin')
        if origin and origin!=request.host_url.rstrip('/'):abort(403)
        if request.mimetype=='multipart/form-data' and request.path=='/api/bookings':
            raw=request.form.get('payload','')
            if len(raw)>30000:abort(400)
            try:data=json.loads(raw)
            except ValueError:abort(400)
        else:
            if not request.is_json or request.content_length and request.content_length>30000:abort(400)
            data=request.get_json(silent=True)
        if not isinstance(data,dict):abort(400)
        if data.get('website_url'):raise ValueError('Unable to accept this submission.')
        if data.get('consent') is not True:raise ValueError('Please agree to the enquiry/feedback notice before submitting.')
        try:uuid.UUID(data.get('request_id',''))
        except (ValueError,TypeError,AttributeError):raise ValueError('Reload the page and try again.')
        return data

    def contact(data,required=True):
        phone=text(data.get('phone',''),50);email=text(data.get('email',''),200)
        if required and not(phone or email):raise ValueError('Please give a mobile number or email address.')
        if phone and (not re.fullmatch(r'\+?[\d\s().-]+',phone) or not 7<=len(re.sub(r'\D','',phone))<=15):raise ValueError('Enter a mobile number with 7–15 digits and its country code.')
        if phone and not phone.startswith('+'):raise ValueError('Start your mobile number with + and its country code, such as +91.')
        if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Enter a valid email address.')
        return phone,email

    def prior(data,kind,payload):
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        row=db().execute('SELECT * FROM public_requests WHERE id=?',(data['request_id'],)).fetchone()
        if row:
            if row['kind']!=kind or row['digest']!=digest:abort(409,'This request changed. Reload the form and try again.')
            return json.loads(row['receipt']),digest
        key=hashlib.sha256((str(app.secret_key)+'|'+(request.remote_addr or '')+'|'+kind).encode()).hexdigest();stamp=time.time()
        row=db().execute('SELECT * FROM public_limits WHERE key=?',(key,)).fetchone()
        count=row['attempts']+1 if row and stamp-row['started']<3600 else 1
        if count>10:abort(429,'Too many submissions. Please contact Britsmaid directly.')
        db().execute('INSERT OR REPLACE INTO public_limits VALUES(?,?,?)',(key,count,row['started'] if count>1 else stamp))
        return None,digest

    @app.get('/api/public-session')
    def public_session():
        response=jsonify(csrf=csrf());response.headers['Cache-Control']='no-store';return response

    @app.get('/feedback')
    def feedback_page():
        header,footer=shell_parts()
        source=render_template('feedback.html',header=header,footer=footer,properties=properties(),property_id=request.args.get('property',''))
        response=app.make_response(contacts(root_paths(source),settings()));response.headers['X-Robots-Tag']='noindex';return response

    @app.post('/api/feedback')
    def feedback_submit():
        d=enforce_public();name=text(d.get('name',''),100);quote=text(d.get('quote',''),2000)
        if not name or len(quote)<10:raise ValueError('Add your name and at least 10 characters of feedback.')
        _,email=contact(d,False);experience=d.get('experience_type','visitor')
        if experience not in ('guest','visitor'):raise ValueError('Choose the feedback type.')
        property_id=d.get('property_id') or None
        if property_id:one_property(property_id,True)
        payload=dict(name=name,quote=quote,email=email,experience_type=experience,property_id=property_id,permission=d.get('publish_permission') is True)
        conn=db();conn.execute('BEGIN IMMEDIATE')
        try:
            existing,digest=prior(d,'feedback',payload)
            if existing:conn.rollback();return jsonify(existing)
            identifier=secrets.token_hex(12)
            review={**payload,'contact_email':payload['email'],'original_quote':quote,'status':'draft','source':'Guest feedback' if experience=='guest' else 'Website visitor feedback','source_url':'','stay_month':'','submitted_at':now(),'consent_version':'feedback-v1','submission_source':'website'}
            # Contact information remains in the authenticated admin record only, not public markup.
            review.pop('email',None)
            conn.execute('INSERT INTO reviews VALUES(?,?,?,?)',(identifier,property_id,json.dumps(review,ensure_ascii=False),now()))
            receipt={'accepted':True,'reference':'FB-'+identifier[:10]}
            conn.execute('INSERT INTO public_requests VALUES(?,?,?,?,?)',(d['request_id'],'feedback',digest,json.dumps(receipt),now()));record('visitor feedback received',identifier);conn.commit()
            return jsonify(receipt)
        except Exception:conn.rollback();raise

    @app.post('/admin/api/reviews/<identifier>/unpublish')
    @admin_required
    def unpublish_review(identifier):
        row=db().execute('SELECT data FROM reviews WHERE id=?',(identifier,)).fetchone()
        if not row:abort(404)
        r=json.loads(row['data']);r['status']='draft'
        db().execute('UPDATE reviews SET data=?,updated_at=? WHERE id=?',(json.dumps(r,ensure_ascii=False),now(),identifier));record('review unpublished',identifier);db().commit();return jsonify(saved=True)

    @app.post('/api/bookings')
    def booking_submit():
        d=enforce_public();p=one_property(d.get('property_id'),True);name=text(d.get('name',''),120)
        if not name:raise ValueError('Please enter your name.')
        phone,email=contact(d);begin=parse_date(d.get('check_in'));end=parse_date(d.get('check_out'))
        if begin<today() or end<=begin or (end-begin).days>180 or end>today()+timedelta(days=731):raise ValueError('Choose a future stay of 1–180 nights within the next two years.')
        guests=d.get('guests')
        if isinstance(guests,bool) or not str(guests).isdigit() or not 1<=int(guests)<=p['guests']:raise ValueError('Choose a guest count within the property capacity.')
        # Include guest metadata and file hashes in retry identity, without leaking IDs into messages.
        file_hashes={}
        for key,upload in request.files.items():
            raw=upload.read(2*1024*1024+1);upload.stream.seek(0)
            if len(raw)>2*1024*1024:raise ValueError('Each ID image must be 2 MB or smaller.')
            file_hashes[key]=hashlib.sha256(raw).hexdigest()
        manifest=d.get('guest_manifest',[])
        payload=dict(property_id=p['id'],name=name,phone=phone,email=email,check_in=begin.isoformat(),check_out=end.isoformat(),guests=int(guests),notes=text(d.get('notes',''),1500),guest_manifest=manifest,id_consent=d.get('id_consent') is True,guardian_consent=d.get('guardian_consent') is True,file_hashes=file_hashes)
        conn=db();conn.execute('BEGIN IMMEDIATE')
        try:
            existing,digest=prior(d,'booking',payload)
            if existing:conn.rollback();return jsonify(existing)
            if overlaps(p['id'],payload['check_in'],payload['check_out']):conn.rollback();return jsonify(error='These dates include a blocked night. Please choose different dates or contact our team.'),409
            identifier='BM-'+secrets.token_hex(5).upper()
            guest_list,documents=app.extensions['britsmaid_guest_ids']['prepare'](d,int(guests))
            booking={**payload,'guest_manifest':guest_list,'source':'website','status':'requested','payment_status':'not_requested','payment_url':'','amount':'','team_notes':'','created_at':now(),'consent_version':'booking-v2','availability_checked_at':None}
            booking.pop('file_hashes',None)
            conn.execute('INSERT INTO bookings(id,property_id,data,updated_at) VALUES(?,?,?,?)',(identifier,p['id'],json.dumps(booking,ensure_ascii=False),now()))
            app.extensions['britsmaid_guest_ids']['save'](identifier,documents,end.isoformat())
            conn.execute('INSERT INTO booking_events(booking_id,actor,action,data,created_at) VALUES(?,?,?,?,?)',(identifier,'website','requested',json.dumps({'status':'requested'}),now()))
            receipt={'accepted':True,'reference':identifier,'status':'requested'}
            conn.execute('INSERT INTO public_requests VALUES(?,?,?,?,?)',(d['request_id'],'booking',digest,json.dumps(receipt),now()));record('booking requested',identifier);conn.commit();return jsonify(receipt)
        except Exception:conn.rollback();raise

    @app.get('/api/availability/<identifier>')
    def availability(identifier):
        one_property(identifier,True)
        blocks=[{'start':x['start'],'end':x['end']} for x in blocks_for(identifier) if x['end']>=today().isoformat()]
        response=jsonify(blocks=blocks,calendar=feed_summary(identifier),timezone='Asia/Kolkata',checkout_exclusive=True)
        response.headers['Cache-Control']='no-store';return response

    @app.get('/admin/api/operations')
    @admin_required
    def operations_content():
        calendars=[];base=settings()['site_url'] or request.host_url.rstrip('/')
        for p in properties(True):
            row=db().execute('SELECT token FROM calendar_tokens WHERE property_id=?',(p['id'],)).fetchone()
            if not row:
                token=secrets.token_urlsafe(32);db().execute('INSERT OR IGNORE INTO calendar_tokens VALUES(?,?)',(p['id'],token))
                token=db().execute('SELECT token FROM calendar_tokens WHERE property_id=?',(p['id'],)).fetchone()['token']
            else:token=row['token']
            feeds=[dict(r) for r in db().execute('SELECT * FROM calendar_feeds WHERE property_id=?',(p['id'],))]
            for f in feeds:
                f['block_count']=db().execute('SELECT COUNT(*) FROM calendar_blocks WHERE feed_id=?',(f['id'],)).fetchone()[0]
            calendars.append(dict(property_id=p['id'],feeds=feeds,summary=feed_summary(p['id']),export_url=base+'/calendar/'+token+'.ics',preview=not bool(settings()['site_url'])))
        db().commit()
        return jsonify(bookings=booking_rows(),calendars=calendars,sync_minutes=SYNC_MINUTES)

    @app.post('/admin/api/bookings')
    @admin_required
    def save_booking():
        d=request.get_json(silent=True) or {};conn=db();conn.execute('BEGIN IMMEDIATE')
        try:
            row=conn.execute('SELECT * FROM bookings WHERE id=?',(d.get('id'),)).fetchone()
            if not row:abort(404)
            if d.get('version')!=row['version']:conn.rollback();return jsonify(error='This booking changed. Reload before editing.'),409
            b=json.loads(row['data']);status=d.get('status',b['status']);payment=d.get('payment_status',b['payment_status'])
            if status not in ('requested','confirmed','declined','cancelled') or payment not in ('not_requested','link_ready','paid','refunded'):raise ValueError('Choose a valid booking and payment status.')
            purl=text(d.get('payment_url',''),2000)
            if purl:
                u=urlparse(purl)
                if u.scheme!='https' or not u.netloc or u.username or u.password:raise ValueError('Paste a valid HTTPS payment-provider link, without login details.')
            if payment=='link_ready' and not purl:raise ValueError('Add the payment link before marking it ready.')
            if (payment=='link_ready' or payment=='paid' and b['payment_status']!='paid') and status!='confirmed':raise ValueError('Confirm availability before requesting or recording payment.')
            if status=='confirmed' and b['status']!='confirmed':
                if d.get('availability_checked') is not True:raise ValueError('Check the OTA calendars and tick the availability confirmation before confirming this request.')
                if overlaps(row['property_id'],b['check_in'],b['check_out'],row['id']):conn.rollback();return jsonify(error='These dates overlap another confirmed stay or imported OTA block.'),409
                b['availability_checked_at']=now()
            raw=d.get('amount','')
            if raw not in ('',None):
                try:amount=float(raw)
                except (ValueError,TypeError):raise ValueError('Enter a valid total in INR.')
                if not 0<amount<10000000 or not __import__('math').isfinite(amount):raise ValueError('Enter a positive total in INR.')
                amount=round(amount,2)
            else:amount=''
            if payment in ('link_ready','paid') and amount=='':raise ValueError('Enter the agreed total before requesting or recording payment.')
            b.update(status=status,payment_status=payment,payment_url=purl,amount=amount,team_notes=text(d.get('team_notes',''),3000))
            old=json.loads(row['data']);changes={key:{'before':old.get(key),'after':b.get(key)} for key in ('status','payment_status','amount','payment_url','team_notes') if old.get(key)!=b.get(key)}
            conn.execute('INSERT INTO booking_events(booking_id,actor,action,data,created_at) VALUES(?,?,?,?,?)',(row['id'],session.get('email','admin'),'booking updated',json.dumps(changes,ensure_ascii=False),now()))
            app.extensions['britsmaid_guest_ids']['retention'](row['id'],b['check_out'],status)
            conn.execute('UPDATE bookings SET data=?,version=version+1,updated_at=? WHERE id=?',(json.dumps(b,ensure_ascii=False),now(),row['id']));record('booking '+status,row['id']);conn.commit();return jsonify(saved=True)
        except Exception:conn.rollback();raise

    @app.post('/admin/api/calendars')
    @admin_required
    def save_calendar():
        d=request.get_json(silent=True) or {};pid=d.get('property_id');one_property(pid)
        name=text(d.get('name',''),100);url=text(d.get('url',''),2000)
        if not name:raise ValueError('Name the calendar, such as Airbnb or Booking.com.')
        validate_feed_url(url,False)
        existing=db().execute('SELECT * FROM calendar_feeds WHERE id=?',(d.get('id'),)).fetchone() if d.get('id') else None
        if d.get('id') and not existing:abort(404)
        if existing and existing['property_id']!=pid:raise ValueError('Calendar property cannot be changed.')
        if not existing and db().execute('SELECT COUNT(*) FROM calendar_feeds WHERE property_id=?',(pid,)).fetchone()[0]>=10:raise ValueError('Use up to 10 calendar feeds per property.')
        if existing and d.get('version')!=existing['version']:return jsonify(error='This calendar changed. Reload and retry.'),409
        if existing and url!=existing['url']:raise ValueError('Disable this calendar and add a new feed to change its address; old blocked dates are retained until you do.')
        identifier=existing['id'] if existing else secrets.token_hex(12)
        enabled=1 if d.get('enabled',True) is True else 0
        if existing:db().execute('UPDATE calendar_feeds SET name=?,enabled=?,version=version+1 WHERE id=?',(name,enabled,identifier))
        else:db().execute('INSERT INTO calendar_feeds(id,property_id,name,url,enabled) VALUES(?,?,?,?,?)',(identifier,pid,name,url,enabled))
        record('calendar configuration',identifier);db().commit();return jsonify(saved=True,id=identifier)

    def sync_one(identifier):
        row=db().execute('SELECT * FROM calendar_feeds WHERE id=? AND enabled=1',(identifier,)).fetchone()
        if not row:raise ValueError('Calendar is missing or disabled.')
        try:
            blocks=extract_blocks(fetch_ics(row['url']))
            conn=db();conn.execute('BEGIN IMMEDIATE')
            fresh=conn.execute('SELECT enabled,version FROM calendar_feeds WHERE id=?',(identifier,)).fetchone()
            if not fresh or not fresh['enabled'] or fresh['version']!=row['version']:conn.rollback();raise ValueError('Calendar settings changed during sync. Try again.')
            conn.execute('DELETE FROM calendar_blocks WHERE feed_id=?',(identifier,))
            conn.executemany('INSERT INTO calendar_blocks VALUES(?,?,?,?)',[(identifier,*b) for b in blocks])
            conn.execute('UPDATE calendar_feeds SET last_success=?,last_attempt=?,error=NULL WHERE id=?',(now(),now(),identifier));conn.commit()
            return {'synced':True,'blocks':len(blocks)}
        except Exception:
            db().rollback()
            # Do not persist URLs, guest details or provider response bodies in error messages.
            db().execute('UPDATE calendar_feeds SET last_attempt=?,error=? WHERE id=?',(now(),'Sync failed. Check the private link, provider access and feed format. Previous blocked dates are retained.',identifier));db().commit()
            return {'synced':False,'error':'Calendar sync failed. Previous blocked dates are retained.'}

    @app.post('/admin/api/calendars/sync')
    @admin_required
    def sync_calendar():
        identifier=(request.get_json(silent=True) or {}).get('id')
        if not _sync_lock.acquire(blocking=False):return jsonify(error='A calendar sync is already running. Try again shortly.'),409
        try:result=sync_one(identifier)
        finally:_sync_lock.release()
        return jsonify(result),200 if result['synced'] else 502

    @app.get('/calendar/<token>.ics')
    def export_calendar(token):
        row=db().execute('SELECT property_id FROM calendar_tokens WHERE token=?',(token,)).fetchone()
        if not row:abort(404)
        cal=Calendar();cal.add('prodid','-//Britsmaid//Direct Bookings//EN');cal.add('version','2.0');cal.add('calscale','GREGORIAN')
        # Export direct confirmed bookings only. Re-exporting imported calendars can create echo loops.
        for item in db().execute('SELECT id,data,updated_at FROM bookings WHERE property_id=?',(row['property_id'],)):
            b=json.loads(item['data'])
            if b['status']!='confirmed':continue
            event=Event();event.add('uid',item['id']+'@britsmaid');event.add('dtstamp',datetime.fromisoformat(item['updated_at']));event.add('dtstart',parse_date(b['check_in']));event.add('dtend',parse_date(b['check_out']));event.add('summary','Reserved');event.add('status','CONFIRMED');event.add('transp','OPAQUE');cal.add_component(event)
        response=app.response_class(cal.to_ical(),mimetype='text/calendar');response.headers['Cache-Control']='no-store';response.headers['X-Robots-Tag']='noindex';return response

    app.extensions['britsmaid_operations']={'sync_one':sync_one,'blocks_for':blocks_for,'db':db}
    from crm import install as install_crm
    install_crm(app,db,admin_required,text,now,record,enforce_public,prior,contact)

def start_calendar_worker(app):
    global _worker_started
    if _worker_started or os.environ.get('BRITSMAID_CALENDAR_WORKER','1')!='1':return
    _worker_started=True
    def run():
        while True:
            try:
                with app.app_context():
                    extension=app.extensions['britsmaid_operations']
                    app.extensions['britsmaid_guest_ids']['purge']()
                    ids=[r['id'] for r in extension['db']().execute('SELECT id FROM calendar_feeds WHERE enabled=1')]
                    for identifier in ids:
                        if _sync_lock.acquire(blocking=False):
                            try:extension['sync_one'](identifier)
                            finally:_sync_lock.release()
            except Exception:app.logger.warning('Calendar worker needs attention; review calendar status in the studio.')
            time.sleep(SYNC_MINUTES*60)
    threading.Thread(target=run,name='britsmaid-calendar-sync',daemon=True).start()
