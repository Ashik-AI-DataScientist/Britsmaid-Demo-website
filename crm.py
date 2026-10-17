"""First-party owner-lead capture and a small authenticated CRM."""
import hashlib
import json
import math
import secrets
import re
from datetime import datetime
from flask import request, jsonify, abort

STAGES=('new','contacted','assessment','proposal_sent','negotiation','won','lost')
AMENITIES={'pool':.20,'gym':.05,'garden':.04,'parking':.02,'ac':.06,'wifi':.03}

def calculate(answers):
    try:bedrooms=int(answers.get('bedrooms',0));land=float(answers.get('land_cents') or 0)
    except (ValueError,TypeError):raise ValueError('Enter valid bedrooms and land extent.')
    if isinstance(answers.get('bedrooms'),bool) or str(answers.get('bedrooms')) not in (str(bedrooms),str(float(bedrooms))) or not 1<=bedrooms<=12 or not math.isfinite(land) or not 0<=land<=100000:raise ValueError('The calculator supports 1–12 bedrooms and a valid land extent.')
    amenities=answers.get('amenities',[])
    if not isinstance(amenities,list) or any(not isinstance(a,str) or a not in AMENITIES for a in amenities):raise ValueError('Choose valid amenities.')
    premium=min(sum(AMENITIES[a] for a in set(amenities))+min(land,50)/50*.05,.45)
    rounded=lambda n:math.floor(n+.5)
    nightly=rounded((1800+bedrooms*1100)*(1+premium))
    return dict(low=rounded(nightly*30*.45/100)*100,high=rounded(nightly*30*.60/100)*100,nightly=nightly,model_version='generic-v1',currency='INR',basis='gross_booking_revenue')

