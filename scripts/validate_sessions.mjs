// The real bridge and pinned upstream server, with a deterministic Realtime
// wire whose delivery precedes ACK (the production handshake race).
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {build} from 'esbuild';
import {resolve} from 'node:path';
import {PeerRoom} from '../browser/transport.js';
const bundle=await build({entryPoints:['browser/bridge.js'],bundle:true,write:false,format:'iife',platform:'browser',plugins:[{
  name:'test-boundaries',setup(b){
    b.onResolve({filter:/^@supabase\/supabase-js$/},()=>({path:'supabase',namespace:'test'}));
    b.onLoad({filter:/.*/,namespace:'test'},()=>({contents:'export const createClient=()=>globalThis.testSupabase;'}));
    b.onResolve({filter:/^\.\/server.js$/},()=>({path:resolve('browser/upstream-server.js')}));
  }
}]});
const tick=()=>new Promise(r=>setTimeout(r,2));
async function until(check,label){for(let i=0;i<300;i++){if(check())return;await tick();}throw new Error('Timeout: '+label);}
const channels=[];
let delayedAccept=false;
const fakeSupabase={
  channel(topic){
    const c={topic,handlers:{},state:{},active:false,
      on(type,{event},fn){this.handlers[type+':'+event]=fn;return this;},
      subscribe(fn){this.status=fn;this.active=true;queueMicrotask(()=>fn('SUBSCRIBED'));return this;},
      async track(state){this.state=state;sync();return 'ok';},
      presenceState(){return Object.fromEntries(channels.filter(x=>x.active&&x.topic===topic&&x.state.id).map(x=>[x.state.id,[x.state]]));},
      async send({payload}){
        for(const other of channels.filter(x=>x!==this&&x.active&&x.topic===topic)) {
          other.handlers['broadcast:wire']?.({payload:structuredClone(payload)});
        }
        if(payload.kind==='accepted'){delayedAccept=true;await new Promise(r=>setTimeout(r,15));}
        return 'ok';
      },
    };channels.push(c);return c;
  },
  async removeChannel(c){c.active=false;sync();c.status('CLOSED');},
};
function sync(){for(const c of channels.filter(x=>x.active))queueMicrotask(()=>c.handlers['presence:sync']?.());}
function client(){
  const inbox=[],errors=[];
  const context={testSupabase:fakeSupabase,crypto:globalThis.crypto,TextEncoder,setTimeout,clearTimeout,
    console:{log(){},warn(){},error(...args){errors.push(args);}},
    Module:{FS_createDataFile(path,name,bytes){inbox.push(JSON.parse(new TextDecoder().decode(bytes)));}},
    addEventListener(){}};
  context.window=context;vm.runInNewContext(bundle.outputFiles[0].text,context);
  const bridge=context.OctopusMP;bridge.attach('/save');
  return {bridge,inbox,errors,send(packet){bridge.send(JSON.stringify(packet));}};
}
const host=client(),guest=client();
for(const [c,name] of [[host,'Host'],[guest,'Guest']]){
  c.send({action:'connect'});c.send({action:'username',username:name+'~1',modHash:'test'});
  c.send({action:'version',version:'0.5.5'});
}
host.send({action:'createLobby',gameMode:'attrition'});
await until(()=>host.inbox.some(p=>p.action==='joinedLobby'),'host lobby');
const code=host.inbox.find(p=>p.action==='joinedLobby').code;
guest.send({action:'joinLobby',code});
await until(()=>guest.inbox.some(p=>p.action==='joinedLobby'),'guest joined');
assert(delayedAccept);
assert.equal(host.errors.length,0,JSON.stringify(host.errors));
assert.equal(guest.errors.length,0,JSON.stringify(guest.errors));
assert.equal(guest.inbox.find(p=>p.action==='lobbyInfo').isHost,false,'guest must not be promoted by shared packet mutation');
guest.send({action:'readyLobby'});
await until(()=>host.inbox.some(p=>p.action==='lobbyInfo'&&p.guestReady===true),'ready synchronization');
host.send({action:'startGame'});
await until(()=>guest.inbox.some(p=>p.action==='startGame'),'run start');
assert.equal(host.inbox.find(p=>p.action==='startGame').seed,guest.inbox.find(p=>p.action==='startGame').seed);
assert.equal(guest.bridge.diagnostics().pending,0);
guest.send({action:'leaveLobby'});
await until(()=>host.inbox.some(p=>p.action==='lobbyInfo'&&!p.guest),'guest leave');
host.send({action:'leaveLobby'});
await until(()=>channels.every(c=>!c.active),'cleanup');
console.log('Actual bridge + upstream server: delayed-ACK handshake, usernames, guest role, ready, shared run seed and leave passed');

// Focused negotiation and fallback checks, including ICE arriving before SDP.
const errors=[],received=[],sent=[];
class RTC {
  constructor(){this.connectionState='new';this.iceConnectionState='new';this.candidates=[];}
  async setRemoteDescription(s){assert(s.type);this.remoteDescription=s;}
  async createAnswer(){return {type:'answer',sdp:'answer'};}
  async setLocalDescription(s){this.localDescription={...s,toJSON(){return s;}};}
  async addIceCandidate(c){assert(this.remoteDescription);this.candidates.push(c);}
  close(){}
}
globalThis.RTCPeerConnection=RTC;
const peer=new PeerRoom({}, {onPeer(){},onPacket:p=>received.push(p),onClose(){},onError:e=>errors.push(e)});
peer.role='guest';peer.remote='host';peer.channel={async send(p){sent.push(p);return 'ok';}};
await peer.enqueue({kind:'ice',from:'host',data:{candidate:'early'}});
await peer.enqueue({kind:'offer',from:'host',data:{type:'offer',sdp:'offer'}});
assert.equal(peer.pc.candidates.length,1);assert.equal(sent.at(-1).payload.kind,'answer');
const rtc={readyState:'open',send(){throw new Error('channel closed during send');},close(){}};
peer.bindRTC(rtc);rtc.onopen();assert.equal(peer.status.dataChannel,'open');
await peer.send({action:'readyLobby'});
assert.equal(sent.at(-1).payload.kind,'action','RTC failure must still send Realtime fallback');
peer.receive({seq:1,packet:{action:'second'}});peer.receive({seq:0,packet:{action:'first'}});
peer.receive({seq:0,packet:{action:'first'}});
assert.deepEqual(received.map(p=>p.action),['first','second']);
assert.equal(errors.length,0);
delete globalThis.RTCPeerConnection;
console.log('Transport: early ICE, offer/answer, channel-open state, failed-RTC fallback and ordered deduplication passed');
