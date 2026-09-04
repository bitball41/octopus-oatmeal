import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.112.4/+esm";

const SUPABASE_URL = "https://yswxdsagoywzevwgarbf.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_Ah6QGx7Tpr-rBvaa4cQcPw_7djryJ9K";

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
    detectSessionInUrl: false,
  },
});

const previousBridge = window.OctopusMultiplayer || {};
const pendingBridgeCalls = Array.isArray(previousBridge._pending)
  ? [...previousBridge._pending]
  : [];

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();
const peerId = crypto.randomUUID();

let role = null;
let lobbyCode = null;
let signalChannel = null;
let remotePeerId = null;
let peerConnection = null;
let dataChannel = null;
let saveDirectory = null;
let inboxCounter = 0;
let pendingInbox = [];
let connectionTimer = null;
let awardedRounds = new Set();

const localRounds = new Map();
const remoteRounds = new Map();

const state = {
  status: "OFFLINE",
  role: "",
  lobbyCode: "",
  opponentScore: 0,
};

function normalizeLobbyCode(value) {
  return String(value || "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 6);
}

function generateLobbyCode() {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(6));
  let code = "";
  for (const byte of bytes) code += alphabet[byte % alphabet.length];
  return code;
}

function decodeBase64Utf8(value) {
  if (!value) return "";
  const binary = atob(value);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  return textDecoder.decode(bytes);
}

function encodeBase64Utf8(value) {
  const bytes = textEncoder.encode(String(value ?? ""));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function updateState(patch) {
  Object.assign(state, patch);
  writeInboxMessage(
    "lobby_state",
    state.status,
    state.lobbyCode || "",
    state.role || "",
    String(state.opponentScore || 0),
  );
}

async function closePeerOnly() {
  if (connectionTimer) {
    clearTimeout(connectionTimer);
    connectionTimer = null;
  }
  if (dataChannel) {
    try { dataChannel.close(); } catch (_) {}
    dataChannel = null;
  }
  if (peerConnection) {
    try { peerConnection.close(); } catch (_) {}
    peerConnection = null;
  }
  remotePeerId = null;
}

async function leaveLobby({ quiet = false } = {}) {
  await closePeerOnly();
  if (signalChannel) {
    try { await signalChannel.untrack(); } catch (_) {}
    try { await supabase.removeChannel(signalChannel); } catch (_) {}
    signalChannel = null;
  }
  role = null;
  lobbyCode = null;
  localRounds.clear();
  remoteRounds.clear();
  awardedRounds.clear();
  updateState({ status: "OFFLINE", role: "", lobbyCode: "", opponentScore: 0 });
  writeInboxMessage("mp_disconnected", "0");
  if (!quiet) writeInboxMessage("notice", "Left multiplayer lobby");
}

async function openSignaling(code, desiredRole) {
  await leaveLobby({ quiet: true });
  role = desiredRole;
  lobbyCode = code;
  updateState({
    status: desiredRole === "host" ? "WAITING FOR PLAYER" : "JOINING...",
    role,
    lobbyCode: code,
    opponentScore: 0,
  });

  signalChannel = supabase.channel(`octopus-balatro:${code}`, {
    config: {
      broadcast: { ack: true, self: false },
      presence: { key: peerId },
    },
  });

  signalChannel
    .on("broadcast", { event: "signal" }, ({ payload }) => handleSignal(payload))
    .on("presence", { event: "sync" }, () => {
      if (role !== "guest" || remotePeerId) return;
      const presence = signalChannel.presenceState();
      for (const entries of Object.values(presence)) {
        for (const entry of entries) {
          if (entry?.role === "host" && entry?.peerId !== peerId) {
            sendSignal("join", entry.peerId, {});
            return;
          }
        }
      }
    })
    .subscribe(async (status) => {
      if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
        updateState({ status: "SIGNALING ERROR" });
        writeInboxMessage("notice", "Could not connect to Supabase Realtime");
        return;
      }
      if (status !== "SUBSCRIBED") return;
      await signalChannel.track({ peerId, role, joinedAt: Date.now() });
      if (role === "guest") await sendSignal("join", null, {});
    });
}

async function createLobby() {
  const code = generateLobbyCode();
  await openSignaling(code, "host");
  return code;
}

async function joinLobby(code) {
  code = normalizeLobbyCode(code);
  if (code.length !== 6) throw new Error("Invalid lobby code");
  await openSignaling(code, "guest");
}

async function joinLobbyEncoded(encodedPacket) {
  const encoded = String(encodedPacket || "").split(".")[0] || "";
  return joinLobby(decodeBase64Utf8(encoded));
}

