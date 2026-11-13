"""Post a prepared image to Instagram and Facebook using a Page access token."""
import os,time,subprocess,requests
from urllib.parse import urljoin
from prepare import ROOT,load_state,save_state

def graph(method,path,params):
    ver=os.getenv('META_GRAPH_VERSION','v27.0').strip()
    r=requests.request(method,'https://graph.facebook.com/'+ver+'/'+path,
                       params=params if method=='GET' else None,
                       data=params if method=='POST' else None,timeout=35)
    try:body=r.json()
    except ValueError:raise RuntimeError('Meta returned non-JSON HTTP '+str(r.status_code))
    if not r.ok or 'error' in body:
        err=body.get('error',{})
        raise RuntimeError('Meta error: code='+str(err.get('code'))+' '+str(err.get('message',''))[:300])
    return body

def checkpoint(message,state):
    save_state(state)
    subprocess.run(['git','add','state/state.json'],cwd=ROOT,check=True)
    changed=subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT)
    if changed.returncode:
        subprocess.run(['git','-c','user.name=github-actions[bot]',
                        '-c','user.email=41898282+github-actions[bot]@users.noreply.github.com',
                        'commit','-m',message],cwd=ROOT,check=True)
        subprocess.run(['git','push'],cwd=ROOT,check=True)

def main():
    state=load_state();post=state.get('pending')
    if not post:
        print('Nothing pending.');return
    base=os.getenv('PAGES_BASE_URL','').strip()
    if not base.startswith('https://') or not base.endswith('/'):
        raise RuntimeError('Set PAGES_BASE_URL ending in / under Actions variables')
    image=urljoin(base,post['image_path'])
    page=os.getenv('META_PAGE_ID','').strip()
    ig=os.getenv('META_IG_USER_ID','').strip()
    token=os.getenv('META_PAGE_TOKEN','').strip()
    if not (page and ig and token):raise RuntimeError('Missing META_PAGE_ID, META_IG_USER_ID or META_PAGE_TOKEN')
    accessible=False
    for _ in range(16):
        try:
            r=requests.get(image,timeout=12,headers={'Cache-Control':'no-cache'})
            if r.ok and 'image/jpeg' in r.headers.get('Content-Type','').lower() and len(r.content)>10000:
                accessible=True;break
        except requests.RequestException:pass
        time.sleep(8)
    if not accessible:raise RuntimeError('Image is not accessible as public JPEG: '+image)
    if not post.get('instagram_post_id'):
        c=graph('POST',ig+'/media',{'image_url':image,'caption':post['caption'],'access_token':token})
        ready=False
        for _ in range(16):
            status=graph('GET',c['id'],{'fields':'status_code','access_token':token}).get('status_code')
            if status=='FINISHED':ready=True;break
            if status in ('ERROR','EXPIRED'):raise RuntimeError('Instagram processing failed: '+status)
            time.sleep(5)
        if not ready:raise RuntimeError('Instagram image not ready; retry carefully')
        out=graph('POST',ig+'/media_publish',{'creation_id':c['id'],'access_token':token})
        post['instagram_post_id']=out['id'];checkpoint('Record Instagram post',state)
    if not post.get('facebook_post_id'):
        out=graph('POST',page+'/photos',{'url':image,'caption':post['caption'],
                                        'published':'true','access_token':token})
        post['facebook_post_id']=out.get('post_id') or out['id']
        checkpoint('Record Facebook post',state)
    if post['instagram_post_id'] and post['facebook_post_id']:
        state.setdefault('history',[]).append({'quote_index':post['quote_index'],
          'instagram_post_id':post['instagram_post_id'],'facebook_post_id':post['facebook_post_id']})
        state['next_quote']=post['quote_index']+1
        del state['pending']
        checkpoint('Complete quote publication',state)
        print('Both platforms published successfully')
if __name__=='__main__':main()
