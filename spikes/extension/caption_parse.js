// Reads Meet's live-caption region into [{speaker, text}], oldest first.
// Structure seen 2026-10-27 (sanitized copy: test/fixture_captions.html):
//   [role=region][aria-label=Captions] > div.nMcdL (one per speaker turn)
//     > div.adE6rb (avatar img + span.NWpY1d speaker name)  +  div.ygicle (caption text)
// Meet's class names are generated and may change; the region is found by role/label, which is stable.
const CAPTION_REGION = '[role="region"][aria-label*="aption" i]';
const CAPTION_BLOCK = "div.nMcdL";
const SPEAKER = "span.NWpY1d";
const TEXT = "div.ygicle";

function parseCaptions(root) {
  const region = root.matches && root.matches(CAPTION_REGION) ? root : root.querySelector(CAPTION_REGION);
  if (!region) return [];
  const out = [];
  for (const block of region.querySelectorAll(CAPTION_BLOCK)) {
    const speaker = block.querySelector(SPEAKER)?.textContent.trim() ?? "";
    // a turn can hold several text pieces (e.g. after a pause): read them all, in order
    const text = [...block.querySelectorAll(TEXT)].map((t) => t.textContent.trim()).filter(Boolean).join(" ");
    if (text) out.push({speaker, text});
  }
  return out;
}