async function sendSignal(kind, to, data) {
  if (!signalChannel) return;
  await signalChannel.send({
    type: "broadcast",
    event: "signal",
    payload: { kind, from: peerId, to: to || null, data: data || {} },
  });
}

function rtcConfig() {
  return {
    iceServers: [
      { urls: "stun:stun.cloudflare.com:3478" },
      { urls: "stun:stun.l.google.com:19302" },
    ],
  };
}

async function makePeer(initiator, targetPeerId) {
  await closePeerOnly();
  remotePeerId = targetPeerId;
  peerConnection = new RTCPeerConnection(rtcConfig());

  peerConnection.onicecandidate = ({ candidate }) => {
    if (candidate) sendSignal("ice", remotePeerId, { candidate });
  };

  peerConnection.onconnectionstatechange = () => {
    const current = peerConnection?.connectionState;
    if (current === "failed") {
      updateState({ status: "P2P FAILED" });
      writeInboxMessage("notice", "Direct P2P failed; this network may require TURN");
    } else if (current === "disconnected" || current === "closed") {
      updateState({ status: "PEER DISCONNECTED" });
    }
  };

  if (initiator) {
    bindDataChannel(peerConnection.createDataChannel("balatro-versus", { ordered: true }));
  } else {
    peerConnection.ondatachannel = (event) => bindDataChannel(event.channel);
  }

  connectionTimer = setTimeout(() => {
    if (!dataChannel || dataChannel.readyState !== "open") {
      updateState({ status: "P2P TIMEOUT" });
      writeInboxMessage("notice", "Could not make a direct P2P connection");
    }
  }, 18000);

  return peerConnection;
}

function bindDataChannel(channel) {
  dataChannel = channel;
  dataChannel.onopen = () => {
    if (connectionTimer) clearTimeout(connectionTimer);
    connectionTimer = null;
    updateState({ status: "CONNECTED" });
    writeInboxMessage("mp_connected", role || "peer", lobbyCode || "------");
  };
  dataChannel.onclose = () => {
    updateState({ status: "PEER DISCONNECTED" });
    writeInboxMessage("mp_disconnected", "0");
  };
  dataChannel.onerror = (error) => console.error("[Octopus MP] data channel error", error);
  dataChannel.onmessage = ({ data }) => {
    try {
      handleGameMessage(JSON.parse(data));
    } catch (error) {
      console.error("[Octopus MP] invalid peer packet", error);
    }
  };
}

async function handleSignal(payload) {
  if (!payload || payload.from === peerId) return;
  if (payload.to && payload.to !== peerId) return;

  if (payload.kind === "join" && role === "host") {
    const pc = await makePeer(true, payload.from);
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await sendSignal("offer", payload.from, { description: pc.localDescription });
    return;
  }

  if (payload.kind === "offer" && role === "guest") {
    const pc = await makePeer(false, payload.from);
    await pc.setRemoteDescription(payload.data.description);
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    await sendSignal("answer", payload.from, { description: pc.localDescription });
    return;
  }

  if (payload.kind === "answer" && role === "host" && peerConnection) {
    await peerConnection.setRemoteDescription(payload.data.description);
    return;
  }

  if (payload.kind === "ice" && peerConnection && payload.data?.candidate) {
    try {
      await peerConnection.addIceCandidate(payload.data.candidate);
    } catch (error) {
      console.warn("[Octopus MP] ICE candidate rejected", error);
    }
  }
}

function sendGameMessage(type, payload) {
  if (!dataChannel || dataChannel.readyState !== "open") return false;
  dataChannel.send(JSON.stringify({ version: 1, type, from: peerId, payload }));
  return true;
}

function handleGameMessage(message) {
  if (!message || message.version !== 1 || !message.type) return;
  const payload = message.payload || {};

  switch (message.type) {
    case "start_game":
      writeInboxMessage("start_game", payload.seed, payload.stake, payload.deck);
      break;
    case "score":
      updateState({ opponentScore: Number(payload.score) || 0 });
      writeInboxMessage("opponent_score", payload.blind, payload.score);
      break;
    case "round_end":
      remoteRounds.set(String(payload.blind), {
        score: Number(payload.score) || 0,
        gameOver: !!payload.gameOver,
        peerId: message.from,
      });
      maybeAwardRound(String(payload.blind));
      break;
    case "award":
      applyAwardPacket(payload);
      break;
  }
}

function hashString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function rewardForRound(blind) {
  const seed = hashString(`${lobbyCode || ""}:${blind}`);
  const pick = seed % 3;
  if (pick === 0) return { type: "money", value: 4 + (seed % 4) };
  if (pick === 1) return { type: "consumable", value: 0 };
  return { type: "joker", value: 0 };
}