def install(app,db,admin_required,text,now,record,enforce_public,prior,contact):
    with app.app_context():
        db().executescript('''CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY,kind TEXT NOT NULL,data TEXT NOT NULL,stage TEXT NOT NULL DEFAULT 'new',assigned_to TEXT NOT NULL DEFAULT '',follow_up TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS lead_events(id INTEGER PRIMARY KEY,lead_id TEXT NOT NULL REFERENCES leads(id),actor TEXT NOT NULL,action TEXT NOT NULL,note TEXT NOT NULL,created_at TEXT NOT NULL);''');db().commit()

    @app.post('/api/leads')
    def create_lead():
        d=enforce_public();kind=d.get('form_type')
        if kind not in ('roi','management','proposal','sale'):raise ValueError('Choose a valid enquiry type.')
        raw=d.get('answers')
        if not isinstance(raw,dict) or len(raw)>40:raise ValueError('Complete your property details.')
        allowed=('owner_name','phone','email','location','property_type','bedrooms','furnished','current_status','main_goal','contact_method','contact_time','land_cents','amenities','amenities_notes','built_up_sqft','description','listing_url','ready_date','proposal_notes','size','size_unit','expected_price','title_status','reason','timeline','listed_elsewhere','open_to_interim_management')
        answers={k:raw[k] if k=='amenities' else text(str(raw[k]),2000) for k in allowed if k in raw}
        if not answers.get('owner_name') or not answers.get('location'):raise ValueError('Enter your name and property location.')
        phone,email=contact(answers);answers.update(phone=phone,email=email)
        required=[] if kind=='roi' else ['property_type','contact_method','contact_time']
        required+=['size','size_unit','title_status','reason','timeline','listed_elsewhere','open_to_interim_management'] if kind=='sale' else ([] if kind=='roi' else ['bedrooms','furnished','current_status','main_goal'])
        if any(not answers.get(k) for k in required):raise ValueError('Complete the required proposal details.')
        if 'amenities' in answers and (not isinstance(answers['amenities'],list) or len(answers['amenities'])>6 or any(not isinstance(a,str) or a not in AMENITIES for a in answers['amenities'])):raise ValueError('Choose valid property amenities.')
        if kind in ('management','proposal'):
            rooms=answers['bedrooms']
            if not re.fullmatch(r'\d+',rooms) or not 1<=int(rooms)<=30:raise ValueError('Enter a whole number of bedrooms between 1 and 30.')
            for field,maximum in (('land_cents',100000),('built_up_sqft',1000000)):
                if answers.get(field):
                    try:number=float(answers[field])
                    except ValueError:raise ValueError('Enter a valid land extent or built-up area.')
                    if not math.isfinite(number) or not 0<=number<=maximum:raise ValueError('Enter a valid land extent or built-up area.')
        choices={'property_type':('Villa','Independent house','Apartment','Homestay','Land','Other'),'furnished':('Fully furnished','Partly furnished','Unfurnished'),'current_status':('Vacant','Self-managed','With another manager','Listed on Airbnb / Booking.com'),'main_goal':('Earn from short-term stays','Find a long-term tenant','Full property care','Explore my options'),'contact_method':('Email','WhatsApp','Phone call'),'contact_time':('Morning (9am–12pm IST)','Afternoon (12pm–5pm IST)','Evening (5pm–8pm IST)','Any time during business hours'),'listed_elsewhere':('Yes','No'),'open_to_interim_management':('Yes','No')}
        if any(answers.get(k) and answers[k] not in options for k,options in choices.items()):raise ValueError('Choose one of the available form options.')
        if kind=='sale':
            for field in ('size','expected_price'):
                if answers.get(field):
                    try:value=float(answers[field])
                    except ValueError:raise ValueError('Enter a valid property size or price.')
                    if not math.isfinite(value) or value<0 or field=='size' and value==0:raise ValueError('Enter a positive property size and a valid optional price.')
        if answers.get('contact_method')=='Email' and not email:raise ValueError('Provide an email for your selected contact method.')
        if answers.get('contact_method') in ('WhatsApp','Phone call') and not phone:raise ValueError('Provide a phone number for your selected contact method.')
        estimate=None
        if kind=='roi':estimate=calculate(answers)
        elif kind in ('management','proposal'):
            try:estimate=calculate(answers)
            except ValueError:pass
        source=text(d.get('source_page',''),300)
        if not source.startswith('/') or source.startswith('//'):raise ValueError('Invalid enquiry page.')
        payload=dict(answers=answers,source_page=source,form_type=kind,estimate=estimate,consent_version='owner-lead-v1')
        conn=db();conn.execute('BEGIN IMMEDIATE')
        try:
            existing,digest=prior(d,'lead',payload)
            if existing:conn.rollback();return jsonify(existing)
            identifier='LEAD-'+secrets.token_hex(5).upper();stamp=now()
            conn.execute('INSERT INTO leads(id,kind,data,created_at,updated_at) VALUES(?,?,?,?,?)',(identifier,kind,json.dumps(payload,ensure_ascii=False),stamp,stamp))
            conn.execute('INSERT INTO lead_events(lead_id,actor,action,note,created_at) VALUES(?,?,?,?,?)',(identifier,'website','received','Enquiry saved with consent.',stamp))
            receipt=dict(accepted=True,submission_id=identifier,reference=identifier,estimate=estimate)
            conn.execute('INSERT INTO public_requests VALUES(?,?,?,?,?)',(d['request_id'],'lead',digest,json.dumps(receipt),stamp));record('lead received',identifier);conn.commit();return jsonify(receipt)
        except Exception:conn.rollback();raise

    @app.get('/admin/api/leads')
    @admin_required
    def lead_list():
        result=[]
        for row in db().execute('SELECT * FROM leads ORDER BY updated_at DESC'):
            lead=dict(row);lead['data']=json.loads(lead['data']);lead['history']=[dict(x) for x in db().execute('SELECT actor,action,note,created_at FROM lead_events WHERE lead_id=? ORDER BY id',(row['id'],))];result.append(lead)
        return jsonify(leads=result,stages=STAGES)

    @app.post('/admin/api/leads')
    @admin_required
    def update_lead():
        d=request.get_json(silent=True) or {};stage=d.get('stage');follow=text(d.get('follow_up',''),40);assigned=text(d.get('assigned_to',''),100);note=text(d.get('note',''),3000)
        if stage not in STAGES:raise ValueError('Choose a valid lead stage.')
        if follow:
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',follow):raise ValueError()
                datetime.fromisoformat(follow)
            except ValueError:raise ValueError('Choose a valid follow-up time.')
        conn=db();conn.execute('BEGIN IMMEDIATE')
        try:
            row=conn.execute('SELECT * FROM leads WHERE id=?',(d.get('id'),)).fetchone()
            if not row:abort(404)
            if d.get('version')!=row['version']:conn.rollback();return jsonify(error='This lead changed. Refresh before saving.'),409
            conn.execute('UPDATE leads SET stage=?,assigned_to=?,follow_up=?,version=version+1,updated_at=? WHERE id=?',(stage,assigned,follow,now(),row['id']))
            action='Stage '+row['stage']+' → '+stage if stage!=row['stage'] else 'Lead updated'
            conn.execute('INSERT INTO lead_events(lead_id,actor,action,note,created_at) VALUES(?,?,?,?,?)',(row['id'],__import__('flask').session.get('email','admin'),action,note,now()));record('lead updated',row['id']);conn.commit();return jsonify(saved=True)
        except Exception:conn.rollback();raise
