// Supabase discovers peers; WebRTC carries the unmodified upstream JSON
// protocol. Realtime is also the ordered fallback when direct RTC is blocked.
import {randomId} from './random.js';
export class PeerRoom {
  constructor(supabase, {onPeer, onPacket, onClose, onError}) {
    Object.assign(this, {supabase, onPeer, onPacket, onClose, onError});
    this.id = randomId();
    this.nextSend = 0; this.nextReceive = 0; this.pending = new Map();
    this.ice = []; this.closed = false;
  }
  async open(code, role) {
    this.role = role;
    this.channel = this.supabase.channel('octopus-bmp-v055:'+code, {
      config:{broadcast:{ack:true,self:false},presence:{key:this.id}},
    });
    this.channel.on('broadcast',{event:'wire'},({payload})=>this.handle(payload).catch(this.onError));
    this.channel.on('presence',{event:'sync'},()=>{
      const peers=Object.values(this.channel.presenceState()).flat();
      if(role==='guest' && !this.remote) {
        const host=peers.find(p=>p.role==='host');
        if(host) this.signal('join',{},host.id).catch(this.onError);
      }
      if(this.remote) {
        if(peers.some(p=>p.id===this.remote)) this.peerSeen=true;
        else if(this.peerSeen) this.dropPeer();
      }
    });
    await new Promise((resolve,reject)=>{
      const timeout=setTimeout(()=>reject(new Error('Room connection timed out')),15000);
      this.channel.subscribe(async status=>{
        if(status==='SUBSCRIBED') {
          clearTimeout(timeout);
          try { await this.channel.track({id:this.id,role}); resolve(); }
          catch(error) {reject(error);}
        } else if(status==='CHANNEL_ERROR' || status==='TIMED_OUT') {
          clearTimeout(timeout); reject(new Error('Room connection failed'));
        }
      });
    });
    if(role==='guest') this.joinTimer=setTimeout(()=>{
      if(!this.remote) this.onError(new Error('Lobby not found or host unavailable'));
    },15000);
  }
  async signal(kind, data, to=this.remote) {
    if(this.closed) return;
    const result=await this.channel.send({type:'broadcast',event:'wire',payload:{kind,data,from:this.id,to}});
    if(result!=='ok') throw new Error('Room message was not delivered');
  }
  async handle(packet) {
    if(this.closed || !packet || packet.from===this.id || (packet.to && packet.to!==this.id)) return;
    if(packet.kind==='join' && this.role==='host') {
      if(this.remote && this.remote!==packet.from) {
        await this.signal('full',{},packet.from); return;
      }
      if(this.remote) return; // Presence sync can repeat; never rebuild an active peer.
      this.remote=packet.from;
      await this.signal('accepted',{});
      this.onPeer();
      await this.makeRTC(true).catch(error=>console.warn('WebRTC unavailable; using Realtime',error));
      return;
    }
    if(packet.kind==='accepted' && this.role==='guest' && !this.remote) {
      this.remote=packet.from; clearTimeout(this.joinTimer); this.onPeer(); return;
    }
    if(packet.kind==='full' && this.role==='guest' && !this.remote) throw new Error('Lobby is full');
    if(packet.from!==this.remote) return;
    if(packet.kind==='action') this.receive(packet.data);
    else if(packet.kind==='offer') {
      if(typeof RTCPeerConnection==='undefined') return;
      await this.makeRTC(false); await this.pc.setRemoteDescription(packet.data);
      await this.flushICE(); await this.pc.setLocalDescription(await this.pc.createAnswer());
      await this.signal('answer',this.pc.localDescription.toJSON());
    } else if(packet.kind==='answer' && this.pc) {
      await this.pc.setRemoteDescription(packet.data); await this.flushICE();
    } else if(packet.kind==='ice') {
      this.ice.push(packet.data); await this.flushICE();
    } else if(packet.kind==='leave') this.dropPeer();
  }
  async makeRTC(initiator) {
    if(typeof RTCPeerConnection==='undefined') return;
    this.pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.cloudflare.com:3478'},{urls:'stun:stun.l.google.com:19302'}]});
    this.pc.onicecandidate=e=>{if(e.candidate)this.signal('ice',e.candidate.toJSON()).catch(this.onError);};
    this.pc.ondatachannel=e=>this.bindRTC(e.channel);
    if(initiator) {
      this.bindRTC(this.pc.createDataChannel('balatro-multiplayer',{ordered:true}));
      await this.pc.setLocalDescription(await this.pc.createOffer());
      await this.signal('offer',this.pc.localDescription.toJSON());
    }
  }
  async flushICE() {
    if(!this.pc?.remoteDescription) return;
    for(const candidate of this.ice.splice(0)) await this.pc.addIceCandidate(candidate);
  }
  bindRTC(channel) {
    this.rtc=channel;
    channel.onmessage=e=>{try{this.receive(JSON.parse(e.data));}catch(error){this.onError(error);}};
  }
  receive(envelope) {
    if(!Number.isSafeInteger(envelope?.seq) || envelope.seq<this.nextReceive) return;
    if(envelope.seq>this.nextReceive+512) throw new Error('Invalid message sequence');
    this.pending.set(envelope.seq,envelope.packet);
    while(this.pending.has(this.nextReceive)) {
      const packet=this.pending.get(this.nextReceive);this.pending.delete(this.nextReceive++);
      this.onPacket(packet);
    }
  }
  async send(packet) {
    if(!this.remote) throw new Error('Peer is not connected');
    const envelope={seq:this.nextSend++,packet};
    // Realtime copy provides recovery if RTC closes after accepting send().
    // Sequence numbers deduplicate and order the two paths before dispatch.
    if(this.rtc?.readyState==='open') this.rtc.send(JSON.stringify(envelope));
    await this.signal('action',envelope);
  }
  dropPeer() {
    if(!this.remote) return;
    this.remote=null;this.peerSeen=false;
    this.rtc?.close();this.pc?.close();this.rtc=null;this.pc=null;
    this.nextSend=0;this.nextReceive=0;this.pending.clear();this.ice=[];
    this.onClose();
  }
  async close() {
    clearTimeout(this.joinTimer);
    if(this.remote) await this.signal('leave',{}).catch(()=>{});
    this.closed=true;this.rtc?.close();this.pc?.close();
    if(this.channel) await this.supabase.removeChannel(this.channel);
  }
}
