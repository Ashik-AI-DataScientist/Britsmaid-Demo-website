"""Import the approved original villa copy/photos without inventing listing data."""
import html
import json
import re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
properties=[]
for filename,name,location,baths,beds,amenities in [
 ('aluva-villa.html','Aluva Nest Global Villa','Aluva, Kerala',5,4,['Entire private villa','Air conditioning','Spacious living area','Large backyard','Long balcony']),
 ('kumbalangi-villa.html','Divya Villa, Kumbalangi','Kumbalangi, Kochi, Kerala',4,6,['Air-conditioned bedrooms','Fully equipped kitchen','Dining area','Free Wi-Fi','Private parking','Outdoor spaces'])]:
    source=(root/'pages'/filename).read_text(encoding='utf-8')
    photos=[{'url':'/'+url,'alt':html.unescape(alt)} for url,alt in re.findall(r'<img src="(assets/properties/[^"]+)" alt="([^"]*)"',source)]
    copy=source[source.find('<h2>'):source.find('<aside')].rsplit('</div>',1)[0]
    copy=re.sub(r'<h2>(.*?)</h2>',r'\n\n## \1\n',copy,flags=re.S)
    copy=copy.replace('<span>',' — ').replace('</p>','\n\n').replace('<li>','\n- ').replace('</li>','\n')
    copy=html.unescape(re.sub('<[^>]+>','',copy))
    description=re.sub(r'\n{3,}','\n\n',copy).strip()
    summary=re.search(r'<meta name="description" content="([^"]*)"',source).group(1)
    properties.append(dict(id=filename[:-5],slug=filename[:-5],name=name,location=location,bedrooms=4,beds=beds,bathrooms=baths,guests=8,category='Entire private villa',summary=html.unescape(summary),description=description,amenities=amenities,photos=photos,nightly_rate=None,status='published',featured=True,seo_title=name+' | Britsmaid Kerala',seo_description=html.unescape(summary)[:175]))
(root/'cms'/'seed.json').write_text(json.dumps(properties,ensure_ascii=False,indent=2),encoding='utf-8')
