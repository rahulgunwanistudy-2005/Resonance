import { createRequire } from 'node:module';
import fs from 'node:fs';
const require=createRequire(new URL('../web/package.json',import.meta.url));
const axeRequire=createRequire(require.resolve('@axe-core/playwright'));
const {chromium}=axeRequire('playwright-core');
const AxeBuilder=require('@axe-core/playwright').default;
const browser=await chromium.launch({headless:true,executablePath:process.argv[2]});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();const results=[];
for(const width of [1440,390]){await page.setViewportSize({width,height:1000});for(const route of ['home','console','measure','fleet','agent','bench','methods']){await page.goto('http://127.0.0.1:5173/#/'+route);await page.waitForLoadState('networkidle');const scan=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();results.push({width,route,violations:scan.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>n.target)}))});}}
await browser.close();fs.writeFileSync('eval/results/accessibility.json',JSON.stringify({tool:'axe-core',checks:results,summary:{pages:results.length,violations:results.reduce((n,r)=>n+r.violations.length,0)}},null,2)+'\n');console.log(JSON.stringify(results.filter(r=>r.violations.length)));
