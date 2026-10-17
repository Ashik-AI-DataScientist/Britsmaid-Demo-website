"""Isolated functional checks: no real enquiries, external services or production writes."""
import copy
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
scratch_parent=Path(__file__).resolve().parents[1]/'test-results'
scratch_parent.mkdir(exist_ok=True)
scratch=tempfile.TemporaryDirectory(prefix='britsmaid-cms-test-',dir=scratch_parent)
os.environ['BRITSMAID_DATA_DIR']=scratch.name
os.environ['ADMIN_EMAIL']='test@example.invalid'
os.environ['ADMIN_PASSWORD']='Local-test-password-42!'
import app as cms
from PIL import Image

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.client=cms.app.test_client()
        page=self.client.get('/admin/login')
        self.token=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        response=self.client.post('/admin/login',data={'csrf':self.token,'email':'test@example.invalid','password':'Local-test-password-42!'})
        self.assertEqual(response.status_code,302)
        with self.client.session_transaction() as s:self.token=s['csrf']
        self.headers={'X-CSRF-Token':self.token}
    def content(self):return self.client.get('/admin/api/content').get_json()
    def post(self,url,data):return self.client.post(url,json=data,headers=self.headers)
    def test_access_and_csrf(self):
        anon=cms.app.test_client();self.assertEqual(anon.get('/admin/api/content').status_code,401)
        self.assertEqual(self.client.post('/admin/api/settings',json={}).status_code,403)
        self.assertEqual(self.client.get('/.data/local-login.txt').status_code,404)
        self.assertEqual(self.client.get('/app.py').status_code,404)
        self.assertEqual(self.client.get('/assets/../app.py').status_code,404)
        self.assertEqual(self.client.post('/admin/api/settings',json={},headers={**self.headers,'Origin':'https://evil.invalid'}).status_code,403)
    def test_seed_and_server_rendering(self):
        for path in ['/','/stay.html','/stays/aluva-villa','/stays/kumbalangi-villa']:
            page=self.client.get(path);self.assertEqual(page.status_code,200)
            self.assertIn('noindex',page.headers['X-Robots-Tag'])
        for path in ['/','/stay.html']:
            page=self.client.get(path);self.assertIn('href="/stays/aluva-villa"',page.text);self.assertIn('Divya Villa',page.text)
        self.assertEqual(self.client.get('/aluva-villa.html').status_code,301)
        self.assertIn('Rajagiri',self.client.get('/stays/aluva-villa').text)
        self.assertIn('Chinese fishing nets',self.client.get('/stays/kumbalangi-villa').text)
    def test_create_publish_archive_and_conflict(self):
        p=copy.deepcopy(self.content()['properties'][0]);p.pop('id');p['slug']='test-new-villa';p['name']='Test-only villa';p['status']='draft'
        response=self.post('/admin/api/properties',p);self.assertEqual(response.status_code,200,response.text)
        identifier=response.json['id'];self.assertEqual(self.client.get('/stays/test-new-villa').status_code,404)
        p=next(x for x in self.content()['properties'] if x['id']==identifier);p['status']='published'
        self.assertEqual(self.post('/admin/api/properties',p).status_code,200)
        self.assertIn('Test-only villa',self.client.get('/stay.html').text)
        self.assertEqual(self.post('/admin/api/properties',p).status_code,409)
        p=next(x for x in self.content()['properties'] if x['id']==identifier);p['status']='archived'
        self.assertEqual(self.post('/admin/api/properties',p).status_code,200)
        self.assertEqual(self.client.get('/stays/test-new-villa').status_code,404)
    def test_validation_and_escaping(self):
        p=copy.deepcopy(self.content()['properties'][0]);p['guests']=-2
        self.assertEqual(self.post('/admin/api/properties',p).status_code,400)
        p['guests']=8;p['description']='<script>alert("x")</script>';p['name']='<img src=x onerror=alert(1)>'
        self.assertEqual(self.post('/admin/api/properties',p).status_code,200)
        page=self.client.get('/stays/'+p['slug']).text
        self.assertNotIn('<script>alert("x")',page);self.assertIn('&lt;script&gt;',page)
        p=next(x for x in self.content()['properties'] if x['id']==p['id']);p['photos'][0]['url']='https://evil.invalid/photo.svg'
        self.assertEqual(self.post('/admin/api/properties',p).status_code,400)
    def test_reviews_permission_and_property_scope(self):
        r=dict(name='Test guest only',quote='Test-only feedback, never production.',source='Direct',source_url='',stay_month='2026-10',status='published',permission=False,property_id='kumbalangi-villa')
        self.assertEqual(self.post('/admin/api/reviews',r).status_code,400)
        r['permission']=True;response=self.post('/admin/api/reviews',r);self.assertEqual(response.status_code,200,response.text)
        self.assertIn(r['quote'],self.client.get('/').text)
        self.assertIn(r['quote'],self.client.get('/stays/kumbalangi-villa').text)
        self.assertNotIn(r['quote'],self.client.get('/stays/aluva-villa').text)
        r['id']=response.json['id'];r['status']='archived';self.post('/admin/api/reviews',r)
        self.assertNotIn(r['quote'],self.client.get('/').text)
    def test_upload_reencode_and_invalid_file(self):
        raw=io.BytesIO();Image.new('RGB',(2400,1000),'green').save(raw,'JPEG');raw.seek(0)
        response=self.client.post('/admin/api/media',data={'alt':'Test-only garden','photo':(raw,'garden.jpg')},headers=self.headers)
        self.assertEqual(response.status_code,200,response.text);url=response.json['url'];image=self.client.get(url)
        self.assertEqual(image.mimetype,'image/webp')
        with Image.open(io.BytesIO(image.data)) as photo:self.assertLessEqual(photo.width,2000);self.assertFalse(photo.getexif())
        image.close()
        response=self.client.post('/admin/api/media',data={'alt':'bad','photo':(io.BytesIO(b'<svg></svg>'),'x.svg')},headers=self.headers)
        self.assertEqual(response.status_code,400)
    def test_settings_and_seo(self):
        s=self.content()['settings'];s['site_url']='https://britsmaid.example';s['hero_title']='Thoughtfully managed.'
        self.assertEqual(self.post('/admin/api/settings',s).status_code,200)
        page=self.client.get('/');self.assertIn('Thoughtfully managed.',page.text);self.assertNotIn('X-Robots-Tag',page.headers)
        self.assertIn('https://britsmaid.example/stays/aluva-villa',self.client.get('/sitemap.xml').text)
        self.assertIn('Disallow: /admin',self.client.get('/robots.txt').text)
        self.assertIn('application/ld+json',self.client.get('/stays/aluva-villa').text)
        self.assertEqual(self.client.get('/admin').headers['Cache-Control'],'no-store')

if __name__=='__main__':unittest.main(verbosity=2)
