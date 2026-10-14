from pathlib import Path
import http.server, threading, os, json
from playwright.sync_api import sync_playwright

root=Path("candidate").resolve()
os.chdir(root)
server=http.server.ThreadingHTTPServer(("127.0.0.1",8765),http.server.SimpleHTTPRequestHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
out=Path("../artifacts/b113-visual");out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    browser=pw.webkit.launch()
    for width,height,label in [(430,932,"iphone15pm"),(428,926,"iphone13pm"),(844,390,"landscape")]:
        page=browser.new_page(viewport={"width":width,"height":height},is_mobile=True,has_touch=True,device_scale_factor=2)
        page.goto("http://127.0.0.1:8765/",wait_until="domcontentloaded")
        page.locator('summary[aria-label="Opciones"]').click()
        page.locator("#soundBtn").click()
        page.locator('summary[aria-label="Opciones"]').click()
        page.locator("#startBtn").click()
        page.locator("#game").wait_for(state="visible",timeout=45000)
        page.wait_for_timeout(3600)
        page.screenshot(path=str(out/f"{label}.png"),full_page=True)
        result=page.evaluate("""() => {
          const box=id=>{const r=document.querySelector(id).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
          const ring=box('.player-card.active .rosco');
          const chips=[...document.querySelectorAll('.player-card.active .letter-chip')].map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}});
          const overlap=(a,b)=>a.x<b.x+b.w-1&&a.x+a.w>b.x+1&&a.y<b.y+b.h-1&&a.y+a.h>b.y+1;
          const collisions=[];
          for(let i=0;i<chips.length;i++)for(let j=i+1;j<chips.length;j++)if(overlap(chips[i],chips[j]))collisions.push([i,j]);
          const clocks=[box('#orbP1'),box('#orbP2')];
          return {ring,clocks,chipCount:chips.length,collisions,
            clockCollisions:clocks.some(c=>chips.some(ch=>overlap(c,ch))),
            centerText:document.querySelector('.player-card.active .rosco-center').innerText,
            clockBelowRing:clocks.every(c=>c.y>=ring.bottom-2),
            centeredLabels:[1,2].every(i=>{const a=box("#orbP"+i),n=box("#orbName"+i),v=box("#orbScore"+i);return Math.abs((a.x+a.w/2)-(n.x+n.w/2))<3&&Math.abs((a.x+a.w/2)-(v.x+v.w/2))<3}),
            scoreBelowClock:[1,2].every(i=>box("#orbScore"+i).y>=box("#orbP"+i).bottom),
            viewport:{w:innerWidth,h:innerHeight}};
        }""")
        print(label,json.dumps(result),flush=True)
        assert result["chipCount"]==27, "Missing rosco letters"
        assert not result["collisions"],"Overlapping letters"
        assert not result["clockCollisions"],"Clock overlaps rosco letter"
        assert result["clockBelowRing"],"Clocks must be below rosco"
        assert result["centeredLabels"],"Names or scores not centered below clocks"
        assert result["scoreBelowClock"],"Score overlaps clock"
        assert result["ring"]["w"]>0 and abs(result["ring"]["w"]-result["ring"]["h"])<3,"Ring distorted"
        page.close()
    browser.close()
server.shutdown()

# Regression: ring must not collapse after ResizeObserver updates.

# Retest compact horizontal layout and portrait geometry.

# Validate landscape 220px ring with uniformly scaled letter chips.
