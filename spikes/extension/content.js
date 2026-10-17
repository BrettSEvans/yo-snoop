// Isolated world: relays between the service worker and page_media.js;
// reads captions (selectors filled in by Task 6).
const port = chrome.runtime.connect({name: "snoop-meet"});
const TAG = "snoop-spike";

port.onMessage.addListener((m) => {
  if (m.type === "dump") { port.postMessage({type: "dump", html: captionRegionHTML()}); return; }
  window.postMessage({tag: TAG, dir: "to-page", msg: m}, location.origin);
});

function captionRegionHTML() {
  const el = document.querySelector('[role="region"][aria-label*="aption" i]') || document.querySelector("[aria-live]");
  return el ? el.outerHTML : "NO-CAPTION-REGION";
}

// Task 6 replaces this with a parser built from a captured fixture.
function emitCaption(speaker, text) {
  port.postMessage({type: "caption", speaker, text, ts: Date.now() / 1000});
}
