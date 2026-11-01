"use strict";

const $ = (id) => document.getElementById(id);
const state = { data: null, pars: [], step: 0, timer: null, soundEnabled: true, highlighted: new Set(), iconDivisions: new Set(), players: new Map() };

function stop() {
  if (state.timer !== null) clearInterval(state.timer);
  state.timer = null;
  $("play").innerHTML = "▶ <span>Play</span>";
  $("play").setAttribute("aria-label", "Play");
}

function showError(message) {
  $("file-status").textContent = message;
  $("file-status").classList.toggle("bad", Boolean(message));
}

async function loadFile(file) {
  if (!file) return;
  stop();
  $("dashboard").classList.add("hidden");
  $("setup").classList.add("hidden");
  showError(`Reading ${file.name}…`);
  const body = new FormData();
  body.append("file", file);
  try {
    const response = await fetch("/api/workbook", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not read workbook");
    state.data = data;
    state.step = 0;
    state.highlighted.clear();
    state.players = new Map();
    for (const round of data.rounds) for (const player of round.players) state.players.set(player.id, player);
    showError(`${file.name} · ${data.rounds.length} rounds · ${data.player_count} players`);
    $("file-status").classList.remove("bad");
    buildSetup();
    $("setup").classList.remove("hidden");
  } catch (error) {
    showError(error.message);
  }
}

function parFor(layout, division) {
  return layout.profiles[division] || layout.profiles.default || null;
}

function parseCustom(value) {
  const parts = value.split(/[\s,;]+/).filter(Boolean);
  if (parts.length !== 18) return null;
  const pars = parts.map(Number);
  return pars.every((n) => Number.isInteger(n) && n >= 1 && n <= 10) ? pars : null;
}

function getRoundPars(roundIndex, check = false) {
  const select = $(`layout-${roundIndex}`);
  const round = state.data.rounds[roundIndex];
  const chosen = state.data.layouts.find((layout) => layout.id === select.value);
  const custom = parseCustom($(`custom-${roundIndex}`).value);
  const profiles = chosen ? chosen.profiles : custom ? { default: custom } : null;
  if (!profiles) return { error: "Choose a layout or enter 18 hole pars." };
  for (const player of round.players) {
    const pars = profiles[player.division] || profiles.default;
    if (!pars || pars.length !== 18) return { error: `No 18-hole pars for ${player.division || "this division"}.` };
    if (check && player.total !== null && player.relative !== null &&
        pars.reduce((sum, par) => sum + par, 0) !== player.total - player.relative) {
      return { error: `${player.name}: layout par ${pars.reduce((a, b) => a + b, 0)} does not match export par ${player.total - player.relative}.` };
    }
  }
  return { profiles };
}

function validateChoice(roundIndex) {
  const selected = $(`layout-${roundIndex}`).value;
  $(`custom-wrap-${roundIndex}`).classList.toggle("hidden", selected !== "custom");
  const result = getRoundPars(roundIndex, true);
  const message = $(`validation-${roundIndex}`);
  message.textContent = result.error || "Par totals match the export.";
  message.classList.toggle("bad", Boolean(result.error));
  return result;
}

function buildSetup() {
  const target = $("layout-controls");
  target.replaceChildren();
  $("setup-error").textContent = "";
  state.data.rounds.forEach((round, i) => {
    const card = document.createElement("div"); card.className = "layout-choice";
    const title = document.createElement("strong"); title.textContent = round.sheet;
    const detail = document.createElement("small");
    detail.textContent = `${round.players.length} players · export par ${Object.keys(round.reported_par_totals).join(", ") || "unknown"}`;
    const label = document.createElement("label"); label.textContent = "Course layout";
    const select = document.createElement("select"); select.id = `layout-${i}`;
    for (const [value, text] of [["", "Choose a layout"], ...state.data.layouts.map((x) => [x.id, x.name]), ["custom", "Enter hole pars manually"]]) {
      const option = document.createElement("option"); option.value = value; option.textContent = text; select.append(option);
    }
    const manualWrap = document.createElement("label"); manualWrap.id = `custom-wrap-${i}`; manualWrap.className = "manual hidden";
    manualWrap.textContent = "18 pars in hole-number order";
    const manual = document.createElement("input"); manual.id = `custom-${i}`; manual.type = "text";
    manual.placeholder = "3, 3, 4, 3, …";
    manualWrap.append(manual);
    const validation = document.createElement("p"); validation.id = `validation-${i}`; validation.className = "validation";
    label.append(select); card.append(title, detail, label, manualWrap, validation); target.append(card);
    const matching = state.data.layouts.filter((layout) => round.players.every((player) => {
      const pars = parFor(layout, player.division);
      return pars && (player.total === null || player.relative === null ||
        pars.reduce((sum, par) => sum + par, 0) === player.total - player.relative);
    }));
    if (matching.length === 1) select.value = matching[0].id;
    select.addEventListener("change", () => validateChoice(i));
    manual.addEventListener("input", () => validateChoice(i));
    validateChoice(i);
  });
}

function startReplay() {
  const pars = state.data.rounds.map((_, i) => validateChoice(i));
  const problem = pars.find((item) => item.error);
  if (problem) {
    $("setup-error").textContent = problem.error;
    return;
  }
  state.pars = pars.map((item) => item.profiles);
  state.step = 0;
  const max = state.data.rounds.length * 18;
  $("timeline").max = String(max);
  $("round-markers").replaceChildren();
  for (let i = 0; i <= state.data.rounds.length; i++) {
    const marker = document.createElement("span");
    marker.textContent = i === 0 ? "Start" : `Round ${i} finish`;
    $("round-markers").append(marker);
  }
  const division = $("division"); division.replaceChildren();
  for (const name of ["All divisions", ...state.data.divisions]) {
    const option = document.createElement("option"); option.value = name; option.textContent = name; division.append(option);
  }
  state.iconDivisions = new Set(state.data.divisions.filter((name) => name.toUpperCase() !== "FPO"));
  const iconOptions = $("icon-division-options"); iconOptions.replaceChildren();
  for (const name of state.data.divisions) {
    const label = document.createElement("label");
    const checkbox = document.createElement("input"); checkbox.type = "checkbox";
    checkbox.checked = state.iconDivisions.has(name);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.iconDivisions.add(name); else state.iconDivisions.delete(name);
      updateIconDivisionSummary();
      render();
    });
    label.append(checkbox, document.createTextNode(name)); iconOptions.append(label);
  }
  updateIconDivisionSummary();
  const options = $("player-options"); options.replaceChildren();
  for (const player of [...state.players.values()].sort((a, b) => a.name.localeCompare(b.name))) {
    const option = document.createElement("option"); option.value = playerLabel(player); options.append(option);
  }
  $("highlight-search").value = "";
  renderHighlights();
  $("dashboard-summary").textContent = `${state.data.player_count} players · ${state.data.rounds.length} rounds · shotgun start`;
  $("dashboard").classList.remove("hidden");
  render(false);
  $("dashboard").scrollIntoView({ behavior: "smooth", block: "start" });
}

