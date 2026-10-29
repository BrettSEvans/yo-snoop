import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {JSDOM} from "jsdom";
import vm from "node:vm";
// caption_parse.js is a plain content script (no modules); load it the way Chrome does, into one global scope.
const ctx = vm.createContext({});
vm.runInContext(readFileSync(new URL("../caption_parse.js", import.meta.url), "utf8"), ctx);
const parseCaptions = (root) => JSON.parse(JSON.stringify(ctx.parseCaptions(root)));  // plain objects across the vm boundary

test("parses speaker and text from the sanitized Meet fixture", () => {
  const dom = new JSDOM(readFileSync(new URL("./fixture_captions.html", import.meta.url), "utf8"));
  const lines = parseCaptions(dom.window.document.body);
  assert.deepEqual(lines, [
    {speaker: "Test Speaker A", text: "yo snoop how many prs merged", block: 1},
    {speaker: "Test Speaker B", text: "we should snoop around the logs", block: 2},
  ]);
});

test("no caption region gives no lines", () => {
  const dom = new JSDOM("<div>nothing here</div>");
  assert.deepEqual(parseCaptions(dom.window.document.body), []);
});

test("a turn split into several text pieces is read whole", () => {
  const html = readFileSync(new URL("./fixture_captions.html", import.meta.url), "utf8")
    .replace("yo snoop how many prs merged</div>", 'yo</div><div class="ygicle VbkSUe">snoop how many prs merged</div>');
  const lines = parseCaptions(new JSDOM(html).window.document.body);
  assert.equal(lines[0].text, "yo snoop how many prs merged");
});

// Group meetings scroll turns off the top, so a line's position is not its identity: each block carries an id
// that stays with it across re-reads and is never given to a later block.
test("a block keeps its id across re-reads", () => {
  const dom = new JSDOM(readFileSync(new URL("./fixture_captions.html", import.meta.url), "utf8"));
  const first = parseCaptions(dom.window.document.body), again = parseCaptions(dom.window.document.body);
  assert.equal(typeof first[0].block, "number");
  assert.notEqual(first[0].block, first[1].block);
  assert.deepEqual(again.map((l) => l.block), first.map((l) => l.block));
});

test("a new block after the oldest scrolls off gets a fresh id", () => {
  const dom = new JSDOM(readFileSync(new URL("./fixture_captions.html", import.meta.url), "utf8"));
  const doc = dom.window.document;
  const before = parseCaptions(doc.body);
  const [a, b] = doc.querySelectorAll("div.nMcdL");
  const c = a.cloneNode(true); c.querySelector("div.ygicle").textContent = "is ci green";
  a.remove(); b.parentNode.appendChild(c);
  const after = parseCaptions(doc.body);
  assert.equal(after[0].block, before[1].block);          // B moved to the top but kept its id
  assert.ok(!before.some((l) => l.block === after[1].block));  // the new block is new
});
