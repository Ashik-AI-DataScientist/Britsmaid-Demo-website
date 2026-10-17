"""New booking/feedback/calendar checks, with all OTA network access mocked."""
import copy
import json
import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch
import test_cms as baseline
cms=baseline.cms
import operations as ops

def ics(start,end,uid='ota-test'):
    return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\nBEGIN:VEVENT\r\nUID:'+uid+'\r\nDTSTART;VALUE=DATE:'+start.replace('-','')+'\r\nDTEND;VALUE=DATE:'+end.replace('-','')+'\r\nSUMMARY:Private guest name must not be copied\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n').encode()

class OperationsTests(unittest.TestCase):
    content=baseline.ContentTests.content
    post=baseline.ContentTests.post
    def setUp(self):
        baseline.ContentTests.setUp(self)
        with cms.app.app_context():
            for table in ['guest_documents','booking_events','public_requests','public_limits','bookings','calendar_blocks','calendar_feeds','reviews']:
                cms.db().execute('DELETE FROM '+table)
            cms.db().commit()
        self.guest=cms.app.test_client();self.public_headers={'X-CSRF-Token':self.guest.get('/api/public-session').json['csrf']}
    def public(self,path,data):return self.guest.post(path,json=data,headers=self.public_headers)
    def booking(self,offset=30,days=3):
        start=ops.today()+timedelta(days=offset)
        return dict(request_id=str(uuid.uuid4()),property_id='aluva-villa',name='Isolated test guest',phone='+919999999999',email='guest@example.invalid',check_in=start.isoformat(),check_out=(start+timedelta(days=days)).isoformat(),guests=2,notes='Test only',consent=True,website_url='')
    def bookings(self):return self.client.get('/admin/api/operations').json['bookings']
    def confirm(self,identifier,**changes):
        b=next(x for x in self.bookings() if x['id']==identifier)
        return self.post('/admin/api/bookings',dict(id=b['id'],version=b['version'],status='confirmed',payment_status=b['payment_status'],payment_url=b['payment_url'],amount=b['amount'],team_notes=b['team_notes'],availability_checked=True,**changes))
    def feed(self):
        response=self.post('/admin/api/calendars',dict(property_id='aluva-villa',name='Test Airbnb',url='https://www.airbnb.com/calendar/ical/isolated-test.ics',enabled=True))
        self.assertEqual(response.status_code,200,response.text);return response.json['id']
    def test_feedback_is_private_until_approved_and_unpublishable(self):
        d=dict(request_id=str(uuid.uuid4()),name='Test reviewer',quote='A private test review for moderation.',email='private@example.invalid',experience_type='visitor',property_id='',consent=True,publish_permission=True)
        self.assertEqual(self.guest.post('/api/feedback',json=d).status_code,403)
        response=self.public('/api/feedback',d);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.public('/api/feedback',d).json['reference'],response.json['reference'])
        reviews=self.content()['reviews'];self.assertEqual(len(reviews),1);r=reviews[0];self.assertEqual(r['status'],'draft')
        self.assertNotIn(d['quote'],self.guest.get('/').text)
        r['status']='published';self.assertEqual(self.post('/admin/api/reviews',r).status_code,200)
        page=self.guest.get('/').text;self.assertIn(d['quote'],page);self.assertNotIn(d['email'],page);self.assertIn('Website visitor feedback',page)
        self.assertEqual(self.post('/admin/api/reviews/'+r['id']+'/unpublish',{}).status_code,200)
        self.assertNotIn(d['quote'],self.guest.get('/').text)
        self.assertEqual(self.content()['reviews'][0]['contact_email'],d['email'])
        d['quote']='Changed duplicate';self.assertEqual(self.public('/api/feedback',d).status_code,409)
    def test_feedback_permission_and_contact_validation(self):
        d=dict(request_id=str(uuid.uuid4()),name='Test',quote='Feedback test only.',email='',experience_type='guest',consent=False,publish_permission=False)
        self.assertEqual(self.public('/api/feedback',d).status_code,400)
        d['consent']=True;self.assertEqual(self.public('/api/feedback',d).status_code,200)
        r=self.content()['reviews'][0];r['status']='published';self.assertEqual(self.post('/admin/api/reviews',r).status_code,400)
    def test_pending_deduplication_confirmation_overlap_and_checkout(self):
        d=self.booking();response=self.public('/api/bookings',d);self.assertEqual(response.status_code,200,response.text);first=response.json['reference']
        self.assertEqual(self.public('/api/bookings',d).json['reference'],first);self.assertEqual(len(self.bookings()),1)
        d2=self.booking();second=self.public('/api/bookings',d2).json['reference']
        b=self.bookings()[0]
        failed=self.post('/admin/api/bookings',dict(id=first,version=1,status='confirmed',payment_status='not_requested',payment_url='',amount='',team_notes='',availability_checked=False));self.assertEqual(failed.status_code,400)
        self.assertEqual(self.confirm(first).status_code,200)
        self.assertEqual(self.confirm(second).status_code,409)
        self.assertEqual(self.public('/api/bookings',self.booking()).status_code,409)
        adjacent=self.booking(offset=33);self.assertEqual(self.public('/api/bookings',adjacent).status_code,200)
        availability=self.guest.get('/api/availability/aluva-villa');self.assertNotIn(d['name'],availability.text);self.assertNotIn(d['email'],availability.text)
        b=next(x for x in self.bookings() if x['id']==first);b.update(status='cancelled');self.assertEqual(self.post('/admin/api/bookings',b).status_code,200)
        self.assertEqual(self.public('/api/bookings',self.booking()).status_code,200)
    def test_payment_requires_confirmed_booking_and_https_link(self):
        identifier=self.public('/api/bookings',self.booking()).json['reference'];b=self.bookings()[0]
        b.update(payment_status='link_ready',amount=10000,payment_url='https://payments.example.invalid/test')
        self.assertEqual(self.post('/admin/api/bookings',b).status_code,400)
        self.assertEqual(self.confirm(identifier).status_code,200)
        b=self.bookings()[0];b.update(payment_status='link_ready',amount=10000,payment_url='http://payments.example.invalid/test')
        self.assertEqual(self.post('/admin/api/bookings',b).status_code,400)
        b['payment_url']='https://payments.example.invalid/test';self.assertEqual(self.post('/admin/api/bookings',b).status_code,200)
        self.assertEqual(self.bookings()[0]['payment_status'],'link_ready')
        b=self.bookings()[0];b['payment_status']='paid';self.assertEqual(self.post('/admin/api/bookings',b).status_code,200)
        b=self.bookings()[0];b['status']='cancelled';self.assertEqual(self.post('/admin/api/bookings',b).status_code,200)
        self.assertEqual(self.bookings()[0]['payment_status'],'paid')
        self.assertEqual(self.guest.get('/api/availability/aluva-villa').json['blocks'],[])
    def test_calendar_import_failure_preserves_blocks_and_success_removes_cancelled(self):
        feed=self.feed();d=self.booking(offset=60);raw=ics(d['check_in'],d['check_out'])
        with patch.object(ops,'fetch_ics',return_value=raw):self.assertEqual(self.post('/admin/api/calendars/sync',{'id':feed}).status_code,200)
        public=self.guest.get('/api/availability/aluva-villa');self.assertEqual(len(public.json['blocks']),1);self.assertNotIn('Private guest',public.text);self.assertNotIn('airbnb.com',public.text)
        self.assertEqual(self.public('/api/bookings',d).status_code,409)
        with patch.object(ops,'fetch_ics',side_effect=ValueError('secret url must not be exposed')):self.assertEqual(self.post('/admin/api/calendars/sync',{'id':feed}).status_code,502)
        self.assertEqual(len(self.guest.get('/api/availability/aluva-villa').json['blocks']),1)
        self.assertNotIn('secret url',self.client.get('/admin/api/operations').text)
        with patch.object(ops,'fetch_ics',return_value=b'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n'):self.assertEqual(self.post('/admin/api/calendars/sync',{'id':feed}).status_code,200)
        self.assertEqual(len(self.guest.get('/api/availability/aluva-villa').json['blocks']),0)
    def test_export_direct_only_no_private_details(self):
        identifier=self.public('/api/bookings',self.booking()).json['reference'];self.confirm(identifier)
        feed=self.feed();d=self.booking(offset=70)
        with patch.object(ops,'fetch_ics',return_value=ics(d['check_in'],d['check_out'],'external-uid')):self.post('/admin/api/calendars/sync',{'id':feed})
        data=self.client.get('/admin/api/operations').json;c=next(x for x in data['calendars'] if x['property_id']=='aluva-villa');url=c['export_url'].split('localhost')[-1]
        export=self.guest.get(url);self.assertEqual(export.status_code,200);self.assertIn('SUMMARY:Reserved',export.text)
        for private in ['guest@example.invalid','Isolated test guest','external-uid','Test only']:self.assertNotIn(private,export.text)
        self.assertEqual(export.text.count('BEGIN:VEVENT'),1)
        self.assertEqual(self.guest.get('/calendar/invalid.ics').status_code,404)
    def test_calendar_parser_recurrence_transparency_and_url_safety(self):
        start=ops.today()+timedelta(days=20);raw=ics(start.isoformat(),(start+timedelta(days=1)).isoformat()).replace(b'SUMMARY:',b'RRULE:FREQ=WEEKLY;COUNT=3\r\nSUMMARY:')
        self.assertEqual(len(ops.extract_blocks(raw)),3)
        self.assertEqual(ops.extract_blocks(raw.replace(b'BEGIN:VEVENT',b'BEGIN:VEVENT\r\nSTATUS:CANCELLED')),[])
        self.assertEqual(ops.extract_blocks(raw.replace(b'BEGIN:VEVENT',b'BEGIN:VEVENT\r\nTRANSP:TRANSPARENT')),[])
        for url in ['http://airbnb.com/test.ics','https://127.0.0.1/a.ics','https://airbnb.com.evil.invalid/a.ics','file:///etc/passwd','https://user:password@airbnb.com/a.ics']:
            with self.assertRaises(ValueError):ops.validate_feed_url(url,False)
    def test_capacity_date_and_contact_checks(self):
        for key,value in [('guests',99),('check_out','2020-01-01'),('phone','9999999999')]:
            d=self.booking();d[key]=value;self.assertEqual(self.public('/api/bookings',d).status_code,400)
        d=self.booking();d['phone']='';d['email']='';self.assertEqual(self.public('/api/bookings',d).status_code,400)
        d['email']='valid@example.invalid';self.assertEqual(self.public('/api/bookings',d).status_code,200)

if __name__=='__main__':unittest.main(verbosity=2)