function snapshot(step = state.step) {
  const players = new Map();
  state.data.rounds.forEach((round, roundIndex) => {
    const allowed = Math.max(0, Math.min(18, step - roundIndex * 18));
    for (const player of round.players) {
      if (!players.has(player.id)) players.set(player.id, { id: player.id, name: player.name, division: player.division,
        score: 0, throws: 0, played: 0, currentPlayed: 0, start: null, last: null,
        lastDelta: null, lastRoundIndex: null, missing: 0 });
      const item = players.get(player.id);
      if (allowed === 0) continue;
      const pars = state.pars[roundIndex][player.division] || state.pars[roundIndex].default;
      item.start = player.start;
      item.currentPlayed = 0;
      item.lastDelta = null;
      item.lastRoundIndex = roundIndex;
      for (let played = 0; played < allowed; played++) {
        const hole = (player.start - 1 + played) % 18;
        const throws = player.scores[hole];
        if (throws === null) { item.missing++; continue; }
        item.score += throws - pars[hole];
        item.throws += throws;
        item.played++;
        item.currentPlayed++;
        item.last = hole + 1;
        if (played === allowed - 1) item.lastDelta = throws - pars[hole];
      }
    }
  });
  const selected = $("division").value;
  return [...players.values()].filter((p) => selected === "All divisions" || p.division === selected)
    .sort((a, b) => a.missing - b.missing || a.score - b.score || b.played - a.played || a.name.localeCompare(b.name));
}

