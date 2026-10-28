import {installClipboard} from './clipboard.js';
import {createClient} from '@supabase/supabase-js';
import {BrowserServer} from './server.js';
import {PeerRoom} from './transport.js';

const SUPABASE_URL='https://trsirhyucncmyyfyiuje.supabase.co';
// Public Realtime rooms use Liminal's publishable key without a persisted Auth session.
const SUPABASE_PUBLISHABLE_KEY='sb_publishable_IRSgHfkgRkLvRYcoKkwAqA_UFpMAetG';
const supabase=createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false},
  realtime:{params:{apikey:SUPABASE_PUBLISHABLE_KEY}},
});
let saveDirectory, server, room, role, joiningCode;
let sequence=0, pending=[], operation=Promise.resolve();
installClipboard(() => saveDirectory);
const handshake=new Map();
const diagnostics={luaToJS:0,jsToLua:0,lastLuaAction:null,lastDeliveredAction:null,lastError:null};

function deliver(packet) {
  if(!saveDirectory || typeof window.Module?.FS_createDataFile!=='function') {pending.push(packet);return;}
  const name='octopus_upstream_'+String(sequence++).padStart(12,'0')+'.json';
  window.Module.FS_createDataFile(saveDirectory,name,new TextEncoder().encode(JSON.stringify(packet)),true,true,true);
  diagnostics.jsToLua++;diagnostics.lastDeliveredAction=packet.action;
}
function fail(error) {
  if(error.name==='AbortError') return;
  diagnostics.lastError=error.message||String(error);
  console.error('[Octopus upstream]',error);
  deliver({action:'error',message:error.message||String(error)});
}
function makeRoom() {
  const peer = new PeerRoom(supabase,{
    onPeer(){
      if(role==='host') server.connect('guest',packet=>room.send(packet).catch(fail));
      else {
        for(const packet of handshake.values()) room.send(packet).catch(fail);
        room.send({action:'joinLobby',code:joiningCode}).catch(fail);
      }
    },
    onPacket(packet){
      const expected=window.__octopusBuild?.identity || 'vanilla-mp';
      const actual=packet.octopusBuild || 'vanilla-mp';
      if(actual!==expected) {
        const error=new Error('Build mismatch. Both players must select the same mods and randomizer minimum/maximum.');
        fail(error);
        return;
      }
      if(role==='host') {
        if(packet.action==='createLobby' || (packet.action==='joinLobby' && packet.code!==server.clients.get('local')?.lobby?.code)) return;
        try {server.dispatch('guest',packet);}catch(error){
          const message='Upstream '+packet.action+' failed: '+error.message;
          room.send({action:'error',message}).catch(fail);fail(new Error(message));
        }
      } else deliver(packet);
    },
    onClose(){
      if(role==='host') server.disconnect('guest');
      else deliver({action:'disconnected'});
    },
    onError:fail,
  });
  const send=peer.send.bind(peer);
  peer.send=packet=>send({...packet,octopusBuild:window.__octopusBuild?.identity || 'vanilla-mp'});
  return peer;
}
async function openRoom(candidate,code,desiredRole) {
  try {await candidate.open(code,desiredRole);}
  catch(error) {
    await candidate.close().catch(()=>{});
    if(room===candidate) {
      room=null;role=null;server?.close();server=null;
    }
    throw error;
  }
}
function bootLocal() {
  if(server) return;
  server=new BrowserServer();
  server.connect('local',packet=>{
    if(packet.action==='joinedLobby') {
      role='host';const candidate=makeRoom();room=candidate;
      openRoom(candidate,packet.code,'host').then(()=>{
        if(room===candidate) deliver(packet);
      }).catch(fail);
    } else deliver(packet);
  });
  for(const packet of handshake.values()) server.dispatch('local',packet);
}
async function send(message) {
  const packet=JSON.parse(message);
  diagnostics.luaToJS++;diagnostics.lastLuaAction=packet.action;
  if(packet.action==='connect') {
    // A peer-hosted room ends when its host leaves. Reconnect returns this
    // client to its own local lobby service, not a dead remote data channel.
    if(role==='guest' && !room?.remote) {
      await room?.close();room=null;role=null;server?.close();server=null;
    }
    bootLocal();return;
  }
  if(packet.action==='username' || packet.action==='version') handshake.set(packet.action,packet);
  if(packet.action==='joinLobby' && role!=='host') {
    joiningCode=String(packet.code||'').trim().toUpperCase();
    if(!/^[A-Z]{5}$/.test(joiningCode)) throw new Error('Enter the five-letter lobby code');
    if(room) await room.close();
    server?.close();server=null;role='guest';room=makeRoom();
    await openRoom(room,joiningCode,'guest');return;
  }
  if(role==='guest') {
    if(!room?.remote) throw new Error('Cannot send '+packet.action+': peer is not connected');
    await room.send(packet);
  } else {bootLocal();server.dispatch('local',packet);}
  if(packet.action==='leaveLobby') {
    await room?.close();room=null;role=null;server?.close();server=null;bootLocal();
  }
}

const queued=window.OctopusMP?._pending||[];
window.OctopusMP={
  diagnostics(){return JSON.parse(JSON.stringify({...diagnostics,role,transport:room?.status,
    sent:room?.nextSend,received:room?.nextReceive,pending:room?.pending.size}));},
  attach(path){saveDirectory=path;for(const packet of pending.splice(0))deliver(packet);},
  send(message){operation=operation.then(()=>send(message)).catch(fail);},
};
for(const [method,args] of queued) window.OctopusMP[method](...args);
window.addEventListener('beforeunload',()=>{room?.close();server?.close();});
