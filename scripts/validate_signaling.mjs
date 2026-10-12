import assert from 'node:assert/strict';
import {PeerRoom} from '../browser/transport.js';

function fixture() {
  const errors=[],removed=[];
  let callback;
  const channel={
    on(){return this;},subscribe(fn){callback=fn;return this;},
    async track(){return 'ok';},presenceState(){return {};},
  };
  const client={channel(){return channel;},async removeChannel(value){removed.push(value);await callback('CLOSED');}};
  const room=new PeerRoom(client,{onPeer(){},onPacket(){},onClose(){},onError:error=>errors.push(error),connectionTimeoutMs:40,presenceRetryDelayMs:1});
  return {room,channel,errors,removed,emit:(status,error)=>callback(status,error)};
}

{
  const f=fixture();
  let tracks=0;
  f.channel.track=async()=>++tracks===1?'timed out':'ok';
  const opened=f.room.open('test','host');
  await f.emit('SUBSCRIBED');
  await opened;
  assert.equal(tracks,2,'a lost initial presence ACK must retry within the same deadline');
  assert.equal(f.errors.length,0);
  await f.room.close();
}

{
  const f=fixture();
  const opened=f.room.open('test','host');
  await f.emit('CHANNEL_ERROR',new Error('channel error: transport failure'));
  await f.emit('SUBSCRIBED');
  await opened;
  assert.equal(f.room.status.presence,'ok');
  assert.equal(f.errors.length,0);
  await f.room.close();
  assert.equal(f.removed.length,1);
  assert.equal(f.errors.length,0,'intentional close must remain quiet');
}

{
  const f=fixture();
  const opened=f.room.open('test','host');
  const rejected=assert.rejects(opened,/transport failure/);
  await f.emit('CHANNEL_ERROR',new Error('channel error: transport failure'));
  await f.emit('TIMED_OUT',new Error('channel error: transport failure'));
  await rejected;
  assert.equal(f.room.closed,true);
  assert.equal(f.removed.length,1,'failed room must release its channel');
  assert.equal(f.errors.length,0,'initial failure is returned once to the bridge');
  await f.emit('SUBSCRIBED');
  assert.equal(f.room.status.presence,'idle','a late retry cannot revive a failed room');
}

{
  const f=fixture();
  const opened=f.room.open('test','host');
  const rejected=assert.rejects(opened,/Unauthorized/);
  await f.emit('CHANNEL_ERROR',new Error('Unauthorized: permission denied'));
  await rejected;
  assert.equal(f.room.closed,true,'authorization failures do not wait for transport recovery');
  assert.equal(f.removed.length,1);
}

{
  const f=fixture();
  const opened=f.room.open('test','host');
  const rejected=assert.rejects(opened,{name:'AbortError'});
  await f.room.close();
  await rejected;
  assert.equal(f.room.closed,true);
  assert.equal(f.errors.length,0);
  assert.equal(f.removed.length,1);
  assert.equal(f.room.openTimer,null);
}

console.log('Signaling: transient recovery, lost presence ACK, bounded failure, channel cleanup, fatal authorization and cancellation passed');
