"""Prepare one image and caption, safely resuming pending work."""
import json
from pathlib import Path
from art import render_quote
from seo import build_post

ROOT=Path(__file__).resolve().parent.parent
STATE=ROOT/'state/state.json'
QUOTES=ROOT/'quotes.json'
def load_state():return json.loads(STATE.read_text())
def save_state(s):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')

def main():
    s=load_state();bank=json.loads(QUOTES.read_text())
    if 'pending' not in s:
        i=int(s.get('next_quote',0))
        if i>=len(bank):
            raise SystemExit('Quote bank exhausted. Add new original quotes; no repeats will be published.')
        headline,caption=build_post(bank[i],i)
        s['pending']={'quote_index':i,'quote':bank[i],'image_path':f'posts/quote-{i+1:04d}.jpg',
                      'title':headline,'caption':caption,'instagram_post_id':None,'facebook_post_id':None}
        save_state(s)
    else:
        # Refresh only completely unpublished drafts. Never change metadata after
        # either platform has posted; that avoids partial-post inconsistency.
        pending=s['pending']
        if not pending.get('instagram_post_id') and not pending.get('facebook_post_id'):
            headline,caption=build_post(pending['quote'],int(pending['quote_index']))
            if pending.get('caption')!=caption or pending.get('title')!=headline:
                pending['title']=headline
                pending['caption']=caption
                save_state(s)
    p=s['pending'];dest=ROOT/'docs'/p['image_path']
    if not dest.exists():render_quote(p['quote'],p['quote_index'],dest)
    (ROOT/'docs/index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Unlearn The Fear</title><body style="margin:0;background:#10131b;color:#f4e7ce;font-family:sans-serif;text-align:center"><h1>Unlearn The Fear</h1><img width="400" style="max-width:95%" src="'+p['image_path']+'" alt="Quote image"></body></html>')
    print('Preview image:',p['image_path'])
if __name__=='__main__':main()
