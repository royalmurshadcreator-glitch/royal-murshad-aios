const fs=require('fs');const path=require('path');const root=__dirname;let failures=0,checks=0;function check(name,ok){checks++;console.log(`${ok?'[PASS]':'[FAIL]'} ${name}`);if(!ok)failures++}
for(const f of ['index.html','styles.css','app.js','README.md','assets/royal-lion.png'])check(`file exists: ${f}`,fs.existsSync(path.join(root,f)));
const html=fs.readFileSync(path.join(root,'index.html'),'utf8'),js=fs.readFileSync(path.join(root,'app.js'),'utf8'),css=fs.readFileSync(path.join(root,'styles.css'),'utf8');
check('HTML references CSS and JS',html.includes('styles.css')&&html.includes('app.js'));
check('public hero branding present',html.includes('One Kingdom.')&&html.includes('Every Kind of Mind.'));
check('search, filters, chat and backend-connect controls present',['globalSearch','filters','chatForm','connectBtn'].every(s=>html.includes(s)));
check('catalog has 60 entries',((js.match(/\['[^']+'\s*,\s*'(?:AI|Work|Automation|Business)'/g)||[]).length)===60);
check('search/filter/modal/backend functions present',['renderApps','activeFilter','showModal','testBackend'].every(s=>js.includes(s)));
check('no remote script/style dependency',!/<script[^>]+src=["']https?:/i.test(html)&&!/<link[^>]+href=["']https?:/i.test(html));
check('responsive CSS present',css.includes('@media(max-width:900px)')&&css.includes('@media(max-width:600px)'));
check('lion asset is readable',fs.statSync(path.join(root,'assets/royal-lion.png')).size>10000);
console.log(`\nResult: ${checks-failures}/${checks} checks passed`);process.exitCode=failures?1:0;
