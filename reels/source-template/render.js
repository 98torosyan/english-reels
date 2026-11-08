const {chromium}=require('playwright'); const fs=require('fs');
(async()=>{ const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1080,height:1920}});
 await p.goto('file:///home/claude/reel/reel.html'); await p.waitForTimeout(800);
 const meta=JSON.parse(fs.readFileSync('meta.json')); const T=meta.end+2.6, fps=30, n=Math.round(T*fps);
 fs.mkdirSync('frames',{recursive:true});
 for(let i=0;i<n;i++){ await p.evaluate(t=>seek(t), i/fps); await p.screenshot({path:`frames/f${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:92}); }
 console.log('frames',n); await b.close(); })();
