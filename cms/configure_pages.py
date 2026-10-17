"""Read/configure this repository's Pages source using the existing Git credential helper.

Credentials are used only in memory for GitHub's API and never printed or saved.
Run with --apply only after committing/pushing the generated docs/ showcase.
"""
import json
import subprocess
import sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError

repo='Ashik-AI-DataScientist/Britsmaid-Demo-website'
credential=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,check=True)
fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
token=fields.get('password')
if not token:raise SystemExit('Sign in with Git Credential Manager first.')
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'BritsmaidPublisher'}
url='https://api.github.com/repos/'+repo+'/pages'
try:
    if '--apply' in sys.argv:
        req=Request(url,data=json.dumps({'source':{'branch':'main','path':'/docs'}}).encode(),headers={**headers,'Content-Type':'application/json'},method='PUT')
        with urlopen(req,timeout=30) as response:response.read()
    with urlopen(Request(url,headers=headers),timeout=30) as response:data=json.load(response)
    print(json.dumps({k:data.get(k) for k in ('html_url','status','build_type','source')},indent=2))
except HTTPError as error:raise SystemExit('GitHub Pages API returned HTTP '+str(error.code)+'. Configure main /docs in repository Settings → Pages if this account lacks API access.')
