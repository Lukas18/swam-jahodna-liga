// Run the real browser render function against a minimal DOM to cover redraws.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.style = { setProperty: (key,value) => { this[key] = value; } }; this.classList = { toggle() {} }; }
  append(...nodes) { nodes.forEach(node => { if (node instanceof Element) node.parent = this; }); this.children.push(...nodes); }
  replaceChildren() { this.children = []; }
  setAttribute() {}
  addEventListener() {}
  getAnimations() { return []; }
  getBoundingClientRect() { return { top: this.parent ? this.parent.children.indexOf(this) * 36 : 0 }; }
  animate(frames, options) { this.movement = { frames, options }; }
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
    assert.equal(icon.width, 72); assert.equal(icon.height, 72);
  }
}
vm.runInContext(`state.iconDivisions.clear(); render(false)`, context);
assert.equal(images(elements.get('standings-body')).length, 0, 'Division opt-out ignored');
context.testPlayers[0].lastRoundIndex = -1;
context.testPlayers = [context.testPlayers[0]];
vm.runInContext(`state.iconDivisions.add('FPO'); render(false)`, context);
assert.equal(images(elements.get('standings-body')).length, 0, 'Previous-round icon leaked');
console.log('PASS: +4/+5/+6/+10 crying icons survive redraws; division opt-out and round boundaries hold.');

context.testPlayers = [2, 3, 4].map(delta => ({ id: String(delta), name: `Plus ${delta}`, division: 'FPO',
  score: delta, throws: delta+3, currentPlayed: 1, last: 1, start: 1, lastDelta: delta, lastRoundIndex: 0 }));
vm.runInContext(`render(false); window.matchMedia = () => ({ matches: false });`, context);
context.testPlayers.reverse();
vm.runInContext(`render(true)`, context);
const rows = elements.get('standings-body').rows;
for (const row of [rows[0],rows[2]]) {
  assert(row.movement, 'Moving row was not animated');
  assert.equal(row['--score-effect-delay'], `${row.movement.options.duration}ms`);
}
assert.equal(rows[1].movement, undefined, 'Stationary row should not move');
assert.equal(rows[1]['--score-effect-delay'], undefined, 'Stationary effects should not be delayed');
for (const icon of images(elements.get('standings-body'))) {
  assert.match(icon.className,/frog-icon/);
  assert.equal(icon.width,72); assert.equal(icon.height,72);
}
console.log('PASS: moving rows delay icon effects; stationary rows do not; all frogs reserve fixed dimensions.');

const byClass = (node, name) => (node.className || '').split(' ').includes(name) ? node : node.children.map(child => byClass(child, name)).find(Boolean);
for (const row of elements.get('standings-body').rows) {
  const score = byClass(row, 'score-content');
  assert.deepEqual(score.children.map(child => child.className), ['score-total','hole-delta-slot','score-icon-slot']);
  const delta = byClass(row, 'hole-delta');
  const icon = images(row)[0];
  assert.equal(delta.parent,score.children[1]);
  assert.equal(icon.parent,score.children[2]);
}
console.log('PASS: total score, adjacent hole delta and larger icon have separate slots in that order.');

context.testPlayers = [-1,-2].map(delta => ({ id: String(delta), name: `Under ${delta}`, division: 'FPO',
  score: delta, throws: delta+3, currentPlayed: 1, last: 1, start: 1, lastDelta: delta, lastRoundIndex: 0 }));
vm.runInContext(`window.matchMedia = () => ({ matches: true }); render(true);`, context);
const underIcons = images(elements.get('standings-body'));
assert.equal(underIcons.length,2);
assert.equal(underIcons[0].width,112); assert.equal(underIcons[0].height,112);
assert.equal(underIcons[1].width,86); assert.equal(underIcons[1].height,86);
assert.equal(underIcons[0].src,'/static/images/birdie-face.png');
assert.equal(underIcons[1].src,'/static/images/eagle-face.png');
console.log('PASS: Troll Face grows 30 percent to 112px; eagle stays 86px.');