function ranksFor(standing) {
  const ranks = new Map();
  let position = 0, previous = null;
  standing.forEach((player, index) => {
    const key = `${player.missing}:${player.score}:${player.played}`;
    if (key !== previous) position = index + 1;
    previous = key;
    if (!player.missing) ranks.set(player.id, position);
  });
  return ranks;
}

function comparisonStep(step) {
  if (step === 0) return null;
  const roundNumber = Math.ceil(step / 18);
  if (roundNumber === 1) return step === 1 ? null : step - 1;
  return (roundNumber - 1) * 18;
}

function cell(row, value, className = "") {
  const td = document.createElement("td"); td.textContent = String(value); td.className = className; row.append(td); return td;
}

function scoreText(value) {
  return value > 0 ? `+${value}` : value < 0 ? String(value) : "±0";
}

function playOof() {
  const audio = $("oof-audio");
  audio.pause();
  audio.currentTime = 0;
  audio.play().catch(() => {
    $("sound-toggle").title = "Sound could not play; check the internet connection or browser audio settings";
  });
}

function playerLabel(player) {
  return `${player.name} · ${player.division}`;
}

function updateIconDivisionSummary() {
  $("icon-division-summary").textContent = `Score icons (${state.iconDivisions.size}/${state.data.divisions.length})`;
}

function searchable(value) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase();
}

function renderHighlights() {
  const target = $("highlight-chips"); target.replaceChildren();
  for (const id of state.highlighted) {
    const player = state.players.get(id);
    if (!player) continue;
    const chip = document.createElement("button"); chip.type = "button"; chip.className = "highlight-chip";
    chip.textContent = `${playerLabel(player)}  ×`;
    chip.setAttribute("aria-label", `Remove highlight from ${player.name}`);
    chip.addEventListener("click", () => { state.highlighted.delete(id); renderHighlights(); render(false); });
    target.append(chip);
  }
  $("clear-highlights").disabled = state.highlighted.size === 0;
}

function addHighlight() {
  const query = searchable($("highlight-search").value.trim());
  if (!query) return;
  const all = [...state.players.values()];
  let matches = all.filter((player) => searchable(playerLabel(player)) === query || searchable(player.name) === query);
  if (!matches.length) matches = all.filter((player) => searchable(player.name).includes(query));
  if (matches.length !== 1) {
    $("highlight-search").setCustomValidity("Choose a player from the suggestions.");
    $("highlight-search").reportValidity();
    return;
  }
  $("highlight-search").setCustomValidity("");
  state.highlighted.add(matches[0].id);
  $("highlight-search").value = "";
  renderHighlights();
  render(false);
}

