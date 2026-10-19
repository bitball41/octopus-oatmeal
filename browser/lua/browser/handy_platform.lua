-- Standalone Handy on the Vanilla browser base; no Steamodded/save migration.
require('browser.vanilla')
_G.load = loadstring or load
package.loaded['handy/nativefs'] = require('browser.nativefs')
package.loaded.lovely = {
    version='0.9.0', mod_dir='Mods', log_path='browser.log',
}
