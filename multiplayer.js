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
  status: "offline",
  role: null,
  lobbyCode: null,
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
  const binary = atob(value);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  return textDecoder.decode(bytes);
}

function encodeBase64Utf8(value) {
  const bytes = textEncoder.encode(String(value));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function updateState(patch) {
  Object.assign(state, patch);
  renderState();
}

function renderState() {
  const status = document.getElementById("octo-mp-status");
  const lobby = document.getElementById("octo-mp-lobby");
  const score = document.getElementById("octo-mp-score");
  const leaveButton = document.getElementById("octo-mp-leave");

  if (status) status.textContent = state.status;
  if (lobby) {
    lobby.textContent = state.lobbyCode ? `Lobby ${state.lobbyCode}` : "No lobby";
  }
  if (score) score.textContent = Number(state.opponentScore || 0).toLocaleString();
  if (leaveButton) leaveButton.disabled = !signalChannel && !peerConnection;
}

function toast(message) {
  const host = document.getElementById("octo-mp-toasts");
  if (!host) return;
  const node = document.createElement("div");
  node.className = "octo-mp-toast";
  node.textContent = message;
  host.appendChild(node);
  requestAnimationFrame(() => node.classList.add("show"));
  setTimeout(() => {
    node.classList.remove("show");
    setTimeout(() => node.remove(), 250);
  }, 4200);
}

function createUi() {
  if (document.getElementById("octo-mp-root")) return;

  const style = document.createElement("style");
  style.textContent = `
    #octo-mp-root{position:fixed;top:12px;right:12px;z-index:2147483646;font-family:Arial,sans-serif;color:#fff;pointer-events:none}
    #octo-mp-toggle{pointer-events:auto;border:1px solid rgba(255,255,255,.2);background:rgba(12,24,34,.88);color:#fff;border-radius:10px;padding:8px 11px;font-weight:700;cursor:pointer;backdrop-filter:blur(10px)}
    #octo-mp-panel{pointer-events:auto;display:none;width:260px;margin-top:8px;padding:12px;border:1px solid rgba(255,255,255,.16);border-radius:12px;background:rgba(9,20,29,.94);box-shadow:0 14px 40px rgba(0,0,0,.35);backdrop-filter:blur(14px)}
    #octo-mp-panel.open{display:block}
    .octo-mp-row{display:flex;gap:7px;margin-top:8px}
    .octo-mp-row input{min-width:0;flex:1;border:1px solid rgba(255,255,255,.14);background:#0f2534;color:#fff;border-radius:8px;padding:8px;text-transform:uppercase}
    .octo-mp-row button,#octo-mp-create,#octo-mp-leave{border:0;border-radius:8px;background:#1e78ad;color:#fff;padding:8px 10px;font-weight:700;cursor:pointer}
    #octo-mp-leave{background:#8b3342}
    #octo-mp-leave:disabled{opacity:.45;cursor:default}
    .octo-mp-meta{font-size:12px;color:#a9c3d4;margin-top:7px}
    .octo-mp-scoreline{display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding-top:9px;border-top:1px solid rgba(255,255,255,.1);font-size:13px}
    #octo-mp-score{font-size:17px;font-weight:700}
    #octo-mp-toasts{position:fixed;right:12px;top:64px;width:280px;pointer-events:none}
    .octo-mp-toast{margin-top:8px;padding:10px 12px;border-radius:10px;background:rgba(9,20,29,.96);border:1px solid rgba(255,255,255,.16);box-shadow:0 12px 30px rgba(0,0,0,.35);opacity:0;transform:translateY(-6px);transition:.22s ease}
    .octo-mp-toast.show{opacity:1;transform:translateY(0)}
  `;
  document.head.appendChild(style);

  const root = document.createElement("div");
  root.id = "octo-mp-root";
  root.innerHTML = `
    <button id="octo-mp-toggle" type="button">MP</button>
    <div id="octo-mp-panel">
      <div style="font-weight:700">Balatro P2P</div>
      <div id="octo-mp-status" class="octo-mp-meta">offline</div>
      <div id="octo-mp-lobby" class="octo-mp-meta">No lobby</div>
      <div class="octo-mp-row"><button id="octo-mp-create" type="button" style="flex:1">Create lobby</button></div>
      <div class="octo-mp-row">
        <input id="octo-mp-code" maxlength="6" placeholder="Lobby code" autocomplete="off" spellcheck="false" />
        <button id="octo-mp-join" type="button">Join</button>
      </div>
      <div class="octo-mp-row"><button id="octo-mp-leave" type="button" style="flex:1" disabled>Leave</button></div>
      <div class="octo-mp-scoreline"><span>Opponent score</span><span id="octo-mp-score">0</span></div>
      <div class="octo-mp-meta">Direct WebRTC. Supabase is only used to introduce the two browsers.</div>
    </div>
    <div id="octo-mp-toasts"></div>
  `;
  document.body.appendChild(root);

  const toggle = document.getElementById("octo-mp-toggle");
  const panel = document.getElementById("octo-mp-panel");
  const codeInput = document.getElementById("octo-mp-code");

  toggle.addEventListener("click", () => panel.classList.toggle("open"));
  codeInput.addEventListener("input", () => {
    codeInput.value = normalizeLobbyCode(codeInput.value);
  });
  document.getElementById("octo-mp-create").addEventListener("click", async () => {
    try {
      await createLobby();
    } catch (error) {
      console.error("[Octopus MP] create lobby failed", error);
      updateState({ status: "lobby error" });
      toast("Could not create lobby.");
    }
  });
  document.getElementById("octo-mp-join").addEventListener("click", async () => {
    const code = normalizeLobbyCode(codeInput.value);
    if (code.length !== 6) {
      toast("Enter a 6-character lobby code.");
      return;
    }
    try {
      await joinLobby(code);
    } catch (error) {
      console.error("[Octopus MP] join lobby failed", error);
      updateState({ status: "join error" });
      toast("Could not join lobby.");
    }
  });
  document.getElementById("octo-mp-leave").addEventListener("click", () => leaveLobby());
  renderState();
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
  updateState({ status: "offline", role: null, lobbyCode: null, opponentScore: 0 });
  writeInboxMessage("mp_disconnected", "0");
  if (!quiet) toast("Left multiplayer lobby.");
}

async function openSignaling(code, desiredRole) {
  await leaveLobby({ quiet: true });
  role = desiredRole;
  lobbyCode = code;
  updateState({ status: desiredRole === "host" ? "waiting for player" : "joining…", role, lobbyCode: code, opponentScore: 0 });

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
      if (status !== "SUBSCRIBED") return;
      await signalChannel.track({ peerId, role, joinedAt: Date.now() });
      if (role === "guest") await sendSignal("join", null, {});
    });
}

