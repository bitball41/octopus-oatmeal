import {build} from 'esbuild';
await build({entryPoints:['browser/custom-runtime.js'],outfile:'custom-runtime.js',bundle:true,format:'iife',target:'es2022',minify:true,legalComments:'inline'});
