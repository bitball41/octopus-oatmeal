"""Compare %s compatibility to LuaJIT; execute packed atlas injection."""
from pathlib import Path
import runpy
import zipfile
from lupa.lua51 import LuaRuntime
from lupa.luajit21 import LuaRuntime as LuaJIT
root = Path(__file__).resolve().parents[1]
z = zipfile.ZipFile(root/'game.data')
source = z.read('browser/format.lua').decode()
web, upstream = LuaRuntime(unpack_returned_tuples=True), LuaJIT(unpack_returned_tuples=True)
web.execute(source).install()
cases = [
    'return string.format("%s_%s", "mod_tags", nil)',
    'return ("%s|%s|%s"):format(nil, true, false)',
    'return string.format("%% %s %.2f %s", nil, 1.25, false)',
    'return string.format("%8.3s", false)',
    'return string.format("%s %s", setmetatable({}, {__tostring=function() return "object" end}), nil)',
    'return string.format("%04d %.2f %x %q %s", 12, 1.25, 255, "quoted", 42)',
    'return string.format("%%%s", nil)',
    'return string.format("%%s %s", true)',
    'return string.format("%s", "plain")',
]
for case in cases:
    assert web.execute(case) == upstream.execute(case), case
for case in ['return string.format("%s")', 'return string.format("%d", nil)',
             'return string.format("%s %d", nil, false)', 'return string.format("%z", 1)',
             'return string.format("%")']:
    for runtime in (web, upstream):
        assert runtime.eval('function() return pcall(function() '+case+' end) end')()[0] is False, case
print('LuaJIT comparison passed: nil/boolean/object %s, width/precision, escaped percent, numeric formats and invalid-input errors')

# Reuse the actual packed base class/registration setup; graphics calls below
# are stubs, while each requested atlas path is verified against the archive.
state = runpy.run_path(str(root/'scripts/validate_object_registration.py'))
lua = state['lua']
paths = []
def file_data(path):
    assert z.read(path).startswith(b'\x89PNG\r\n\x1a\n'), path
    paths.append(path)
    return path
lua.globals().packed_file_data = file_data
lua.execute('''
NFS={newFileData=packed_file_data}
SMODS.path='Mods/Steamodded/'
SMODS.config={graphics_mipmap_level_options={0},graphics_mipmap_level=1}
G.SETTINGS={language='en-us',GRAPHICS={texture_scaling=1}}
G.ASSET_ATLAS={}
love={image={newImageData=function(data) return data end},graphics={newImage=function(data,options)
 return {path=data,options=options,setMipmapFilter=function() end}
end}}
''')
objects = z.read('Mods/Steamodded/src/game_object.lua').decode()
a = objects.index('    SMODS.Atlases = {}')
b = objects.index('    -------------------------------------------------------------------------------------------------', a)
lua.execute(objects[a:b])
lua.execute('''
local ok,err=pcall(function() SMODS.Atlases.mod_tags:inject() end)
assert(not ok and string.find(err,'format',1,true) and string.find(err,'got nil',1,true),
 'expected the original Lua 5.1 atlas crash before installing compatibility')
''')
lua.execute(source).install()
lua.execute('''
-- The reported crash: a valid base atlas with real_language unset.
for _,key in ipairs(SMODS.Atlas.obj_buffer) do SMODS.Atlases[key]:inject() end
assert(G.ASSET_ATLAS.mod_tags and G.ASSET_ATLAS.achievements)
local base=SMODS.Atlases.mod_tags
G.ASSET_ATLAS.mod_tags=nil
SMODS.Atlases.mod_tags_fr={}
G.SETTINGS.real_language='fr'
base:inject()
assert(G.ASSET_ATLAS.mod_tags==nil, 'localized override must suppress base atlas')
G.SETTINGS.real_language=nil
G.SETTINGS.language='fr'
base:inject()
assert(G.ASSET_ATLAS.mod_tags==nil, 'primary-language override must suppress base atlas')
G.SETTINGS.language='en-us'
base:inject()
assert(G.ASSET_ATLAS.mod_tags, 'base atlas fallback lost')
''')
assert paths
platform = z.read('browser/platform.lua').decode()
assert "require('browser.format').install()" in platform
assert z.read('main.lua').decode().startswith('require "browser.platform"')
print('Packed atlas injection passed: actual PNG paths, absent real_language, primary/real-language overrides and base fallback; shim installed before mods')
