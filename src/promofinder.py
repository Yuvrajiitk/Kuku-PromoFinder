"""PromoFinder: deterministic, inspectable screenplay-to-promo ranking engine.
No external API, no training data, no screenplay text sent to third parties.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, re
from collections import Counter
from pathlib import Path

TIME = r'(\d{2}:\d{2}(?:\.\d{1,2})?)'
EVENT = re.compile(r'^Start:\s*\(?'+TIME+r'\)?\s*\|\s*End:\s*\(?'+TIME+r'\)?', re.I)
SCENE = re.compile(r'^Scene (start|end):\s*'+TIME, re.I)
HEADER = re.compile(r'^\*\*(.+?):\*\*$')
STOP = {'a','an','the','i','me','my','you','your','he','she','her','his','they','them','we','our','is','are','was','were','to','of','in','on','at','and','but','or','it','that','this','for','with','not','from','be','as','have','has','had','do','did','so','if','what','who','why','how','will','would','could','should','can','just','all','no'}
HOOK = {'never':1.7,'marry':1.6,'marrying':1.6,'husband':1.4,'wife':1.4,'duke':2.1,'secret':1.9,'pregnant':2.4,'kill':2.6,'dead':2.5,'murder':2.8,'betray':2.4,'betrayed':2.4,'liar':1.9,'thief':2.0,'stop':1.4,'wait':1.0,'father':1.0,'mother':.9,'money':1.3,'truth':1.6,'love':.9,'leave':1.2,'blood':2.1,'help':1.5,'name':.8,'impossible':1.9,'royal':1.5,'arrest':2.2,'divorce':2.2,'sister':1.3,'daughter':1.2,'son':1.2,'poison':2.5,'fire':1.7,'die':2.3,'dying':2.2,'danger':2.0,'traitor':2.5,'prove':1.1,'prove':1.1,'caught':2.0,'enough':1.2,'expose':2.0,'baby':1.6,'mine':1.1,'get':.3,'out':.4}
SUSPENSE = {'but':.7,'unless':2.1,'until':1.0,'before':.7,'if':1.2,'who':1.6,'what':1.5,'why':1.7,'how':1.5,'where':1.2,'wait':1.1,'stop':1.1,'secret':1.7,'truth':1.8,'real':1.0,'actually':1.2,'suddenly':1.5,'arrives':1.4,'appears':1.3,'reveals':1.5,'reveal':1.7,'discover':1.7,'exposed':1.8,'shocked':1.3,'stunned':1.2,'gasp':1.3,'door':.6,'enters':1.1,'recognizes':1.6,'realizes':1.4,'threatens':1.5,'gun':2.0,'knife':1.6,'blood':1.4,'dead':1.6,'kill':1.4,'caught':1.3,'witness':1.6,'identity':2.0,'demand':.9,'scream':1.3,'silence':.8,'whispers':.8,'promise':.8}
TWIST = {'but','unless','except','instead','however','only','actually','truth','secret','real','reveals','never'}
WORDS = re.compile(r"[a-zA-Z']+")

def seconds(t):
    m,s=t.split(':');return int(m)*60+float(s)
def stamp(t):
    m=int(t//60); s=t-m*60
    return f'{m:02d}:{s:05.2f}'
def tokens(s):return [w.lower() for w in WORDS.findall(s)]
def excerpt(s,n=170):
    s=' '.join(s.split()).strip('" ')
    return s if len(s)<=n else s[:n-1].rsplit(' ',1)[0]+'…'

def parse_episode(path):
    text=Path(path).read_text(encoding='utf-8-sig',errors='replace')
    number=int(re.search(r'episode-(\d+)',Path(path).name,re.I).group(1))
    logline=re.search(r'^EPISODE LOGLINE:\s*(.+)$',text,re.M)
    events=[];scene=0;scene_bounds=[];category=None
    lines=text.splitlines()
    for i,line in enumerate(lines):
        s=line.strip();sm=SCENE.match(s)
        if s.startswith('SCENE ') and re.match(r'SCENE\s+\d+',s):scene+=1
        if sm:
            scene_bounds.append((sm.group(1).lower(),seconds(sm.group(2)),scene))
        hm=HEADER.match(s)
        if hm:
            category=hm.group(1)
            continue
        match=EVENT.match(s)
        if match and category:
            start,end=seconds(match.group(1)),seconds(match.group(2))
            # Event body is usually the next nonempty text line.
            body=''
            for following in lines[i+1:i+4]:
                if following.strip():
                    if not EVENT.match(following.strip()) and not following.strip().startswith('**'):
                        body=following.strip()
                    break
            typ=category.split(' ',1)[0].upper() if category in ('CAMERA','ACTION','SFX','MUSIC') else 'DIALOGUE'
            if 0<=start<end and body:
                events.append({'start':round(start,2),'end':round(end,2),'type':typ,'speaker':category if typ=='DIALOGUE' else '', 'text':body,'scene':scene})
    duration=max([e['end'] for e in events]+[v for k,v,_ in scene_bounds if k=='end']+[0])
    return {'episode':number,'filename':Path(path).name,'logline':logline.group(1) if logline else '', 'duration':round(duration,2),'events':events,'scene_count':scene, 'scene_bounds':scene_bounds}

def strongest(events, weight):
    if not events:return None,0
    ranked=[]
    for e in events:
        ws=tokens(e['text']);score=sum(weight.get(w,0) for w in set(ws))
        if '?' in e['text']:score+=1.65
        if '!' in e['text']:score+=.35
        if e['type']=='DIALOGUE':score*=1.25
        else:score*=.85
        ranked.append((score,e))
    score,e=max(ranked,key=lambda item:item[0])
    return e,score

def evaluate(ep,start,end):
    events=[e for e in ep['events'] if e['start']<end and e['end']>start and e['type']!='CAMERA']
    if len(events)<4:return None
    first=[e for e in events if e['start']<start+3.05 and e['end']>start]
    last=[e for e in events if e['start']<end and e['end']>=end-7.0]
    hook_e,hook_v=strongest(first,HOOK)
    end_e,end_v=strongest(last,SUSPENSE)
    if not hook_e or not end_e:return None
    dialogue=[e for e in events if e['type']=='DIALOGUE']
    if len(dialogue)<3:return None
    # Standalone comprehension proxies: first 10 s references, named entities, speech density.
    intro=[e for e in events if e['start']<start+10]
    intro_text=' '.join(e['text'] for e in intro)
    all_text=' '.join(e['text'] for e in events)
    intro_w=tokens(intro_text); all_w=tokens(all_text)
    opaque=sum(int(x in intro_w) for x in ['he','she','they','him','her','them','it','this','that','those'])
    named=len(re.findall(r'\b[A-Z][a-z]{2,}\b',intro_text))
    clarity=max(0.0,min(1.0, .6+.045*min(named,5)-.055*opaque+.07*(len(dialogue)>=5)))
    first_dialogue=min((e['start'] for e in dialogue),default=end)
    immediate=(first_dialogue-start<5.0)
    hook_score=min(1, (hook_v/5.5)*.78+.20*(immediate)+.07*('?' in hook_e['text']))
    cliff_score=min(1,(end_v/5.0)*.8+.18*('?' in end_e['text']))
    # Explicitly discourage resolving the cliff after the last suspense beat.
    if end - end_e['end']>2.5:cliff_score*=.7
    tension=min(1.0,(sum(1 for w in all_w if w in HOOK)+sum(1 for w in all_w if w in TWIST)*1.3)/(max(12,len(all_w)))*5)
    speech_density=min(1.0, len(dialogue)/max(3,(end-start)/4.8))
    duration=end-start
    target=40
    duration_quality=max(0.0,1-abs(duration-target)/45)
    score=100*(.29*hook_score+.30*cliff_score+.21*clarity+.10*tension+.06*speech_density+.04*duration_quality)
    if hook_v<.35:score-=10
    if end_v<.6:score-=10
    # raw subtitles and exact evidence retained to enable reviewer checks
    words=set(w for w in all_w if w not in STOP and len(w)>=4)
    return {'episode':ep['episode'],'start_seconds':round(start,2),'end_seconds':round(end,2),'duration_seconds':round(duration,2),
      'start':stamp(start),'end':stamp(end),'score':round(score,2),'hook_score':round(hook_score,3),'cliffhanger_score':round(cliff_score,3),
      'standalone_score':round(clarity,3),'tension_score':round(tension,3),'hook':excerpt(hook_e['text']),
      'cliffhanger':excerpt(end_e['text']),'hook_type':hook_e['type'],'cliffhanger_type':end_e['type'],
      'reason':f"Immediate {('spoken' if hook_e['type']=='DIALOGUE' else 'visual')} conflict; suspense near the cut; "
               + ('clear opening context.' if clarity>=.65 else 'some prior context may be needed.'),
      'segment_list':[{'episode':ep['episode'],'start':stamp(start),'end':stamp(end)}],
      'event_count':len(events),'dialogue_count':len(dialogue),'token_set':words,
      'source_filename':ep['filename']}

def candidates(ep):
    ev=[e for e in ep['events'] if e['type'] in ('DIALOGUE','ACTION')]
    starts=sorted(set(round(e['start'],2) for e in ev if e['start']<=ep['duration']-20))
    ends=sorted(set(round(e['end'],2) for e in ev if e['end']>=20))
    # Scope limited to one contiguous segment within a single episode.
    out=[]
    for start in starts:
        for end in ends:
            duration=end-start
            if duration<25:continue
            if duration>55:break
            val=evaluate(ep,start,end)
            if val:out.append(val)
    out.sort(key=lambda c:c['score'],reverse=True)
    # Pre-deduplicate overlapping windows to keep candidate pool tractable
    kept=[]
    for c in out:
        if any(overlap(c,k)>.64 for k in kept):continue
        kept.append(c)
        if len(kept)>=12:break
    return kept

def overlap(a,b):
    if a['episode']!=b['episode']:return 0.0
    intersect=max(0,min(a['end_seconds'],b['end_seconds'])-max(a['start_seconds'],b['start_seconds']))
    union=max(a['end_seconds'],b['end_seconds'])-min(a['start_seconds'],b['start_seconds'])
    return intersect/union if union else 0

def similarity(a,b):
    a_words,b_words=a['token_set'],b['token_set']; jac=len(a_words & b_words)/max(1,len(a_words | b_words))
    return max(overlap(a,b),.45*jac)

def rank(pool,n=20,max_per_episode=1,diversity=.25):
    selected=[];count=Counter()
    while len(selected)<n:
        elig=[c for c in pool if count[c['episode']]<max_per_episode and c not in selected]
        if not elig:break
        best=max(elig,key=lambda c: c['score']-100*diversity*max([similarity(c,s) for s in selected] or [0]))
        selected.append(best);count[best['episode']]+=1
    for i,c in enumerate(selected,1):c['rank']=i
    return selected

def public(c):return {k:v for k,v in c.items() if k!='token_set'}

def run(input_dir,output_dir,top=20):
    input_dir=Path(input_dir);out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    paths=sorted(input_dir.glob('episode-*.txt'))
    if not paths:raise ValueError(f'No episode-*.txt files in {input_dir}')
    eps=[parse_episode(p) for p in paths]
    missing=sorted(set(range(1,max(ep['episode'] for ep in eps)+1)) - {ep['episode'] for ep in eps})
    pool=[x for ep in eps for x in candidates(ep)]
    chosen=rank(pool,n=top)
    # Coverage export: one best valid candidate for each episode, independent of top-N cutoff.
    best_by_episode={}
    for c in pool:
        if c['episode'] not in best_by_episode or c['score']>best_by_episode[c['episode']]['score']:
            best_by_episode[c['episode']]=c
    per_episode=[public(best_by_episode[k]) for k in sorted(best_by_episode)]
    (out/'best_per_episode.json').write_text(json.dumps({'method':'rules-v1','promos':per_episode},indent=2,ensure_ascii=False),encoding='utf-8')
    for c in chosen:
        assert 20<=c['duration_seconds']<=60
        assert 0<=c['start_seconds']<c['end_seconds']
    result={'schema_version':'1.0','method':'rules-v1; no supervised training','input_episode_count':len(eps),'top_promos':[public(c) for c in chosen]}
    (out/'promos_ranked.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    if chosen:
        with (out/'promos_ranked.csv').open('w',newline='',encoding='utf-8') as f:
            fields=['rank','episode','start','end','duration_seconds','score','hook_score','cliffhanger_score','standalone_score','hook','cliffhanger','reason','source_filename']
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows([{key:c.get(key) for key in fields} for c in chosen])
    qa={'total_episodes':len(eps),'total_events':sum(len(e['events']) for e in eps),'total_dialogue_events':sum(sum(v['type']=='DIALOGUE' for v in e['events']) for e in eps),
      'total_action_events':sum(sum(v['type']=='ACTION' for v in e['events']) for e in eps),
      'duration_seconds_min':min(e['duration'] for e in eps),'duration_seconds_max':max(e['duration'] for e in eps),
      'missing_episode_numbers':missing,'zero_parsed_events':[e['episode'] for e in eps if not e['events']],
      'no_candidates':[e['episode'] for e in eps if not any(c['episode']==e['episode'] for c in pool)],
      'candidate_count_after_local_dedup':len(pool),'selected_promos':len(chosen),'episodes_with_candidate':len(best_by_episode),
      'invalid_event_bounds':sum(sum(not (0<=v['start']<v['end']<=e['duration']+.001) for v in e['events']) for e in eps),
      'episode_summary':[{'episode':e['episode'],'duration_seconds':e['duration'],'scenes':e['scene_count'],'events':len(e['events']),
      'dialogue_events':sum(v['type']=='DIALOGUE' for v in e['events']),'action_events':sum(v['type']=='ACTION' for v in e['events'])} for e in eps],
      'limitations':['Heuristic scores are not probabilities or engagement measurements.','Standalone coherence is approximate and requires human inspection.','Only one continuous same-episode clip per recommendation; no cross-episode montage.','Screenplay timestamps may not match edited video timecodes.','No blinded human labels, so precision and recall cannot be reported.']}
    (out/'quality_audit.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
    return result,qa

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='data');ap.add_argument('--output',default='outputs');ap.add_argument('--top',type=int,default=20)
    args=ap.parse_args();result,qa=run(args.input,args.output,args.top)
    print(f"Parsed {qa['total_episodes']} episodes, {qa['total_events']} events; selected {len(result['top_promos'])} promos")
    for c in result['top_promos'][:10]:print(f"#{c['rank']:2} E{c['episode']:02} {c['start']}-{c['end']} score={c['score']:.1f} | {c['hook'][:75]}")
if __name__=='__main__':main()
