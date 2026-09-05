import {createClient} from '@supabase/supabase-js';
import {BrowserServer} from './server.js';
import {PeerRoom} from './transport.js';

const supabase=createClient('https://yswxdsagoywzevwgarbf.supabase.co',
  'sb_publishable_Ah6QGx7Tpr-rBvaa4cQcPw_7djryJ9K',
  {auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});
let saveDirectory, server, room, role, joiningCode;
let sequence=0, pending=[], operation=Promise.resolve();
const handshake=new Map();

function deliver(packet) {
  if(!saveDirectory || typeof window.Module?.FS_createDataFile!=='function') {pending.push(packet);return;}
  const name='octopus_upstream_'+String(sequence++).padStart(12,'0')+'.json';
  window.Module.FS_createDataFile(saveDirectory,name,new TextEncoder().encode(JSON.stringify(packet)),true,true,true);
}
function fail(error) {
  console.error('[Octopus upstream]',error);
  deliver({action:'error',message:error.message||String(error)});
}
function makeRoom() {
  return new PeerRoom(supabase,{
    onPeer(){
      if(role==='host') server.connect('guest',packet=>room.send(packet).catch(fail));
      else {
        for(const packet of handshake.values()) room.send(packet).catch(fail);
        room.send({action:'joinLobby',code:joiningCode}).catch(fail);
      }
    },
    onPacket(packet){
      if(role==='host') {
        if(packet.action==='createLobby' || (packet.action==='joinLobby' && packet.code!==server.clients.get('local')?.lobby?.code)) return;
        try {server.dispatch('guest',packet);}catch(error){room.send({action:'error',message:'Invalid client action'}).catch(fail);console.error(error);}
      } else deliver(packet);
    },
    onClose(){
      if(role==='host') server.disconnect('guest');
      else deliver({action:'disconnected'});
    },
    onError:fail,
  });
}
function bootLocal() {
  if(server) return;
  server=new BrowserServer();
  server.connect('local',packet=>{
    if(packet.action==='joinedLobby') {
      role='host';room=makeRoom();
      room.open(packet.code,'host').then(()=>deliver(packet)).catch(fail);
    } else deliver(packet);
  });
}
async function send(message) {
  const packet=JSON.parse(message);
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
    await room.open(joiningCode,'guest');return;
  }
  if(role==='guest') {
    if(room?.remote) await room.send(packet);
  } else {bootLocal();server.dispatch('local',packet);}
  if(packet.action==='leaveLobby') {
    await room?.close();room=null;role=null;server?.close();server=null;bootLocal();
  }
}

const queued=window.OctopusMP?._pending||[];
window.OctopusMP={
  attach(path){saveDirectory=path;for(const packet of pending.splice(0))deliver(packet);},
  send(message){operation=operation.then(()=>send(message)).catch(fail);},
};
for(const [method,args] of queued) window.OctopusMP[method](...args);
window.addEventListener('beforeunload',()=>{room?.close();server?.close();});
