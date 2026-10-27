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
    {speaker: "Test Speaker A", text: "yo snoop how many prs merged"},
    {speaker: "Test Speaker B", text: "we should snoop around the logs"},
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
