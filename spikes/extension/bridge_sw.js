// Holds the localhost websocket; relays to/from the Meet tab.
let ws = null, port = null, cfg = null;

async function config() {
  if (!cfg) cfg = await (await fetch(chrome.runtime.getURL("config.local.json"))).json();
  return cfg;
}

async function connect() {
  const c = await config();
  ws = new WebSocket(`ws://127.0.0.1:${c.port}/snoop`);
  ws.onopen = () => ws.send(JSON.stringify({type: "hello", token: c.token}));
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.type !== "ack" && port) port.postMessage(m); };
  ws.onclose = () => { ws = null; setTimeout(connect, 2000); };
}

chrome.runtime.onConnect.addListener((p) => {
  if (p.name !== "snoop-meet") return;
  port = p;
  config().then((c) => p.postMessage({type: "card", text: `Snoop (${c.host_display_name})`}));
  p.onMessage.addListener((m) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); });
  p.onDisconnect.addListener(() => { port = null; });
  if (!ws) connect();
});
