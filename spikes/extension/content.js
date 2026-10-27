// Isolated world: relays between the service worker and page_media.js;
// reads captions (selectors filled in by Task 6).
const TAG = "snoop-spike";
let port = null;

// Reconnect when Chrome restarts the service worker (the old port disconnects).
function connectPort() {
  port = chrome.runtime.connect({name: "snoop-meet"});
  port.onMessage.addListener((m) => {
    if (m.type === "dump") { port.postMessage({type: "dump", html: captionRegionHTML()}); return; }
    window.postMessage({tag: TAG, dir: "to-page", msg: m}, location.origin);
  });
  port.onDisconnect.addListener(() => setTimeout(connectPort, 1000));
}
connectPort();

function captionRegionHTML() {
  const el = document.querySelector('[role="region"][aria-label*="aption" i]') || document.querySelector("[aria-live]");
  return el ? el.outerHTML : "NO-CAPTION-REGION";
}

function emitCaption(speaker, text) {
  port.postMessage({type: "caption", speaker, text, ts: Date.now() / 1000});
}

// Captions grow in place while someone talks: send each line whenever its text changes.
const sent = new Map();  // block index -> last "speaker|text" sent
new MutationObserver(() => {
  parseCaptions(document).forEach((line, i) => {
    const key = `${line.speaker}|${line.text}`;
    if (sent.get(i) !== key) { sent.set(i, key); emitCaption(line.speaker, line.text); }
  });
}).observe(document.body, {childList: true, subtree: true, characterData: true});
