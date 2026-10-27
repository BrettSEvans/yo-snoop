// Isolated world: relays between the service worker and page_media.js;
// reads captions (selectors filled in by Task 6).
const TAG = "snoop-spike";
let port = null;

// Send to the service worker; after the extension is reloaded this page's link is dead for good
// (chrome.runtime.id is gone), so stop quietly until the tab is reloaded.
function send(msg) {
  if (!chrome.runtime?.id) { port = null; return; }
  try { if (port) port.postMessage(msg); } catch (e) { port = null; }
}

// Reconnect when Chrome restarts the service worker (the old port disconnects).
function connectPort() {
  if (!chrome.runtime?.id) return;  // extension reloaded: this page is orphaned
  port = chrome.runtime.connect({name: "snoop-meet"});
  port.onMessage.addListener((m) => {
    if (m.type === "dump") { send({type: "dump", html: captionRegionHTML()}); return; }
    window.postMessage({tag: TAG, dir: "to-page", msg: m}, location.origin);
  });
  port.onDisconnect.addListener(() => setTimeout(connectPort, 1000));
}
connectPort();

function captionRegionHTML() {
  const el = document.querySelector('[role="region"][aria-label*="aption" i]') || document.querySelector("[aria-live]");
  return el ? el.outerHTML : "NO-CAPTION-REGION";
}

// Page -> extension (meeting audio from page_media.js), same origin and tag only.
window.addEventListener("message", (e) => {
  if (e.source !== window || e.data?.tag !== TAG || e.data.dir !== "to-ext") return;
  send(e.data.msg);
});

function emitCaption(speaker, text) {
  send({type: "caption", speaker, text, ts: Date.now() / 1000});
}

// Captions grow in place while someone talks: send each line whenever its text changes.
const sent = new Map();  // block index -> last "speaker|text" sent
new MutationObserver(() => {
  parseCaptions(document).forEach((line, i) => {
    const key = `${line.speaker}|${line.text}`;
    if (sent.get(i) !== key) { sent.set(i, key); emitCaption(line.speaker, line.text); }
  });
}).observe(document.body, {childList: true, subtree: true, characterData: true});
