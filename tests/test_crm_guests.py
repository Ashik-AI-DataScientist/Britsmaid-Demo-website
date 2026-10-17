"""Private identity and first-party CRM checks using fabricated images and isolated data."""
import io
import json
import unittest
import uuid
from datetime import timedelta
from PIL import Image
import test_cms as baseline
cms=baseline.cms
import operations

class CRMGuestTests(unittest.TestCase):
    post=baseline.ContentTests.post
    def setUp(self):
        baseline.ContentTests.setUp(self)
        with cms.app.app_context():
            for table in ['lead_events','leads','guest_documents','booking_events','public_requests','public_limits','bookings']:
                cms.db().execute('DELETE FROM '+table)
            cms.db().commit()
        self.guest=cms.app.test_client();self.h={'X-CSRF-Token':self.guest.get('/api/public-session').json['csrf']}
    def roi(self):return dict(request_id=str(uuid.uuid4()),consent=True,form_type='roi',source_page='/',answers=dict(owner_name='Test owner',phone='',email='owner@example.invalid',location='Kochi',bedrooms=4,land_cents=10,amenities=['pool','wifi']))
    def test_crm_capture_calculation_consent_and_private_pipeline(self):
        d=self.roi();self.assertEqual(self.guest.post('/api/leads',json=d).status_code,403)
        d['consent']=False;self.assertEqual(self.guest.post('/api/leads',json=d,headers=self.h).status_code,400);d['consent']=True
        response=self.guest.post('/api/leads',json=d,headers=self.h);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json['estimate']['nightly'],7688)
        self.assertEqual(self.guest.post('/api/leads',json=d,headers=self.h).json['reference'],response.json['reference'])
        self.assertEqual(self.guest.get('/admin/api/leads').status_code,401)
        lead=self.client.get('/admin/api/leads').json['leads'][0]
        update=dict(id=lead['id'],version=lead['version'],stage='proposal_sent',follow_up='2026-12-10T10:00',assigned_to='Test teammate',note='A test follow-up note.')
        self.assertEqual(self.post('/admin/api/leads',update).status_code,200)
        self.assertEqual(self.post('/admin/api/leads',update).status_code,409)
        lead=self.client.get('/admin/api/leads').json['leads'][0];self.assertEqual(len(lead['history']),2);self.assertEqual(lead['stage'],'proposal_sent')
        bad=self.roi();bad['answers']['email']='';self.assertEqual(self.guest.post('/api/leads',json=bad,headers=self.h).status_code,400)
    def test_all_owner_form_types_and_complete_answers(self):
        for kind in ['management','proposal','sale']:
            d=self.roi();d['form_type']=kind;d['source_page']='/partner-with-us.html';d['answers'].update(property_type='Villa',contact_method='Email',contact_time='Any time during business hours',furnished='Fully furnished',current_status='Vacant',main_goal='Earn from short-term stays',size='1000',size_unit='Square feet',title_status='Clear title — sole owner',reason='Test sale',timeline='Flexible',listed_elsewhere='No',open_to_interim_management='Yes',description='Property story retained',amenities_notes='Test amenities')
            response=self.guest.post('/api/leads',json=d,headers=self.h);self.assertEqual(response.status_code,200,response.text)
        leads=self.client.get('/admin/api/leads').json['leads'];self.assertEqual({l['kind'] for l in leads},{'management','proposal','sale'});self.assertTrue(all(l['data']['answers']['description']=='Property story retained' for l in leads))
    def booking(self):
        start=operations.today()+timedelta(days=40)
        return dict(request_id=str(uuid.uuid4()),consent=True,property_id='aluva-villa',name='Test adult',phone='',email='guest@example.invalid',check_in=start.isoformat(),check_out=(start+timedelta(days=2)).isoformat(),guests=2,notes='Test only',id_consent=True,guardian_consent=True,guest_manifest=[dict(name='Test adult',minor=False,relationship='Self'),dict(name='Test minor',minor=True,relationship='Daughter',guardian_name='Test adult',guardian_relationship='Father')])
    def image(self):
        out=io.BytesIO();Image.new('RGB',(80,50),'blue').save(out,format='JPEG');out.seek(0);return out
    def submit_booking(self,d):return self.guest.post('/api/bookings',data={'payload':json.dumps(d),'id_0':(self.image(),'test-adult.jpg'),'id_1':(self.image(),'test-minor.jpg')},headers=self.h)
    def test_ids_encrypted_private_reviewable_and_not_in_public_data(self):
        d=self.booking();response=self.submit_booking(d);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.submit_booking(d).json['reference'],response.json['reference'])
        b=self.client.get('/admin/api/operations').json['bookings'][0];g=b['guest_manifest'][1];url='/admin/api/guest-documents/'+g['document_id']
        self.assertNotEqual(self.guest.get(url).status_code,200)
        image=self.client.get(url);self.assertEqual(image.status_code,200);self.assertIn('no-store',image.headers['Cache-Control']);self.assertTrue(image.data.startswith(b'\xff\xd8'))
        with cms.app.app_context():
            row=cms.db().execute('SELECT content FROM guest_documents LIMIT 1').fetchone();self.assertFalse(bytes(row['content']).startswith(b'\xff\xd8'))
        public=self.guest.get('/api/availability/aluva-villa').text;self.assertNotIn('Test minor',public);self.assertNotIn(g['document_id'],public)
        review=dict(version=b['version'],guest_index=1,review_status='verified',review_note='Test guardian documents reviewed manually.')
        self.assertEqual(self.post('/admin/api/bookings/'+b['id']+'/guest-review',review).status_code,200)
        fresh=self.client.get('/admin/api/operations').json['bookings'][0];self.assertEqual(fresh['guest_manifest'][1]['review_status'],'verified')
        self.assertEqual(self.post('/admin/api/bookings/'+b['id']+'/delete-ids',{}).status_code,200);self.assertEqual(self.client.get(url).status_code,404)
        review['version']=fresh['version'];self.assertEqual(self.post('/admin/api/bookings/'+b['id']+'/guest-review',review).status_code,400)
    def test_minor_permission_relationship_and_invalid_image_rejected_atomically(self):
        for change in ['permission','relationship','guardian']:
            d=self.booking()
            if change=='permission':d['guardian_consent']=False
            if change=='relationship':d['guest_manifest'][1]['relationship']='Unlisted relationship'
            if change=='guardian':d['guest_manifest'][1]['guardian_name']=''
            self.assertEqual(self.submit_booking(d).status_code,400)
        d=self.booking();response=self.guest.post('/api/bookings',data={'payload':json.dumps(d),'id_0':(io.BytesIO(b'<script>bad</script>'),'id.jpg'),'id_1':(self.image(),'minor.jpg')},headers=self.h);self.assertEqual(response.status_code,400)
        with cms.app.app_context():
            self.assertEqual(cms.db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0],0);self.assertEqual(cms.db().execute('SELECT COUNT(*) FROM guest_documents').fetchone()[0],0)
    def test_expired_ids_purged_without_deleting_booking(self):
        self.assertEqual(self.submit_booking(self.booking()).status_code,200)
        with cms.app.app_context():
            cms.db().execute("UPDATE guest_documents SET delete_after='2020-01-01'");cms.db().commit();cms.app.extensions['britsmaid_guest_ids']['purge']()
            self.assertEqual(cms.db().execute('SELECT COUNT(*) FROM guest_documents').fetchone()[0],0);self.assertEqual(cms.db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0],1)

if __name__=='__main__':unittest.main(verbosity=2)