function render(animate = true) {
  $("timeline").value = String(state.step);
  const roundNumber = state.step === 0 ? 1 : Math.ceil(state.step / 18);
  const thru = state.step === 0 ? 0 : (state.step - 1) % 18 + 1;
  $("moment-label").textContent = state.step === 0 ? "Before play" : `Round ${roundNumber} (Thru ${thru})`;
  const standing = snapshot();
  const currentRanks = ranksFor(standing);
  const previousStep = comparisonStep(state.step);
  const comparisonRanks = previousStep === null ? new Map() : ranksFor(snapshot(previousStep));
  const target = $("standings-body");
  const oldRows = new Map();
  if (animate && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    for (const row of target.rows) {
      // Settle the previous movement so a fast replay never starts two holes behind.
      for (const animation of row.getAnimations()) animation.finish();
      oldRows.set(row.dataset.playerId, { top: row.getBoundingClientRect().top });
    }
  }
  target.replaceChildren();
  standing.forEach((player) => {
    const position = currentRanks.get(player.id);
    const row = document.createElement("tr");
    row.dataset.playerId = player.id;
    row.classList.toggle("highlighted", state.highlighted.has(player.id));
    const rankCell = cell(row, position ?? "—", "rank");
    const baseline = comparisonRanks.get(player.id);
    if (baseline && position && baseline !== position) {
      const movement = document.createElement("span");
      movement.className = `rank-movement ${position < baseline ? "up" : "down"}`;
      movement.textContent = `${position < baseline ? "▲" : "▼"}${Math.abs(baseline - position)}`;
      const reference = roundNumber === 1 ? "the previous hole" : `the end of Round ${roundNumber - 1}`;
      movement.title = `${Math.abs(baseline - position)} place${Math.abs(baseline - position) === 1 ? "" : "s"} ${position < baseline ? "up" : "down"} since ${reference}`;
      rankCell.append(movement);
    }
    const nameCell = document.createElement("td"); nameCell.className = "player-name";
    const playerButton = document.createElement("button"); playerButton.type = "button"; playerButton.className = "player-highlight-button";
    playerButton.textContent = player.name;
    playerButton.setAttribute("aria-label", `${state.highlighted.has(player.id) ? "Remove highlight from" : "Highlight"} ${player.name}`);
    playerButton.setAttribute("aria-pressed", String(state.highlighted.has(player.id)));
    playerButton.addEventListener("click", () => {
      if (state.highlighted.has(player.id)) state.highlighted.delete(player.id); else state.highlighted.add(player.id);
      renderHighlights(); render(false);
    });
    nameCell.append(playerButton);
    if ($("division").value === "All divisions") {
      const tag = document.createElement("span"); tag.className = "division-tag"; tag.textContent = player.division; nameCell.append(tag);
    }
    row.append(nameCell);
    const score = player.score > 0 ? `+${player.score}` : String(player.score);
    const scoreCell = cell(row, "", `score ${player.score > 0 ? "over" : player.score === 0 ? "even" : ""}`);
    const scoreContent = document.createElement("span"); scoreContent.className = "score-content";
    const total = document.createElement("span"); total.textContent = score; scoreContent.append(total);
    if (animate && player.lastDelta !== null && player.lastDelta !== 0 && player.lastRoundIndex === roundNumber - 1) {
      const holeDelta = document.createElement("sup");
      const tone = player.lastDelta >= 3 ? "big-over" : player.lastDelta > 0 ? "over" : "under";
      const size = player.lastDelta > 5 ? "huge" : player.lastDelta >= 3 ? "large" : player.lastDelta > 0 ? "small-over" : "";
      holeDelta.className = `hole-delta ${tone} ${size}`;
      holeDelta.textContent = scoreText(player.lastDelta);
      holeDelta.title = `Hole ${player.last}: ${scoreText(player.lastDelta)} relative to par`;
      scoreContent.append(holeDelta);
      const underParIcon = { "-1": "birdie", "-2": "eagle" }[player.lastDelta];
      if (state.iconDivisions.has(player.division) && (player.lastDelta >= 3 || underParIcon)) {
        const icon = document.createElement("img");
        icon.className = `hole-icon${underParIcon ? ` ${underParIcon}-icon` : ""}`;
        icon.src = underParIcon ? `/static/images/${underParIcon}-face.png`
          : player.lastDelta >= 5 ? "/static/images/crying-frog.png" : "/static/images/sad-frog.png";
        icon.alt = "";
        icon.setAttribute("aria-hidden", "true");
        scoreContent.append(icon);
      }
    }
    scoreCell.append(scoreContent);
    cell(row, player.throws || "—");
    cell(row, `${player.currentPlayed} / 18`);
    cell(row, player.last === null ? "—" : player.last);
    cell(row, player.start === null ? "—" : player.start);
    target.append(row);
  });
  if (oldRows.size) {
    const duration = Math.min(240, Math.max(120, Number($("speed").value) * 0.6));
    for (const row of target.rows) {
      const old = oldRows.get(row.dataset.playerId);
      if (!old) continue;
      const offset = old.top - row.getBoundingClientRect().top;
      if (Math.abs(offset) > 1) row.animate(
        [{ transform: `translateY(${offset}px)`, zIndex: 1 }, { transform: "translateY(0)", zIndex: 1 }],
        { duration, easing: "cubic-bezier(.2,.8,.2,1)" });
    }
  }
  return standing;
}

