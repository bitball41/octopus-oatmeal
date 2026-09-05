// Browser entry point for the pinned upstream server. Scoring, timers, lives,
// lobby settings, ready/start and win/loss dispatch all remain upstream.
import Client from '../build/upstream-server/src/Client.ts';
import { actionHandlers, disconnectFromLobbyAction } from '../build/upstream-server/src/actionHandlers.ts';
import { Lobbies } from '../build/upstream-server/src/Lobby.ts';

export class BrowserServer {
  constructor() { this.clients = new Map(); }
  connect(id, send) {
    if (this.clients.has(id)) throw new Error('Connection already exists');
    const client = new Client({}, send, () => this.disconnect(id));
    this.clients.set(id, client);
    send({action:'connected'});
    send({action:'version'});
    return client;
  }
  dispatch(id, packet) {
    const client = this.clients.get(id);
    if (!client) throw new Error('Connection is not established');
    if (!packet || typeof packet.action !== 'string') throw new Error('Invalid action');
    if (!Object.hasOwn(actionHandlers, packet.action)) return;
    // Never let a second peer take an occupied guest slot or create unrelated
    // lobbies on the host. The host's existing lobby is the network boundary.
    const handler = actionHandlers[packet.action];
    if (handler.length === 1) handler(client);
    else handler(packet, client);
  }
  disconnect(id) {
    const client = this.clients.get(id);
    if (!client) return;
    disconnectFromLobbyAction(client);
    this.clients.delete(id);
  }
  close() {
    for (const id of this.clients.keys()) this.disconnect(id);
    for (const [code, lobby] of Lobbies) {
      if (lobby.disconnectedSlot) clearTimeout(lobby.disconnectedSlot.timer);
      Lobbies.delete(code);
    }
  }
}
