"""Rebuild and validate a requested mobile release before updating public artifacts."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[1]
request=root/'tools/source_release_request.json'
config=json.loads(request.read_text())
source=Path(sys.argv[1]).resolve();godot=Path(sys.argv[2]).resolve()
assert re.fullmatch(r'[0-9a-f]{40}',config['source_commit'])
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==config['source_commit']
with tempfile.TemporaryDirectory(prefix='afb-public-candidate-') as temp:
 out=Path(temp)/'build'
 subprocess.run([sys.executable,str(source/'tools/mobile_3d_movement/build.py'),'--output-dir',str(out)],check=True,cwd=source)
 subprocess.run([str(godot),'--headless','--path',str(out/'candidate'),'--editor','--import','--quit'],check=True)
 scripts=re.findall(r'--script "\$\{GITHUB_WORKSPACE\}/([^\"]+)"',(source/'.github/workflows/mobile-3d-preview.yml').read_text())
 for script in dict.fromkeys(scripts):
  with tempfile.TemporaryDirectory(prefix='afb-release-test-') as data:
   result=subprocess.run([str(godot),'--headless','--path',str(out/'candidate'),'--script',str(source/script)],env=dict(os.environ,XDG_DATA_HOME=data),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
   print(script,flush=True);print(result.stdout,flush=True)
   assert result.returncode==0 and 'RESULT: PASS' in result.stdout and 'SCRIPT ERROR' not in result.stdout and 'ERROR:' not in result.stdout,script
 shutil.copy2(out/'candidate.pck',root/'index-mobile.pck')
previous=json.loads((root/'RELEASE_INTEGRITY.json').read_text());old=previous['release_id'];release=config['release_id']
for name in ['index.html','tools/manifest.py','BUILD_VERSION.txt','README.md']:
 path=root/name;path.write_text(path.read_text().replace(old,release))
pack=(root/'index-mobile.pck').read_bytes()
previous.update(release_id=release,source_commit=config['source_commit'],source_branch='fix/property-operations',main_pack_sha256=hashlib.sha256(pack).hexdigest(),main_pack_bytes=len(pack),previous_public_commit=os.environ.get('GITHUB_SHA','local-validation'),previous_public_release=old,source_ci_run=os.environ.get('GITHUB_RUN_ID','local-validation'))
(root/'RELEASE_INTEGRITY.json').write_text(json.dumps(previous,indent=2)+'\n')
(root/'RELEASE_NOTES.md').write_text(config['notes'])
readme=root/'README.md'
s=readme.read_text();start=s.find('The full game pack is byte-identical');end=s.find('`RELEASE_INTEGRITY.json`',start)
if start>=0 and end>start:s=s[:start]+'The game pack is rebuilt from its pinned source and passes the mobile gameplay and property-isolation checks before publication. '+s[end:]
readme.write_text(s)
subprocess.run([sys.executable,str(root/'tools/manifest.py')],check=True,cwd=root)
request.unlink()
print('SOURCE_RELEASE_BUILD: PASS',release)
