// Lua 5.1 cannot compare a table-backed OmegaNum with a native number.
// Rewrite comparison AST nodes, preserving comments, strings and evaluation
// order. Never rewrite source text with regexes: strings can contain Lua code.
import luaparse from 'luaparse';
import {createHash} from 'node:crypto';
import {mkdirSync,readFileSync,writeFileSync,existsSync,renameSync} from 'node:fs';
const cacheDir = new URL('../build/comparison-cache/', import.meta.url);
mkdirSync(cacheDir,{recursive:true});

let input = '';
for await (const chunk of process.stdin) input += chunk;
const files = JSON.parse(input);
const operators = {'<':'lt', '<=':'le', '>':'gt', '>=':'ge', '==':'eq', '~=':'ne'};
// These engine classes operate on screen coordinates, frame counters and
// object identity. They never compare scores, money, antes or hand levels.
// They load before Amulet, so retain the native math used by their geometry.
const geometry = new Set(['engine/node.lua', 'engine/moveable.lua']);
// Keep comparisons native when their operands cannot be OmegaNums. Most
// frame-loop comparisons check names, nil, booleans, lengths or type() results.
// Numeric literals alone are not enough: chips > 0 still needs the adapter.
function primitive(node) {
  if (node.type === 'NumericLiteral') return 'number';
  if (node.type === 'StringLiteral') return 'string';
  if (node.type === 'BooleanLiteral') return 'boolean';
  if (node.type === 'NilLiteral') return 'nil';
  if (node.type === 'UnaryExpression') {
    if (node.operator === '#') return 'number';
    if (node.operator === 'not') return 'boolean';
    if (node.operator === '-' && primitive(node.argument) === 'number') return 'number';
  }
  if (node.type === 'BinaryExpression') {
    if (operators[node.operator]) return 'boolean';
    if (node.operator === '..') {
      const a = primitive(node.left), b = primitive(node.right);
      return ['number','string'].includes(a) && ['number','string'].includes(b) ? 'string' : null;
    }
    if (primitive(node.left) === 'number' && primitive(node.right) === 'number') return 'number';
  }
  if (node.type === 'CallExpression' && node.base.type === 'Identifier') {
    if (node.base.name === 'type' || node.base.name === 'tostring') return 'string';
  }
  return null;
}
function needsAdapter(node) {
  const a = primitive(node.left), b = primitive(node.right);
  if (a && b) return false;
  if (node.operator === '==' || node.operator === '~=') {
    if ((a && a !== 'number') || (b && b !== 'number')) return false;
  }
  return true;
}
for (const [name, source] of Object.entries(files)) {
  if (geometry.has(name)) {
    files[name] = 'local math = {abs=math.abs, cos=math.cos, sin=math.sin, sqrt=math.sqrt, min=math.min, max=math.max, pi=math.pi}\n' + source;
    continue;
  }
  const cachePath = new URL(createHash('sha256').update('v1:'+source).digest('hex')+'.lua', cacheDir);
  if(existsSync(cachePath)) { files[name]=readFileSync(cachePath,'utf8'); continue; }
  let ast;
  // 5.2 also accepts the empty semicolon statements in this browser base.
  // Emitted code is separately compiled against the actual Lua 5.1 runtime.
  try { ast = luaparse.parse(source, {luaVersion:'5.2', ranges:true, comments:false}); }
  catch (error) { throw new Error(name + ': ' + error.message); }
  function render(node) {
    if (node.type === 'BinaryExpression' && operators[node.operator] && needsAdapter(node)) {
      return `__octopus_${operators[node.operator]}(${render(node.left)}, ${render(node.right)})`;
    }
    const children = [];
    for (const [key, value] of Object.entries(node)) {
      if (key === 'range') continue;
      const values = Array.isArray(value) ? value : [value];
      for (const child of values) if (child?.type && child.range) children.push(child);
    }
    children.sort((a,b)=>a.range[0]-b.range[0]);
    let text = '', cursor = node.range[0];
    for (const child of children) {
      if (child.range[0] < cursor) continue;
      text += source.slice(cursor, child.range[0]) + render(child);
      cursor = child.range[1];
    }
    return text + source.slice(cursor, node.range[1]);
  }
  files[name] = render({...ast, range:[0,source.length]});
  const tempPath=new URL(cachePath.href+'.'+process.pid+'.tmp');
  writeFileSync(tempPath,files[name]);renameSync(tempPath,cachePath);
}
process.stdout.write(JSON.stringify(files));