function setStep(next) {
  const previous = state.step;
  state.step = Math.max(0, Math.min(state.data.rounds.length * 18, next));
  const standing = render();
  if (state.soundEnabled && state.step === previous + 1 &&
      standing.some((player) => player.lastRoundIndex === Math.ceil(state.step / 18) - 1 && player.lastDelta >= 3)) {
    playOof();
  }
  if (state.step === state.data.rounds.length * 18) stop();
}

function play() {
  if (state.timer !== null) { stop(); return; }
  if (state.step === state.data.rounds.length * 18) setStep(0);
  $("play").innerHTML = "Ⅱ <span>Pause</span>";
  $("play").setAttribute("aria-label", "Pause");
  state.timer = setInterval(() => setStep(state.step + 1), Number($("speed").value));
}

$("workbook").addEventListener("change", (event) => loadFile(event.target.files[0]));
$("drop-zone").addEventListener("dragover", (event) => { event.preventDefault(); event.currentTarget.classList.add("dragging"); });
$("drop-zone").addEventListener("dragleave", (event) => event.currentTarget.classList.remove("dragging"));
$("drop-zone").addEventListener("drop", (event) => {
  event.preventDefault(); event.currentTarget.classList.remove("dragging"); loadFile(event.dataTransfer.files[0]);
});
$("start").addEventListener("click", startReplay);
$("change-file").addEventListener("click", () => { stop(); $("dashboard").classList.add("hidden"); $("workbook").click(); });
$("first").addEventListener("click", () => { stop(); setStep(0); });
$("previous").addEventListener("click", () => { stop(); setStep(state.step - 1); });
$("play").addEventListener("click", play);
$("next").addEventListener("click", () => { stop(); setStep(state.step + 1); });
$("last").addEventListener("click", () => { stop(); setStep(state.data.rounds.length * 18); });
$("timeline").addEventListener("input", (event) => { stop(); setStep(Number(event.target.value)); });
$("division").addEventListener("change", () => render(false));
$("add-highlight").addEventListener("click", addHighlight);
$("highlight-search").addEventListener("input", () => $("highlight-search").setCustomValidity(""));
$("highlight-search").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); addHighlight(); } });
$("clear-highlights").addEventListener("click", () => { state.highlighted.clear(); renderHighlights(); render(false); });
$("speed").addEventListener("change", () => { if (state.timer !== null) { stop(); play(); } });
$("sound-toggle").addEventListener("click", () => {
  state.soundEnabled = !state.soundEnabled;
  if (!state.soundEnabled) $("oof-audio").pause();
  $("sound-toggle").textContent = state.soundEnabled ? "🔊 Sound" : "🔇 Muted";
  $("sound-toggle").setAttribute("aria-pressed", String(state.soundEnabled));
  $("sound-toggle").title = state.soundEnabled ? "Mute triple bogey sound" : "Enable triple bogey sound";
});
document.addEventListener("keydown", (event) => {
  if ($("dashboard").classList.contains("hidden") || ["INPUT", "SELECT"].includes(document.activeElement.tagName)) return;
  if (event.key === "ArrowRight") { stop(); setStep(state.step + 1); }
  if (event.key === "ArrowLeft") { stop(); setStep(state.step - 1); }
  if (event.code === "Space") { event.preventDefault(); play(); }
});
