from pathlib import Path
import json,hashlib,argparse,shutil
ROOT=Path(__file__).resolve().parents[1]
RELEASE='0.16.0-mobile-beta.5'
def paths():
 names=['index.html','index-mobile.js','index-mobile.pck','index.wasm','index.audio.worklet.js','index.audio.position.worklet.js','index.offline.html','index.icon.png','index.png','index.144x144.png','index.180x180.png','index.192x192.png','index.512x512.png','index.apple-touch-icon.png','index.manifest.json','index.service.worker.js','afewbuds-update.html','shared/config.js','shared/afb-api.js','shared/afb-cloud.js','shared/afb-legacy-save.js','shared/afb-updater.js','shared/afb-tracker.js','shared/style.css']
 for folder in ['account','admin']:
  names.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())
 return sorted(set(names))
def manifest():
 return {'updater_protocol':1,'release_id':RELEASE,'game_build':RELEASE,'files':[{'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name in paths() for data in [(ROOT/name).read_bytes()]]}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--output',type=Path);args=ap.parse_args()
 if not args.check:
  for name in paths():
   p=ROOT/name
   if p.suffix in ['.html','.js','.json','.css']:
    raw=p.read_bytes();p.write_bytes(raw.replace(b'\r\n',b'\n'))
 data=manifest()
 if args.check:assert data==json.loads((ROOT/'version.json').read_text(encoding='utf-8')),'Stale updater manifest'
 else:(ROOT/'version.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
 if args.output:
  out=args.output.resolve();assert out!=ROOT and ROOT not in out.parents and not out.exists();out.mkdir(parents=True)
  for name in paths()+['version.json','.nojekyll','BUILD_VERSION.txt','index-accountsync14.js','index-accountsync14.pck','shared/afb-cloud-accountsync14.js']:
   target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
 print('MANIFEST_TEST_RESULT: PASS',len(data['files']),'verified files')
