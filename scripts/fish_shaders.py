"""WebGL 1 (GLSL ES 1.00) repairs for Fish and Chips shaders.

Desktop GLSL accepts implicit int -> float conversions, uniform initializers
and a few GLSL 3 array forms that WebGL 1 rejects. love.js cannot recover from
a failed love.graphics.newShader (the error can escape Steamodded's pcall and
abort boot), so every Fish shader is rewritten at build time to compile on
WebGL 1.
"""
from __future__ import annotations

import re

TOKEN = re.compile(r'''
    (?P<comment>//[^\n]*|/\*.*?\*/)
  | (?P<pre>\#[^\n]*(?:\\\n[^\n]*)*)
  | (?P<num>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fF]?|0[xX][0-9a-fA-F]+)
  | (?P<id>[A-Za-z_]\w*)
  | (?P<op>\+\+|--|<=|>=|==|!=|&&|\|\||[-+*/%]=|[-+*/%<>=!?:;,.(){}\[\]&|^~])
  | (?P<ws>\s+)
''', re.S | re.M | re.X)

INT_TYPES = {'int', 'ivec2', 'ivec3', 'ivec4'}
BIN_OPS = {'<', '>', '<=', '>=', '==', '!=', '+', '-', '*', '/', '%', '=',
           '+=', '-=', '*=', '/='}


def tokenize(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f'shader tokenizer stuck at {text[pos:pos + 20]!r}')
        out.append([m.lastgroup, m.group()])
        pos = m.end()
    return out


def float_literals(text):
    """Turn integer literals into float literals outside integer contexts."""
    toks = tokenize(text)
    sig = [i for i, (k, _) in enumerate(toks) if k not in ('ws', 'comment', 'pre')]
    val = lambda j: toks[sig[j]][1] if 0 <= j < len(sig) else ''
    int_names, int_funcs = set(), set()
    int_params = {}     # user function -> argument positions declared int
    for j in range(1, len(sig) - 1):
        if toks[sig[j]][0] == 'id' and val(j + 1) == '(' and toks[sig[j - 1]][0] == 'id' \
                and val(j - 1) not in ('return', 'else'):
            k, arg, depth, positions = j + 2, 0, 0, set()
            while k < len(sig) and not (depth == 0 and val(k) == ')'):
                depth += val(k) == '('
                depth -= val(k) == ')'
                if depth == 0 and val(k) == ',':
                    arg += 1
                if depth == 0 and val(k) in INT_TYPES:
                    positions.add(arg)
                k += 1
            if val(k + 1) == '{' and positions:
                int_params[val(j)] = positions
    for j in range(len(sig)):
        if val(j) in INT_TYPES and j + 1 < len(sig) and toks[sig[j + 1]][0] == 'id':
            name = val(j + 1)
            (int_funcs if val(j + 2) == '(' else int_names).add(name)
            # int a = 1, b = 2;
            depth, k = 0, j + 2
            while k < len(sig) and not (depth == 0 and val(k) in (';', ')', '{')):
                depth += val(k) in ('(', '[')
                depth -= val(k) in (')', ']')
                if depth == 0 and val(k) == ',' and toks[sig[k + 1]][0] == 'id':
                    int_names.add(val(k + 1))
                k += 1

    def int_operand(j, step):
        """Is the operand on one side of the operator at j integer-typed?"""
        k = j + step
        if val(k) in ('-', '+') and step > 0:
            k += 1
        if val(k) in int_names:
            return True
        if val(k) == ']' and step < 0:
            return False
        if step < 0 and val(k) == ')':
            # foo(...) * 2 where foo returns int, or int(...) * 2
            depth, m = 0, k
            while m >= 0:
                depth += val(m) == ')'
                depth -= val(m) == '('
                if depth == 0:
                    break
                m -= 1
            return val(m - 1) in int_funcs or val(m - 1) in INT_TYPES
        return False

    stack = []          # innermost '(' / '[' contexts: 'int' or 'float'
    stmt_int = False    # current statement declares an int
    func_int = False    # inside a function returning int
    pending_func = None
    for j, i in enumerate(sig):
        v = val(j)
        prev = val(j - 1)
        if v in (';', '{', '}'):
            stmt_int = False
            if v == '{' and pending_func is not None:
                func_int, pending_func = pending_func, None
        if v in INT_TYPES and prev in (';', '{', '}', '(', 'const', 'in', 'out', 'inout', ''):
            stmt_int = True
        if v in INT_TYPES and val(j + 2) == '(' and prev in (';', '}', ''):
            pending_func = True
        elif toks[i][0] == 'id' and val(j + 2) == '(' and prev in (';', '}', '') and v not in ('return',):
            pending_func = False
        if v in ('(', '['):
            if v == '[' or prev in INT_TYPES or prev in int_funcs:
                stack.append(['int'])
            elif prev in int_params and val(j - 2) not in INT_TYPES | {'float', 'void', 'vec2', 'vec3', 'vec4', 'bool'}:
                stack.append(['call', prev, 0])
            else:
                stack.append(['other'])
            continue
        if v in (')', ']'):
            if stack:
                stack.pop()
            continue
        if v == ',' and stack and stack[-1][0] == 'call':
            stack[-1][2] += 1
            continue
        if toks[i][0] != 'num' or not re.fullmatch(r'\d+', v):
            continue
        if stack and stack[-1][0] == 'int':
            continue
        if stack and stack[-1][0] == 'call' and stack[-1][2] in int_params[stack[-1][1]] \
                and prev in ('(', ',') and val(j + 1) in (')', ','):
            continue
        if stmt_int and not stack:
            continue
        if stmt_int and stack and prev in ('=', ',', '<', '>', '<=', '>=', ';'):
            # for (int i = 0; i < 10; i++)
            continue
        if prev in BIN_OPS and int_operand(j - 1, -1):
            continue
        if prev in ('-', '+') and val(j - 2) in BIN_OPS | {'(', ',', 'return'} and int_operand(j - 2, -1):
            continue
        if val(j + 1) in BIN_OPS and int_operand(j + 1, +1):
            continue
        if prev == 'return' and func_int:
            continue
        if prev == 'case':
            continue
        toks[i][1] = v + '.0'
    return ''.join(t for _, t in toks)