async function createLobby() {
  const code = generateLobbyCode();
  await openSignaling(code, "host");
  const codeInput = document.getElementById("octo-mp-code");
  if (codeInput) codeInput.value = code;
  toast(`Lobby ${code} created.`);
  return code;
}

async function joinLobby(code) {
  code = normalizeLobbyCode(code);
  if (code.length !== 6) throw new Error("Invalid lobby code");
  await openSignaling(code, "guest");
  toast(`Joining ${code}…`);
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
    if (current === "failed" || current === "disconnected" || current === "closed") {
      updateState({ status: current === "failed" ? "P2P failed" : "peer disconnected" });
      if (current === "failed") toast("Direct P2P failed. This network may require TURN.");
    }
  };

  if (initiator) {
    bindDataChannel(peerConnection.createDataChannel("balatro-versus", { ordered: true }));
  } else {
    peerConnection.ondatachannel = (event) => bindDataChannel(event.channel);
  }

  connectionTimer = setTimeout(() => {
    if (!dataChannel || dataChannel.readyState !== "open") {
      updateState({ status: "P2P timeout" });
      toast("Could not make a direct P2P connection.");
    }
  }, 18000);

  return peerConnection;
}

function bindDataChannel(channel) {
  dataChannel = channel;
  dataChannel.onopen = () => {
    if (connectionTimer) clearTimeout(connectionTimer);
    connectionTimer = null;
    updateState({ status: "connected" });
    writeInboxMessage("mp_connected", role || "peer", lobbyCode || "------");
    toast("P2P connected.");
  };
  dataChannel.onclose = () => {
    updateState({ status: "peer disconnected" });
    writeInboxMessage("mp_disconnected", "0");
  };
  dataChannel.onerror = (error) => console.error("[Octopus MP] data channel error", error);
  dataChannel.onmessage = ({ data }) => {
    try {
      const message = JSON.parse(data);
      handleGameMessage(message);
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
      toast("Opponent started a synced run.");
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
  const won = winner === peerId;

  writeInboxMessage("award", blind, won ? "1" : "0", reward.type, reward.value ?? 0);

  if (!winner) {
    toast(`Blind ${blind}: tie.`);
    return;
  }
  if (won) {
    const label = reward.type === "money"
      ? `+$${reward.value}`
      : reward.type === "joker"
        ? "perishable Joker"
        : "random consumable";
    toast(`You won blind ${blind}: ${label}.`);
  } else {
    toast(`Opponent won blind ${blind}.`);
  }
}

function writeInboxMessage(type, ...fields) {
  const packet = [type, ...fields.map((value) => String(value))]
    .map(encodeBase64Utf8)
    .join(".");

  if (!saveDirectory || !window.Module || typeof window.Module.FS_createDataFile !== "function") {
    pendingInbox.push(packet);
    return;
  }

  const name = `octopus_mp_inbox_${Date.now()}_${String(inboxCounter++).padStart(4, "0")}.txt`;
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
  saveDirectory = decodeBase64Utf8(encodedPath);
  flushInbox();
}

const bridge = {
  _pending: [],
  state,
  createLobby,
  joinLobby,
  leaveLobby,
  fromLuaEncoded,
  setSaveDirectoryEncoded,
  sendGameMessage,
};
window.OctopusMultiplayer = bridge;

for (const [method, args] of pendingBridgeCalls) {
  if (typeof bridge[method] === "function") {
    try { bridge[method](...(args || [])); } catch (error) { console.error(error); }
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", createUi, { once: true });
} else {
  createUi();
}

window.addEventListener("beforeunload", () => {
  try { leaveLobby({ quiet: true }); } catch (_) {}
});
