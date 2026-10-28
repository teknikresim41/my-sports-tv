#!/usr/bin/env python3
"""Best-effort public TV guide parser. Never invent a match."""
import datetime as dt, json, re, os
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

CHANNELS={
 'TRT 1':['https://www.trt1.com.tr/yayin-akisi','https://www.trt.net.tr/televizyon/akis.aspx?kanal=trt-1'],
 'TRT Spor':['https://www.trtspor.com.tr/yayin-akisi'],
 'ATV':['https://www.atv.com.tr/yayin-akisi'],
 'A Spor':['https://www.aspor.com.tr/yayin-akisi'],
 'TV8':['https://www.tv8.com.tr/yayin-akisi'],
 'TV8,5':['https://www.tv8bucuk.com/yayin-akisi'],
}
# Conservative: only an explicit match context and a start time are sufficient.
MATCH=re.compile(r'(?:\b(?:maç[ıi]?|karşılaşma(?:sı)?|canlı maç|şampiyonlar ligi|avrupa ligi|konferans ligi|türkiye kupası|süper lig|basketbol süper ligi|euroleague|uefa)\b|\b[A-Za-zÇĞİÖŞÜçğıöşü0-9 .]{2,35}\s+[-–]\s+[A-Za-zÇĞİÖŞÜçğıöşü0-9 .]{2,35}\b)',re.I)
REPLAY=re.compile(r'\b(tekrar|özet|highlights|geniş özet|maçın ardından|maç önü|belgesel|stüdyo|programı)\b',re.I)
TIME=re.compile(r'(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)')
TZ=ZoneInfo('Europe/Istanbul')
now=dt.datetime.now(TZ)
session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; MySportsTVGuide/1.0; personal use)'})
results=[]; status={}
for channel,urls in CHANNELS.items():
    found=[];errors=[]
    for url in urls:
        try:
            r=session.get(url,timeout=18);r.raise_for_status()
            soup=BeautifulSoup(r.text,'html.parser')
            for x in soup(['script','style','nav','footer','header']):x.decompose()
            seen=set()
            # Prefer discrete schedule rows; fall back to short line text.
            candidates=soup.select('li, tr, article, [class*="program"], [class*="schedule"], [class*="event"], [class*="item"]')
            if not candidates:candidates=soup.select('div')
            for el in candidates:
                line=' '.join(el.stripped_strings)
                if len(line)>210 or len(line)<9 or not MATCH.search(line) or REPLAY.search(line):continue
                m=TIME.search(line)
                if not m:continue
                clock=f'{int(m.group(1)):02d}:{m.group(2)}'
                title=(line[:m.start()]+' '+line[m.end():]).strip(' -|–:')
                title=re.sub(r'\s+',' ',title)
                if not (5<len(title)<125):continue
                key=(clock,title.lower())
                if key in seen:continue
                seen.add(key)
                found.append({'time':clock,'title':title,'channel':channel,'date':now.date().isoformat(),'source':url})
            if found:break
        except Exception as e:errors.append(type(e).__name__+': '+str(e)[:90])
    # Source may be accessible but no match; distinguish from inaccessible.
    status[channel]={'matches_found':len(found),'source':url if found else None,'errors':errors}
    results.extend(found)
# Duplicate rows in nested DOM often have slightly different text. Keep a bounded set.
results=sorted(results,key=lambda x:(x['time'],x['channel'],x['title']))[:100]
output={'date':now.date().isoformat(),'checked_at':now.isoformat(timespec='minutes'),'timezone':'Europe/Istanbul','matches':results,'sources':status,'note':'Best-effort parsing; verify broadcaster schedule before relying on it.'}
with open(os.path.join(os.path.dirname(__file__),'..','tv-matches.json'),'w',encoding='utf-8') as f:json.dump(output,f,ensure_ascii=False,indent=2)
print('Matches:',len(results),'Channels:',{k:v['matches_found'] for k,v in status.items()})
