"""Check the optional static snapshot does not advertise dynamic submission features."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
import test_cms as baseline

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cms'))
from export_static import export

class StaticSnapshotTests(unittest.TestCase):
    def test_snapshot_removes_backend_controls_and_private_assets(self):
        with contextlib.redirect_stdout(io.StringIO()):output=export('/Britsmaid-Demo-website')
        for path in output.rglob('*.html'):
            source=path.read_text(encoding='utf-8')
            self.assertNotIn('href="/feedback',source)
            self.assertNotIn('Britsmaid-Demo-website/feedback',source)
            self.assertNotIn('data-managed-booking="true"',source)
            self.assertNotIn('id="availability-calendar"',source)
            self.assertIn('noindex',source)
        villa=(output/'stays/aluva-villa/index.html').read_text(encoding='utf-8')
        self.assertIn('this static preview does not save booking requests',villa)
        self.assertIn('src="/Britsmaid-Demo-website/assets/booking.js"',villa)
        for name in ['admin.js','admin-operations.js','admin.css']:
            self.assertFalse((output/'assets'/name).exists())
        for name in ['admin','feedback','.data']:
            self.assertFalse((output/name).exists())

if __name__=='__main__':unittest.main(verbosity=2)
