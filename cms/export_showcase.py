"""Build a public browser-only showcase from seed content, never from real guest records.

Output: docs/ for GitHub Pages. The actual Flask backend remains unchanged.
"""
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def export(base='/Britsmaid-Demo-website'):
    if not re.fullmatch(r'/[A-Za-z0-9_-]+',base):raise ValueError('Use the GitHub Pages repository base path.')
    output=ROOT/'docs';output.mkdir(exist_ok=True);(ROOT/'test-results').mkdir(exist_ok=True)
    # This export must start in its own Python process so no real app/database has been loaded.
    if 'app' in sys.modules:raise RuntimeError('Run export_showcase.py in a fresh process.')
    with tempfile.TemporaryDirectory(prefix='showcase-build-',dir=ROOT/'test-results') as scratch:
        os.environ.update(BRITSMAID_DATA_DIR=scratch,ADMIN_EMAIL='showcase@example.invalid',ADMIN_PASSWORD=secrets.token_urlsafe(32),BRITSMAID_ENV='showcase',BRITSMAID_CALENDAR_WORKER='0')
        import app as cms
        from flask import render_template
        now=datetime.now(timezone.utc);stamp=now.isoformat(timespec='seconds');props=None
        with cms.app.app_context():props=cms.property_rows();settings=cms.settings()
        def convert(value):
            if isinstance(value,str) and value.startswith('/assets/'):return base+value
            if isinstance(value,list):return [convert(x) for x in value]
            if isinstance(value,dict):return {k:convert(v) for k,v in value.items()}
            return value
        guest=dict(name='Sample adult · fictional',minor=False,relationship='Self',review_status='pending',review_note='',document_available=False)
        minor=dict(name='Sample minor · fictional',minor=True,relationship='Daughter',guardian_name='Sample parent · fictional',guardian_relationship='Mother',review_status='pending',review_note='',document_available=False)
        booking=dict(id='BM-DEMO-SAMPLE',property_id=props[0]['id'],version=1,name='Sample guest · fictional',phone='',email='guest@example.invalid',check_in=(now+timedelta(days=40)).date().isoformat(),check_out=(now+timedelta(days=43)).date().isoformat(),guests=2,notes='Fictional showcase request. No reservation or payment exists.',status='requested',payment_status='not_requested',amount='',payment_url='',team_notes='',conflicts=[],guest_manifest=[guest,minor],history=[dict(actor='Public showcase',action='Sample request',data={'status':'requested'},created_at=stamp)],updated_at=stamp,created_at=stamp)
        answers=dict(owner_name='Sample owner · fictional',email='owner@example.invalid',phone='',location='Kochi · demonstration',bedrooms=4,land_cents=10,amenities=['pool','wifi'])
        from crm import calculate,STAGES
        lead=dict(id='LEAD-DEMO-SAMPLE',kind='roi',stage='new',assigned_to='',follow_up='',version=1,created_at=stamp,updated_at=stamp,data=dict(answers=answers,source_page='/',estimate=calculate(answers)),history=[dict(actor='Public showcase',action='Sample lead',note='Fictional record for demonstrating the CRM.',created_at=stamp)])
        seed=dict(version=now.isoformat(),receipts={},stages=STAGES,content=dict(properties=props,reviews=[],settings=settings,media=[],activity=[]),leads=[lead],operations=dict(bookings=[booking],calendars=[dict(property_id=p['id'],feeds=[],summary=dict(feed_count=0,configured=False,needs_review=False),export_url='Showcase only · connect after backend deployment',preview=True) for p in props]))
        paths=['/','/stay.html','/property-management.html','/partner-with-us.html','/sell-your-property.html','/privacy-policy.html','/cookie-policy.html','/terms.html','/feedback']+['/stays/'+p['slug'] for p in props]
        def write(path,source):
            source=source.replace('</head>','<meta name="robots" content="noindex,nofollow"><link rel="stylesheet" href="/assets/showcase.css"><script src="/assets/showcase-data.js"></script><script src="/assets/showcase.js"></script></head>')
            source=re.sub(r'((?:href|src|action)=")/(?!/)',lambda m:m[1]+base+'/',source)
            source=source.replace("url('/assets/","url('"+base+"/assets/").replace('url("/assets/','url("'+base+'/assets/')
            target=output/('index.html' if path=='/' else path.lstrip('/') if path.endswith('.html') else path.lstrip('/')+'/index.html');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf8')
        with cms.app.test_client() as client:
            for path in paths:
                response=client.get(path)
                if response.status_code!=200:raise RuntimeError('Cannot export '+path)
                write(path,response.text)
        with cms.app.test_request_context('/admin'):
            write('/admin',render_template('admin.html',csrf='public-showcase-not-a-live-session',email='Public showcase · no sign-in'))
        for name,slug in [('aluva-villa.html','aluva-villa'),('kumbalangi-villa.html','kumbalangi-villa'),('property-detail.html','aluva-villa')]:shutil.copy2(output/'stays'/slug/'index.html',output/name)
        shutil.copytree(ROOT/'assets',output/'assets',dirs_exist_ok=True,ignore=shutil.ignore_patterns('Aluva_Nest_Global_Villa','Kumbalangi_Villa'))
        (output/'assets/showcase-data.js').write_text('window.BritsmaidShowcaseSeed='+json.dumps(convert(seed),ensure_ascii=False).replace('<','\\u003c')+';',encoding='utf8')
        (output/'.nojekyll').touch();(output/'robots.txt').write_text('User-agent: *\nDisallow: /\n',encoding='utf8')
    print('Public showcase built in docs/. Only approved seed properties and clearly fictional sample leads/bookings are included; no real database or credentials were read.')

if __name__=='__main__':export()
