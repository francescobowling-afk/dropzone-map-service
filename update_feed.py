#!/usr/bin/env python3
"""Pubblica schede con zona indicativa e istruzioni, anche senza coordinate. Nessuno scraping di forum."""
import json, pathlib, urllib.request, datetime
BASE=pathlib.Path(__file__).resolve().parent
OUT=BASE/'mappa-verificata.json'
INPUT=BASE/'data'/'verified-points.json'
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
URLS={'map':'https://fortnite-api.com/v1/map','quests':'https://prod.fn-api.cc/v1/quests?lang=it'}
BLOCK=('fortnite.gg','fortnite.gs','fortnite database')
def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'DropzoneGuide/1.1','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def entries(v):return v if isinstance(v,list) else list(v.values()) if isinstance(v,dict) else []
def text(v,limit=450):return str(v).strip()[:limit] if isinstance(v,(str,int,float)) else ''
def coords(p):
    q=p.get('normalizedPosition') or p.get('normalizedCoordinates') or p.get('mapPosition') or p
    if not isinstance(q,dict):return {}
    x,y=q.get('x'),q.get('y')
    return {'x':x,'y':y} if type(x) in (float,int) and type(y) in (float,int) and 0<=x<=1 and 0<=y<=1 else {}
def parse_map(payload):
    root=payload.get('data',payload)
    return [dict(id='poi:'+text(p.get('id') or p.get('name'),110),kind='Location',name=text(p.get('name'),110),description='Punto di interesse riportato da Fortnite-API',source='Fortnite-API',sourceUrl=URLS['map'],**coords(p)) for p in entries(root.get('pois')) if isinstance(p,dict) and text(p.get('name'))][:350]
def parse_quests(payload):
    root=payload.get('data',payload)
    pool=next((root.get(k) for k in ('quests','athenaQuests','brQuests','questDefinitions','questMap') if isinstance(root,dict) and isinstance(root.get(k),(list,dict))),None)
    if pool is None and isinstance(root,list):pool=root
    out=[]
    for i,q in enumerate(entries(pool)):
        if not isinstance(q,dict):continue
        name=text(q.get('name') or q.get('title') or q.get('displayName') or q.get('questName'),110)
        if not name:continue
        objectives=entries(q.get('objectives'))
        first=objectives[0] if objectives and isinstance(objectives[0],dict) else {}
        description=text(q.get('description') or q.get('shortDescription') or first.get('description') or first.get('text')) or 'Consulta i dettagli della missione nel gioco'
        out.append(dict(id='quest:'+text(q.get('templateId') or q.get('id') or i,100),kind='Obiettivi',name=name,description=description,source='FN Api',sourceUrl=URLS['quests']))
    return out[:1200]
def parse_curated():
    raw=json.loads(INPUT.read_text(encoding='utf-8'))
    result=[]
    for p in entries(raw.get('items')):
        if not isinstance(p,dict) or p.get('kind') not in ('NPC','Luoghi nascosti','Obiettivi','Location'):continue
        if not text(p.get('name')):continue
        url=text(p.get('sourceUrl'),500)
        if not url.startswith('https://') or any(x in url.lower() for x in BLOCK):continue
        result.append(dict(id=text(p.get('id') or p['name'],110),kind=p['kind'],name=text(p['name'],110),description=text(p.get('description')) or 'Informazione riportata dalla fonte',zoneName=text(p.get('zoneName'),110),searchHint=text(p.get('searchHint'),600),accuracy='approximate' if p.get('accuracy')=='approximate' or (p.get('zoneName') and not coords(p)) else 'precise' if coords(p) else 'unknown',source=text(p.get('source')) or 'Fonte pubblica',sourceUrl=url,**coords(p)))
    return result

def main():
    try:old=json.loads(OUT.read_text(encoding='utf-8'))
    except Exception:old={'items':[],'sourceStatus':{}}
    olditems=entries(old.get('items')); oldstatus=old.get('sourceStatus',{})
    source_status={};fresh=[];any_success=False
    for name,url,parser in [('map',URLS['map'],parse_map),('quests',URLS['quests'],parse_quests)]:
        try:
            items=parser(get_json(url))
            if not items:raise ValueError('Nessun dato nel formato riconosciuto')
            fresh.extend(items);any_success=True
            source_status[name]={'ok':True,'checkedAt':NOW,'count':len(items)}
        except Exception as e:
            source_status[name]={'ok':False,'checkedAt':NOW,'error':str(e)[:120]}
            # Preserve data from that source if it is unavailable.
            source_name='Fortnite-API' if name=='map' else 'FN Api'
            fresh.extend(x for x in olditems if x.get('source')==source_name)
    try:
        curated=parse_curated();fresh.extend(curated)
        source_status['curated']={'ok':True,'checkedAt':NOW,'count':len(curated)}
    except Exception as e:
        source_status['curated']={'ok':False,'checkedAt':NOW,'error':str(e)[:120]}
        fresh.extend(x for x in olditems if x.get('source') not in ('Fortnite-API','FN Api'))
    # An empty response is not a reason to erase the last good catalog.
    dedup={}
    for p in fresh:
        if isinstance(p,dict) and p.get('name') and p.get('kind'):dedup[(p['kind'],p.get('id',p['name']))]=p
    items=list(dedup.values()) or olditems
    output={'schemaVersion':3,'generatedAt':NOW,'lastSuccessfulDataAt':NOW if any_success else old.get('lastSuccessfulDataAt'), 'sourceStatus':source_status,'items':items,'status':'Dati disponibili pubblicati; le coordinate sono facoltative'}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Pubblicati',len(items),'elementi')
if __name__=='__main__':main()
