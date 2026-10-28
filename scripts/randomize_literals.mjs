// Instrument literal gameplay effects, preserving all structural/UI numbers.
import luaparse from 'luaparse';
let input='';for await(const c of process.stdin)input+=c;
const files=JSON.parse(input);
const fields=new Set(['mult_mod','chip_mod','Xmult_mod','x_mult','xmult','h_mult','h_x_mult','p_dollars','h_dollars','dollars','repetitions']);
for(const [name,source] of Object.entries(files)) {
  if(!name.endsWith('.lua')||name.startsWith('Mods/Steamodded/')||name.startsWith('Mods/Amulet/')||name.startsWith('browser/'))continue;
  // Vanilla enhancements are evaluated outside calculate_joker and stay untouched.
  if(!name.startsWith('Mods/')&&name!=='card.lua')continue;
  const lower=name.toLowerCase();
  if(/enhancement|\/editions?\//.test(lower))continue;
  const ast=luaparse.parse(source,{luaVersion:'5.2',ranges:true,comments:false});const edits=[];
  function walk(node,inJoker=false){
    if(!node||typeof node!=='object')return;
    if(node.type==='FunctionDeclaration'&&node.identifier?.type==='MemberExpression'&&node.identifier.identifier?.name==='calculate_joker')inJoker=true;
    if(node.type==='TableKeyString'&&fields.has(node.key.name)&&(name.startsWith('Mods/')||inJoker)){
      const v=node.value;
      if(v.type==='NumericLiteral' || (v.type==='UnaryExpression'&&v.operator==='-'&&v.argument.type==='NumericLiteral')){
        const original=source.slice(...v.range), key=JSON.stringify(name+':'+v.range[0]+':'+node.key.name);
        edits.push([v.range[0],v.range[1],`(LiminalRandomizer and LiminalRandomizer.literal(${key}, ${original}) or ${original})`]);return;
      }
    }
    for(const [k,v]of Object.entries(node)){if(k==='range')continue;if(Array.isArray(v))v.forEach(x=>walk(x,inJoker));else if(v&&typeof v==='object')walk(v,inJoker);}
  }
  walk(ast);let result=source;for(const [a,b,text]of edits.sort((a,b)=>b[0]-a[0]))result=result.slice(0,a)+text+result.slice(b);files[name]=result;
}
process.stdout.write(JSON.stringify(files));