def strip_uniform_initializers(text):
    # GLSL ES 1.00 forbids `extern float x = 1.0;` (desktop GLSL allows it).
    return re.sub(r'(\b(?:extern|uniform)\b[^;=(){}]*?)\s*=\s*[^;]+;', r'\1;', text)


def inline_int_defines(text):
    """Inline `#define NAME 10` so each use gets the int/float literal it needs."""
    for m in list(re.finditer(r'^[ \t]*#define[ \t]+(\w+)[ \t]+(\d+)[ \t]*$', text, re.M)):
        name, value = m.groups()
        rest = text.replace(m.group(), '', 1)
        directives = re.findall(r'^[ \t]*#.*$', rest, re.M)
        if any(re.search(r'\b' + name + r'\b', d) for d in directives):
            continue
        text = re.sub(r'\b' + name + r'\b', value, rest)
    return text


def uniform_precision(text):
    # LÖVE declares fragment floats mediump but vertex floats highp. Uniforms
    # shared by both stages must agree on WebGL 1, so qualify them the way
    # LÖVE qualifies its own built-in uniforms.
    return re.sub(r'\b(extern|uniform)(\s+)(float|number|vec[234]|mat[234]|int|ivec[234])\b',
                  r'\1\2LOVE_HIGHP_OR_MEDIUMP \3', text)


def array_initializers(text):
    """`vec3 a[2] = vec3[](x, y);` -> element assignments (GLSL ES 1.00)."""
    pattern = re.compile(r'(?P<indent>[ \t]*)(?P<type>\w+)\s+(?P<name>\w+)\s*\[\s*(?P<size>\d+)\s*\]'
                         r'\s*=\s*(?P=type)\s*\[\s*\d*\s*\]\s*\(')
    while True:
        m = pattern.search(text)
        if not m:
            return text
        depth, k, args, start = 1, m.end(), [], m.end()
        while depth:
            c = text[k]
            if c in '([':
                depth += 1
            elif c in ')]':
                depth -= 1
            if (c == ',' and depth == 1) or depth == 0:
                args.append(text[start:k].strip())
                start = k + 1
            k += 1
        end = text.index(';', k) + 1
        if len(args) != int(m['size']):
            raise RuntimeError(f'array initializer size mismatch for {m["name"]}')
        body = m['indent'] + f'{m["type"]} {m["name"]}[{m["size"]}];' + ''.join(
            f'\n{m["indent"]}{m["name"]}[{i}] = {a};' for i, a in enumerate(args))
        text = text[:m.start()] + body + text[end:]


def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise RuntimeError(f'Fish shader anchor missing: {label}')
    return text.replace(old, new, 1)


def targeted(name, text):
    base = name.rsplit('/', 1)[-1].lower()
    if base in ('jpeg_encode.fs', 'jpeg_decode.fs'):
        # Loop bounds must be constant. The Lua side sends samples <= 19.
        for axis in ('x', 'y'):
            text = replace_once(text, f'for(float {axis} = 0.; {axis} < samples; {axis}++) {{',
                                f'for(float {axis} = 0.; {axis} < 20.; {axis}++) {{ if ({axis} >= samples) break;',
                                base + ' loop ' + axis)
    if base == 'prismond.fs':
        # Fragment shaders may only index arrays with constants or loop indices.
        text = replace_once(text, 'vec3 base = mix(palette[i], palette[j == 8 ? 0 : j], fract(element));',
                            'int wrapped_j = j == 8 ? 0 : j;\n'
                            '    vec3 colour_i = palette[0];\n'
                            '    vec3 colour_j = palette[0];\n'
                            '    for (int k = 0; k < 8; k++) {\n'
                            '        if (k == i) colour_i = palette[k];\n'
                            '        if (k == wrapped_j) colour_j = palette[k];\n'
                            '    }\n'
                            '    vec3 base = mix(colour_i, colour_j, fract(element));',
                            'prismond palette lookup')
    return text


def repair(name, text):
    text = targeted(name, text)
    text = strip_uniform_initializers(text)
    text = inline_int_defines(text)
    text = array_initializers(text)
    text = float_literals(text)
    return uniform_precision(text)
