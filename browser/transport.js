// Supabase discovers peers; WebRTC carries the unmodified upstream JSON
// protocol. Realtime is also the ordered fallback when direct RTC is blocked.
import {randomId} from './random.js';
export class PeerRoom {
  constructor(supabase, {onPeer, onPacket, onClose, onError, connectionTimeoutMs=15000, presenceRetryDelayMs=500}) {
    Object.assign(this, {supabase, onPeer, onPacket, onClose, onError, connectionTimeoutMs, presenceRetryDelayMs});
    this.id = randomId();
    this.nextSend = 0; this.nextReceive = 0; this.pending = new Map();
    this.ice = []; this.closed = false;
    this.incoming = Promise.resolve();
    this.status = {subscription:'CLOSED', presence:'idle', peer:'waiting', rtc:'new', dataChannel:'none', signalsSent:{}, signalsReceived:{}};
  }
  enqueue(packet) {
    // A broadcast can arrive before the previous send's server ACK. In
    // particular, accepted -> username/join must finish registering the guest
    // before dispatch. Also serialize offer/answer and early ICE candidates.
    this.incoming = this.incoming.then(()=>this.handle(packet)).catch(this.onError);
    return this.incoming;
  }
  async open(code, role) {
    this.role = role;
    this.channel = this.supabase.channel('octopus-bmp-v055:'+code, {
      config:{broadcast:{ack:true,self:false},presence:{key:this.id}},
    });
    this.channel.on('broadcast',{event:'wire'},({payload})=>this.enqueue(payload));
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
      let opened=false, failed=false, tracking=false, lastFailure;
      const failOpen=error=>{
        if(failed || this.closed) return;
        failed=true;clearTimeout(this.openTimer);this.openTimer=null;
        reject(error);
        this.close().catch(()=>{});
      };
      // Supabase retries a dropped transport itself. An initial socket error
      // is not a failed lobby until the bounded connection window expires.
      this.openTimer=setTimeout(()=>failOpen(lastFailure || new Error('Room connection timed out')),this.connectionTimeoutMs);
      this.cancelOpen=()=>{
        if(opened || failed) return;
        failed=true;
        reject(Object.assign(new Error('Room connection closed'),{name:'AbortError'}));
      };
      const trackPresence=async()=>{
        if(this.closed || failed || tracking) return;
        tracking=true;
        try {
            const result=await this.channel.track({id:this.id,role});
            if(this.closed || failed) return;
            this.status.presence=result;
            if(result==='timed out' && !opened) {
              lastFailure=new Error('Presence tracking failed: timed out');
              this.trackRetry=setTimeout(()=>{
                this.trackRetry=null;
                if(this.status.subscription==='SUBSCRIBED') trackPresence();
              },this.presenceRetryDelayMs);
              return;
            }
            if(result!=='ok') throw new Error('Presence tracking failed: '+result);
            clearTimeout(this.openTimer);clearTimeout(this.trackRetry);this.openTimer=null;this.trackRetry=null;this.cancelOpen=null;
            opened=true;resolve();
        } catch(error) {
            if(opened) this.onError(error);
            else failOpen(error);
        } finally {tracking=false;}
      };
      this.channel.subscribe((status,error)=>{
        this.status.subscription=status;
        if(this.closed || failed) return;
        if(status==='SUBSCRIBED') trackPresence();
        else if(status==='CHANNEL_ERROR' || status==='TIMED_OUT' || status==='CLOSED') {
          const failure=new Error('Signaling '+status+(error?.message ? ': '+error.message : ''),{cause:error});
          if(opened) this.onError(failure);
          else if(/unauthori[sz]ed|permission|invalid.*(?:jwt|token)|(?:jwt|token).*(?:invalid|expired)/i.test(error?.message || '')) failOpen(failure);
          else lastFailure=failure;
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
    if(result!=='ok') throw new Error('Signaling '+kind+' failed: '+result);
    this.status.signalsSent[kind]=(this.status.signalsSent[kind]||0)+1;
  }
  async handle(packet) {
    if(this.closed || !packet || packet.from===this.id || (packet.to && packet.to!==this.id)) return;
    this.status.signalsReceived[packet.kind]=(this.status.signalsReceived[packet.kind]||0)+1;
    if(packet.kind==='join' && this.role==='host') {
      if(this.remote && this.remote!==packet.from) {
        await this.signal('full',{},packet.from); return;
      }
      if(this.remote) return; // Presence sync can repeat; never rebuild an active peer.
      this.remote=packet.from;
      await this.signal('accepted',{});
      if(this.closed) return;
      this.status.peer='accepted';
      this.onPeer();
      await this.makeRTC(true).catch(error=>{this.status.rtc='failed: '+error.message;});
      return;
    }
    if(packet.kind==='accepted' && this.role==='guest' && !this.remote) {
      this.remote=packet.from; this.status.peer='accepted';clearTimeout(this.joinTimer); this.onPeer(); return;
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
    if(typeof RTCPeerConnection==='undefined') {this.status.rtc='unavailable';return;}
    this.pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.cloudflare.com:3478'},{urls:'stun:stun.l.google.com:19302'}]});
    this.pc.onconnectionstatechange=()=>{this.status.rtc=this.pc?.connectionState||'closed';};
    this.pc.oniceconnectionstatechange=()=>{this.status.ice=this.pc?.iceConnectionState||'closed';};
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
    this.status.dataChannel=channel.readyState;
    channel.onopen=()=>{this.status.dataChannel='open';};
    channel.onclose=()=>{this.status.dataChannel='closed';};
    channel.onerror=()=>{this.status.dataChannel='error';};
    channel.onmessage=e=>{
      try {this.enqueue({kind:'action',from:this.remote,to:this.id,data:JSON.parse(e.data)});}
      catch(error){this.onError(error);}
    };
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
    const envelope={seq:this.nextSend++,packet:JSON.parse(JSON.stringify(packet))};
    // Realtime copy provides recovery if RTC closes after accepting send().
    // Sequence numbers deduplicate and order the two paths before dispatch.
    if(this.rtc?.readyState==='open') {
      try {this.rtc.send(JSON.stringify(envelope));}
      catch(error) {this.status.dataChannel='send failed: '+error.message;}
    }
    await this.signal('action',envelope);
  }
  dropPeer() {
    if(!this.remote) return;
    this.remote=null;this.peerSeen=false;
    this.status.peer='disconnected';
    this.rtc?.close();this.pc?.close();this.rtc=null;this.pc=null;
    this.nextSend=0;this.nextReceive=0;this.pending.clear();this.ice=[];
    this.onClose();
  }
  async close() {
    if(this.closed) return;
    const leave=this.remote ? this.signal('leave',{}).catch(()=>{}) : Promise.resolve();
    this.closed=true;this.rtc?.close();this.pc?.close();
    clearTimeout(this.joinTimer);clearTimeout(this.openTimer);clearTimeout(this.trackRetry);this.openTimer=null;this.trackRetry=null;this.cancelOpen?.();this.cancelOpen=null;
    await leave;
    if(this.channel) await this.supabase.removeChannel(this.channel);
  }
}
