// Headless test of the points engine — mirrors the logic in index.html.
global.window = {};
require("../app/data.js");
const G = global.window.GAME_DATA;
const slug=s=>(s||"").replace(/[’']/g,"").replace(/[^a-zA-Z0-9]+/g,"-").replace(/^-|-$/g,"").toLowerCase();
const unitMap={}; G.units.forEach(u=>unitMap[u.id]=u);

function parseModel(u){
  const out={base:u.pointsValue||0, baseCount:1, perModel:0, maxExtra:0, addons:[], lists:[]};
  const comp=(u.composition||"").match(/^\s*(\d+)/); if(comp) out.baseCount=+comp[1];
  (u.sizeRules||[]).forEach(line=>{
    line.split(/\n/).forEach(seg=>{
      let m=seg.match(/up to (\d+) additional.*?\+\s*(\d+)\s*points?\s*per model/i);
      if(m){out.maxExtra=Math.max(out.maxExtra,+m[1]); out.perModel=out.perModel||+m[2];}
      m=seg.match(/up to (\d+)\s+([A-Z][\w '’]+?)\s+(?:for|at)\s*\+\s*(\d+)\s*points/i);
      if(m && !/^additional/i.test(m[2].trim())){out.addons.push({name:m[2].trim(),pts:+m[3],qty:0,max:+m[1]});}
      m=seg.match(/may include up to 1\s+([\w '’]+?)\s+(?:for|at)\s*\+\s*(\d+)\s*points/i);
      if(m && !out.addons.some(a=>a.name.toLowerCase()===m[1].trim().toLowerCase()))
        out.addons.push({name:m[1].trim(),pts:+m[2],qty:0,max:1});
    });
  });
  (u.options||[]).forEach(opt=>{
    const lm=opt.match(/from the ([\w '’\-]+? List)/i);
    if(lm){const key=slug(lm[1]); if(G.wargearLists[key]) out.lists.push({key,label:lm[1]});}
  });
  return out;
}

const samples=["dire-avengers","guardian-defenders","fire-dragons","wave-serpent","fire-prism","wraithguard","windriders"];
for(const id of samples){
  const u=unitMap[id]; if(!u){console.log("MISSING",id);continue;}
  const m=parseModel(u);
  console.log(`\n${u.name} [${u.slot}]  base=${m.base} count=${m.baseCount} perModel=${m.perModel} maxExtra=${m.maxExtra}`);
  m.addons.forEach(a=>console.log(`   addon: ${a.name} +${a.pts} (max ${a.max})`));
  m.lists.forEach(L=>console.log(`   list: ${L.label} -> ${G.wargearLists[L.key].items.length} items`));
  // simulate full squad cost
  const full=m.base + m.maxExtra*m.perModel + m.addons.reduce((s,a)=>s+a.pts*a.max,0);
  console.log(`   max-size cost (no wargear): ${full}`);
}
// sanity: every unit parses without throwing
let bad=0;
G.units.forEach(u=>{try{parseModel(u);}catch(e){bad++;console.log("THREW",u.id,e.message);}});
console.log(`\nAll ${G.units.length} units parsed; ${bad} errors.`);
