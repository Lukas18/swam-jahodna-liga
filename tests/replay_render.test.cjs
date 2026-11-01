// Run the real browser render function against a minimal DOM to cover redraws.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.classList = { toggle() {} }; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; }
  setAttribute() {}
  addEventListener() {}
  get rows() { return this.children; }
}
const elements = new Map();
const context = vm.createContext({
  document: { getElementById(id) { if (!elements.has(id)) elements.set(id, new Element(id)); return elements.get(id); },
    createElement: tag => new Element(tag), addEventListener() {} },
  window: { matchMedia: () => ({ matches: true }) },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../replay_app/static/app.js'), 'utf8'), context);
vm.runInContext(`
  state.step = 1;
  state.iconDivisions = new Set(['MPO', 'FPO']);
  $('division').value = 'All divisions';
  snapshot = () => testPlayers;
  ranksFor = players => new Map(players.map((p,i) => [p.id,i+1]));
`, context);
const images = node => [...(node.tag === 'img' ? [node] : []), ...node.children.flatMap(images)];
for (const animate of [true, false]) {
  context.testPlayers = [4, 5, 6, 10].map(delta => ({ id: String(delta), name: `Plus ${delta}`, division: 'FPO',
    score: delta, throws: delta+3, currentPlayed: 1, last: 1, start: 1, lastDelta: delta, lastRoundIndex: 0 }));
  vm.runInContext(`render(${animate})`, context);
  const icons = images(elements.get('standings-body'));
  assert.equal(icons.length, 4, `Missing crying icon with animate=${animate}`);
  for (const icon of icons) {
    assert.equal(icon.src, '/static/images/crying-frog.png');
    assert.match(icon.className, /crying-icon/);
  }
}
vm.runInContext(`state.iconDivisions.clear(); render(false)`, context);
assert.equal(images(elements.get('standings-body')).length, 0, 'Division opt-out ignored');
context.testPlayers[0].lastRoundIndex = -1;
context.testPlayers = [context.testPlayers[0]];
vm.runInContext(`state.iconDivisions.add('FPO'); render(false)`, context);
assert.equal(images(elements.get('standings-body')).length, 0, 'Previous-round icon leaked');
console.log('PASS: +4/+5/+6/+10 crying icons survive redraws; division opt-out and round boundaries hold.');
