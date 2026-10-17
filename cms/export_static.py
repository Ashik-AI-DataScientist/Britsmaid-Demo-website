"""Optional read-only public snapshot for GitHub Pages; never exports admin or secrets.

Run from the project root: python cms/export_static.py --base-path /Britsmaid-Demo-website
The live admin still requires a Python host. Exporting does not push to GitHub.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app as cms

def export(base_path):
    base_path=base_path.rstrip('/')
    if base_path and not re.fullmatch(r'/[A-Za-z0-9_-]+',base_path): raise ValueError('Use a repository base path such as /Britsmaid-Demo-website.')
    # A fresh output folder is used each time; no automatic recursive deletion.
    from datetime import datetime
    output=ROOT/'dist'/datetime.now().strftime('public-%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True)
    with cms.app.app_context(): props=cms.property_rows()
    paths=['/','/stay.html','/property-management.html','/partner-with-us.html','/sell-your-property.html','/privacy-policy.html','/cookie-policy.html','/terms.html']+['/stays/'+p['slug'] for p in props]
    with cms.app.test_client() as client:
        for path in paths:
            response=client.get(path)
            if response.status_code!=200: raise RuntimeError(f'Export failed: {path}')
            source=response.text
            # GitHub Pages cannot accept requests or run the availability backend.
            source=re.sub(r'<div class="feedback-inline">.*?</div>','',source,flags=re.S)
            source=re.sub(r'<a[^>]+href="/feedback(?:\?[^"]*)?"[^>]*>.*?</a>','',source,flags=re.S)
            source=source.replace('data-managed-booking="true"','')
            source=source.replace('leadEndpoint:"/api/leads"','leadEndpoint:null')
            source=source.replace('<script src="/assets/lead-client.js"></script>','')
            source=re.sub(r'<div class="field"><label for="calc-(?:owner|phone|email)">.*?</div>','',source,flags=re.S)
            source=re.sub(r'<label class="consent-row"><input type="checkbox" name="consent" required><span>I agree to Britsmaid saving.*?</label>','',source,flags=re.S)
            source=source.replace('Save &amp; enquire','Enquire').replace('Save & enquire','Enquire')
            source=source.replace('Your request is saved for our team, then your details are prepared for WhatsApp or email.', 'Your details are prepared for WhatsApp or email; this static preview does not save booking requests.')
            source=re.sub(r'<div class="availability-panel".*?</aside>','</aside>',source,flags=re.S)
            if base_path:
                source=re.sub(r'((?:href|src|action)=")/(?!/)',lambda m:m[1]+base_path+'/',source)
                source=source.replace("url('/assets/","url('"+base_path+"/assets/").replace("url('/media/","url('"+base_path+"/media/")
            target=output/('index.html' if path=='/' else path.lstrip('/') if path.endswith('.html') else path.lstrip('/')+'/index.html')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(source,encoding='utf-8')
        # Legacy links remain usable, with canonical tags supplied by the actual property page.
        for name,slug in [('aluva-villa.html','aluva-villa'),('kumbalangi-villa.html','kumbalangi-villa'),('property-detail.html','aluva-villa')]:
            original=output/'stays'/slug/'index.html'
            if original.exists():shutil.copy2(original,output/name)
        with cms.app.app_context():live=cms.settings()['site_url']
        # A repository snapshot must not compete with a separately hosted canonical website.
        for p in output.rglob('*.html'):
            s=p.read_text(encoding='utf-8').replace('</head>','<meta name="robots" content="noindex,nofollow"></head>')
            p.write_text(s,encoding='utf-8')
        (output/'robots.txt').write_text('User-agent: *\nDisallow: /\n',encoding='utf-8')
    (output/'.nojekyll').touch()
    shutil.copytree(ROOT/'assets',output/'assets',ignore=shutil.ignore_patterns('Aluva_Nest_Global_Villa','Kumbalangi_Villa','admin*.js','admin.css'))
    public_media={photo['url'] for p in props for photo in p['photos'] if photo['url'].startswith('/media/')}
    with cms.app.app_context():hero=cms.settings()['hero_image']
    if hero.startswith('/media/'):public_media.add(hero)
    (output/'media').mkdir()
    for url in public_media:shutil.copy2(cms.DATA/'uploads'/url.split('/')[-1],output/'media'/url.split('/')[-1])
    print(output)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-path',default='');args=parser.parse_args();export(args.base_path)
