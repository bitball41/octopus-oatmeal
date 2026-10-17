// Lua 5.1 cannot compare a table-backed OmegaNum with a native number.
// Rewrite comparison AST nodes, preserving comments, strings and evaluation
// order. Never rewrite source text with regexes: strings can contain Lua code.
import luaparse from 'luaparse';

let input = '';
for await (const chunk of process.stdin) input += chunk;
const files = JSON.parse(input);
const operators = {'<':'lt', '<=':'le', '>':'gt', '>=':'ge', '==':'eq', '~=':'ne'};
for (const [name, source] of Object.entries(files)) {
  let ast;
  // 5.2 also accepts the empty semicolon statements in this browser base.
  // Emitted code is separately compiled against the actual Lua 5.1 runtime.
  try { ast = luaparse.parse(source, {luaVersion:'5.2', ranges:true, comments:false}); }
  catch (error) { throw new Error(name + ': ' + error.message); }
  function render(node) {
    if (node.type === 'BinaryExpression' && operators[node.operator]) {
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
}
process.stdout.write(JSON.stringify(files));