function maybeAwardRound(blind) {
  if (role !== "host" || awardedRounds.has(blind)) return;
  const local = localRounds.get(blind);
  const remote = remoteRounds.get(blind);
  if (!local || !remote) return;

  awardedRounds.add(blind);
  let winner = null;
  if (local.score > remote.score) winner = peerId;
  if (remote.score > local.score) winner = remote.peerId || remotePeerId;

  const reward = winner ? rewardForRound(blind) : { type: "none", value: 0 };
  const packet = { blind, winner, reward };
  applyAwardPacket(packet);
  sendGameMessage("award", packet);
}

function applyAwardPacket(packet) {
  const blind = String(packet.blind);
  const winner = packet.winner || null;
  const reward = packet.reward || { type: "none", value: 0 };
  writeInboxMessage(
    "award",
    blind,
    winner === peerId ? "1" : "0",
    reward.type,
    reward.value ?? 0,
  );
}

function writeInboxMessage(type, ...fields) {
  const packet = [type, ...fields.map((value) => String(value ?? ""))]
    .map(encodeBase64Utf8)
    .join(".");

  if (!saveDirectory || !window.Module || typeof window.Module.FS_createDataFile !== "function") {
    pendingInbox.push(packet);
    return;
  }

  const name = `octopus_mp_inbox_${Date.now()}_${String(inboxCounter++).padStart(5, "0")}.txt`;
  try {
    window.Module.FS_createDataFile(
      saveDirectory,
      name,
      textEncoder.encode(packet),
      true,
      true,
      true,
    );
  } catch (error) {
    console.error("[Octopus MP] could not write Lua inbox file", error);
  }
}

function flushInbox() {
  if (!saveDirectory || !window.Module || typeof window.Module.FS_createDataFile !== "function") return;
  const queued = pendingInbox;
  pendingInbox = [];
  for (const packet of queued) {
    const parts = packet.split(".").map(decodeBase64Utf8);
    writeInboxMessage(parts[0], ...parts.slice(1));
  }
}

function fromLuaEncoded(encodedPacket) {
  const parts = String(encodedPacket || "").split(".").map(decodeBase64Utf8);
  const type = parts.shift();
  if (!type) return;

  switch (type) {
    case "start_game":
      sendGameMessage("start_game", {
        seed: parts[0],
        stake: Number(parts[1]) || 1,
        deck: parts[2],
      });
      break;
    case "score":
      sendGameMessage("score", {
        blind: parts[0],
        score: Number(parts[1]) || 0,
      });
      break;
    case "round_end": {
      const blind = String(parts[0]);
      const result = {
        score: Number(parts[1]) || 0,
        gameOver: parts[2] === "1",
        peerId,
      };
      localRounds.set(blind, result);
      sendGameMessage("round_end", {
        blind,
        score: result.score,
        gameOver: result.gameOver,
      });
      maybeAwardRound(blind);
      break;
    }
  }
}

function setSaveDirectoryEncoded(encodedPath) {
  const first = String(encodedPath || "").split(".")[0] || "";
  saveDirectory = decodeBase64Utf8(first);
  flushInbox();
}

function setTextInputActiveEncoded(encodedPacket) {
  const first = String(encodedPacket || "").split(".")[0] || "";
  window.__octopusTextInputActive = decodeBase64Utf8(first) === "1";
}

function handleBrowserTextKey(key, caps) {
  writeInboxMessage("text_key", String(key || ""), caps ? "1" : "0");
}

const bridge = {
  _pending: [],
  state,
  createLobby,
  joinLobby,
  joinLobbyEncoded,
  leaveLobby,
  fromLuaEncoded,
  setSaveDirectoryEncoded,
  setTextInputActiveEncoded,
  handleBrowserTextKey,
  sendGameMessage,
};
window.OctopusMultiplayer = bridge;

for (const [method, args] of pendingBridgeCalls) {
  if (typeof bridge[method] === "function") {
    try {
      bridge[method](...(args || []));
    } catch (error) {
      console.error("[Octopus MP] queued bridge call failed", method, error);
    }
  }
}

const queuedKeys = Array.isArray(window.__octopusTextKeyQueue)
  ? window.__octopusTextKeyQueue.splice(0)
  : [];
for (const [key, caps] of queuedKeys) handleBrowserTextKey(key, caps);

window.addEventListener("beforeunload", () => {
  try { leaveLobby({ quiet: true }); } catch (_) {}
});
