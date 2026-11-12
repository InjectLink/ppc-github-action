"""Visualiseur HTML autonome (un seul fichier, sans connexion Internet), même gabarit que le
visualiseur de la cartographie de démontage PPC (GT1).

Vues : Synthèse, Radar (familles de causes par domaine), Frise (échéances datées),
Constats (filtrables), Composants (cycle de vie, avertissements), Fichiers.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import __version__
from .analyse import Resultat, etat_sources_composants, synthese
from .referentiel import DOMAINES, FAMILLES


def _donnees(res: Resultat, source: str) -> dict:
    s = synthese(res)
    p = res.produit
    max_ligne: dict = {}
    for c in res.constats:
        max_ligne[c.ligne.numero] = max(max_ligne.get(c.ligne.numero, 0), c.criticite)
    familles_utiles = sorted({c.famille for c in res.constats} | {"A", "B", "C", "D"})
    return {
        "version": __version__,
        "genere": date.today().isoformat(),
        "source": source,
        "produit": {
            "nom": p.nom, "mise_marche": p.date_mise_marche.isoformat(),
            "duree_vie": p.duree_vie_cible_ans, "horizon": p.horizon.isoformat(),
            "fin_support": p.fin_support.isoformat() if p.fin_support else None,
        },
        "synthese": {k: s[k] for k in ("indice", "lignes_critiques", "lignes_a_surveiller")},
        "familles": {k: FAMILLES[k] for k in familles_utiles},
        "domaines": DOMAINES,
        "lignes": [{"n": l.numero, "id": str(l.get("id", l.numero)), "designation": str(l.get("designation")),
                    "domaine": l.domaine, "gravite": l.gravite, "max": max_ligne.get(l.numero, 0)}
                   for l in res.lignes],
        "constats": [{"n": c.ligne.numero, "id": str(c.ligne.get("id", c.ligne.numero)),
                      "ligne": c.ligne.libelle, "domaine": c.ligne.domaine, "famille": c.famille,
                      "code": c.code, "intitule": c.intitule, "expo": c.exposition, "grav": c.gravite,
                      "crit": c.criticite, "niveau": c.niveau, "detail": c.detail,
                      "reco": c.recommandation, "preuve": c.preuve, "auto": c.automatique}
                     for c in sorted(res.constats, key=lambda c: (-c.criticite, c.ligne.numero, c.code))],
        "cycles": res.cycles_vie,
        "echeances": sorted(res.echeances, key=lambda e: e["date"]),
        "avertissements": res.avertissements,
        "sources": [{"nom": n, "actif": a} for n, a, _ in etat_sources_composants()],
    }


def ecrire_visualiseur(res: Resultat, chemin: Path, source: str = "") -> Path:
    donnees = json.dumps(_donnees(res, source), ensure_ascii=False).replace("</", "<\\/")
    html = GABARIT.replace("__DONNEES__", donnees).replace("__TITRE__", "Radar d'obsolescence")
    Path(chemin).write_text(html, encoding="utf-8")
    return Path(chemin)


GABARIT = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITRE__</title>
<style>
:root { --marine:#1F3A5F; --sarcelle:#1A8C8C; --corail:#E8735A; --ambre:#E9A93B; --vert:#4FAE7B; --fond:#F4F7F9; --carte:#FFFFFF; --ligne:#D5DDE5; --texte:#1B2633; --doux:#5B6B7C; }
* { box-sizing:border-box; }
html, body { margin:0; height:100%; }
body { font-family: Calibri, "Segoe UI", Arial, sans-serif; color:var(--texte); background:var(--fond); display:flex; flex-direction:column; font-size:15px; }
header { background:var(--marine); color:#fff; padding:12px 20px; display:flex; flex-wrap:wrap; align-items:center; gap:10px 24px; }
header h1 { font-family: Cambria, Georgia, serif; font-size:20px; margin:0; font-weight:700; }
header .src { font-size:12px; opacity:.8; }
nav { display:flex; flex-wrap:wrap; gap:6px; margin-left:auto; }
nav button { font:inherit; font-size:14px; border:1px solid rgba(255,255,255,.35); background:transparent; color:#fff; padding:6px 14px; border-radius:18px; cursor:pointer; }
nav button.actif { background:#fff; color:var(--marine); font-weight:700; }
main { flex:1; display:flex; min-height:0; }
.vue { display:none; flex:1; min-height:0; }
.vue.actif { display:flex; }
.panneau { width:330px; flex-shrink:0; overflow:auto; padding:16px; background:var(--carte); border-right:1px solid var(--ligne); }
.panneau h2 { font-size:15px; color:var(--marine); margin:18px 0 8px; }
.panneau h2:first-child { margin-top:0; }
.kpi { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:8px; }
.kpi div { background:var(--fond); border-radius:8px; padding:8px 10px; }
.kpi b { display:block; font-size:24px; color:var(--sarcelle); font-family:Cambria, Georgia, serif; }
.kpi b.c { color:var(--corail); } .kpi b.a { color:var(--ambre); }
.kpi span { font-size:12px; color:var(--doux); }
.jauge { margin:4px 0 6px; }
.leg { display:grid; grid-template-columns:auto 1fr; gap:6px 10px; align-items:center; font-size:13px; }
.sw { width:28px; height:16px; border-radius:4px; }
.note { font-size:12px; color:var(--doux); line-height:1.4; }
.cibles { list-style:none; padding:0; margin:0; }
.cibles li { display:flex; justify-content:space-between; gap:8px; padding:6px 8px; border-radius:6px; cursor:pointer; font-size:14px; }
.cibles li:hover { background:#FDECE8; }
.cibles li b { color:var(--corail); }
.page { flex:1; overflow:auto; padding:24px; }
.page .bloc { background:var(--carte); border-radius:10px; padding:18px 20px; margin-bottom:18px; max-width:1180px; }
.bloc h2 { margin:0 0 10px; font-size:17px; color:var(--marine); font-family:Cambria, Georgia, serif; }
.grille2 { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:18px; max-width:1180px; }
.grille2 .bloc { margin-bottom:0; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th { background:var(--marine); color:#fff; text-align:left; padding:8px 10px; font-weight:600; }
td { padding:7px 10px; border-bottom:1px solid var(--ligne); vertical-align:top; }
td.num { text-align:center; }
.mat td, .mat th { text-align:center; }
.mat td.cell { cursor:pointer; font-weight:700; border:2px solid #fff; border-radius:6px; }
.mat td.lib { text-align:left; font-size:13px; }
.pill { display:inline-block; font-size:11px; padding:1px 8px; border-radius:9px; color:#fff; font-weight:700; white-space:nowrap; }
.code { display:inline-block; font-size:12px; padding:1px 6px; border-radius:5px; background:var(--fond); color:var(--marine); font-weight:700; }
.outils { display:flex; gap:8px; padding:10px 0 14px; align-items:center; flex-wrap:wrap; }
.outils select { max-width:260px; }
.outils select, .outils input { font:inherit; font-size:13px; border:1px solid var(--ligne); background:#fff; padding:5px 9px; border-radius:6px; color:var(--marine); }
.outils .aide { font-size:12px; color:var(--doux); margin-left:auto; }
.alerte { background:#FFF4D6; border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:8px; }
.dl a { display:inline-block; margin:3px 6px 3px 0; padding:5px 10px; border:1px solid var(--ligne); border-radius:6px; text-decoration:none; color:var(--marine); font-size:13px; background:#fff; }
.dl a:hover { border-color:var(--sarcelle); }
a { color:var(--sarcelle); }
.reco { font-size:13px; color:var(--doux); margin-top:3px; }
tr.flash td { animation: flash 1.6s ease 2; }
@keyframes flash { 50% { background:#FDECE8; } }
svg text { font-family: Calibri, "Segoe UI", Arial, sans-serif; }
@media (max-width: 900px) { .vue.actif { flex-direction:column; } .panneau { width:auto; border-right:none; border-bottom:1px solid var(--ligne); max-height:45vh; } .grille2 { grid-template-columns:1fr; } }
</style>
</head>
<body>
<header>
  <div><h1 id="titre">Radar d'obsolescence</h1><div class="src" id="src"></div></div>
  <nav id="nav"></nav>
</header>
<main id="main"></main>
<script id="donnees" type="application/json">__DONNEES__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("donnees").textContent);
const NIV = { "CRITIQUE": "#E8735A", "A SURVEILLER": "#E9A93B", "FAIBLE": "#4FAE7B", "MAITRISE": "#9AA8B6" };
const DOM_COUL = { M: "#1F3A5F", E: "#1A8C8C", L: "#E8735A" };
const $ = (s, r = document) => r.querySelector(s);
const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fr = iso => iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) : "";
const niveau = c => c >= 6 ? "CRITIQUE" : c >= 3 ? "A SURVEILLER" : c >= 1 ? "FAIBLE" : "MAITRISE";
const pill = n => `<span class="pill" style="background:${NIV[n]}">${n === "A SURVEILLER" ? "À SURVEILLER" : n}</span>`;
const lienPreuve = p => !p ? "" : p.startsWith("http") ? `<a href="${esc(p)}" target="_blank" rel="noopener">source</a>` : esc(p);
const NS = "http://www.w3.org/2000/svg";

document.title = "Radar d'obsolescence : " + D.produit.nom;
$("#titre").textContent = "Radar d'obsolescence : " + D.produit.nom;
$("#src").textContent = (D.source ? "Source : " + D.source + "  |  " : "") + "Généré le " + fr(D.genere) +
  " par radar_obsolescence " + D.version + "  |  Association PPC  |  CC BY-SA 4.0";

const VUES = [["synthese", "Synthèse"], ["radar", "Radar"], ["frise", "Frise"], ["constats", "Constats"],
              ["composants", "Composants"], ["fichiers", "Fichiers"]];
const nav = $("#nav"), main = $("#main");
VUES.forEach(([id, lib]) => {
  const b = document.createElement("button"); b.textContent = lib; b.dataset.vue = id;
  b.onclick = () => montrer(id); nav.appendChild(b);
  const v = document.createElement("section"); v.className = "vue"; v.id = "vue-" + id; main.appendChild(v);
});
function montrer(id) {
  nav.querySelectorAll("button").forEach(b => b.classList.toggle("actif", b.dataset.vue === id));
  main.querySelectorAll(".vue").forEach(v => v.classList.toggle("actif", v.id === "vue-" + id));
  history.replaceState(null, "", "#" + id);
}

// ---------------------------------------------------------------- panneau commun
function panneau() {
  const s = D.synthese, nbAv = D.avertissements.length;
  const actives = D.sources.filter(x => x.actif).map(x => x.nom);
  return `<aside class="panneau">
    <h2>Indice de pérennité</h2>
    <div class="jauge">${jauge(s.indice)}</div>
    <p class="note">100 = aucun risque détecté. L'indice baisse avec la criticité maximale de chaque ligne.</p>
    <div class="kpi">
      <div><b class="c">${s.lignes_critiques}</b><span>lignes critiques (≥ 6)</span></div>
      <div><b class="a">${s.lignes_a_surveiller}</b><span>lignes à surveiller (3 à 5)</span></div>
      <div><b>${D.lignes.length}</b><span>lignes analysées</span></div>
      <div><b>${nbAv}</b><span>avertissement(s)</span></div>
    </div>
    <h2>Calendrier du produit</h2>
    <div class="note">Mise sur le marché : <b>${fr(D.produit.mise_marche)}</b><br>
      Durée de vie cible : <b>${D.produit.duree_vie} ans</b> (horizon ${fr(D.produit.horizon)})<br>
      ${D.produit.fin_support ? "Support annoncé jusqu'au <b>" + fr(D.produit.fin_support) + "</b>" : "Durée de support non renseignée"}</div>
    <h2>Criticité</h2>
    <div class="leg">
      <span class="sw" style="background:${NIV["CRITIQUE"]}"></span><span>Critique : 6 à 9</span>
      <span class="sw" style="background:${NIV["A SURVEILLER"]}"></span><span>À surveiller : 3 à 5</span>
      <span class="sw" style="background:${NIV["FAIBLE"]}"></span><span>Faible : 1 à 2</span>
    </div>
    <p class="note">Criticité = exposition (0 à 3) × gravité de la fonction (1 à 3).</p>
    <h2>Sources de composants</h2>
    <p class="note">${actives.length ? "Interrogées : " + actives.join(", ") : "Aucune : statuts issus de la nomenclature."}</p>
  </aside>`;
}
function jauge(v) {
  const r = 70, cx = 90, cy = 84, a0 = Math.PI, a = Math.PI * (1 - v / 100);
  const pt = t => [cx + r * Math.cos(t), cy - r * Math.sin(t)];
  const [x0, y0] = pt(a0), [x1, y1] = pt(0), [xv, yv] = pt(a);
  const coul = v >= 70 ? "#4FAE7B" : v >= 40 ? "#E9A93B" : "#E8735A";
  return `<svg width="180" height="100" viewBox="0 0 180 100" role="img" aria-label="Indice ${v} sur 100">
    <path d="M${x0},${y0} A${r},${r} 0 0 1 ${x1},${y1}" fill="none" stroke="#E3E9EF" stroke-width="16" stroke-linecap="round"/>
    <path d="M${x0},${y0} A${r},${r} 0 0 1 ${xv.toFixed(1)},${yv.toFixed(1)}" fill="none" stroke="${coul}" stroke-width="16" stroke-linecap="round"/>
    <text x="${cx}" y="${cy - 8}" text-anchor="middle" font-size="34" font-weight="700" fill="#1F3A5F" font-family="Cambria, Georgia, serif">${v}</text>
    <text x="${cx}" y="${cy + 12}" text-anchor="middle" font-size="12" fill="#5B6B7C">sur 100</text></svg>`;
}

// ---------------------------------------------------------------- Synthèse
function vueSynthese() {
  const fam = Object.keys(D.familles), dom = Object.keys(D.domaines);
  const agr = {};
  D.constats.forEach(c => { const k = c.famille + c.domaine; const e = agr[k] ||= { nb: 0, max: 0 }; e.nb++; e.max = Math.max(e.max, c.crit); });
  let mat = `<table class="mat"><tr><th style="text-align:left">Famille de causes</th>${dom.map(d => `<th>${D.domaines[d]}</th>`).join("")}</tr>`;
  fam.forEach(f => {
    mat += `<tr><td class="lib"><span class="code">${f}</span> ${esc(D.familles[f])}</td>`;
    dom.forEach(d => {
      const e = agr[f + d];
      mat += e ? `<td class="cell" style="background:${NIV[niveau(e.max)]};color:#fff" title="${e.nb} constat(s), criticité max ${e.max}" onclick="filtrer('${f}','${d}')">${e.nb}<div style="font-size:11px;font-weight:400">max ${e.max}</div></td>`
               : `<td class="cell" style="background:#EEF2F5;color:#9AA8B6">·</td>`;
    });
    mat += "</tr>";
  });
  mat += "</table>";
  const top = D.lignes.filter(l => l.max > 0).sort((a, b) => b.max - a.max || a.n - b.n);
  $("#vue-synthese").innerHTML = panneau() + `<div class="page">
    <div class="grille2">
      <div class="bloc"><h2>Constats par famille et par domaine</h2>${mat}
        <p class="note">Nombre de constats et criticité maximale. Cliquer sur une case pour voir les constats correspondants.</p></div>
      <div class="bloc"><h2>Lignes les plus exposées</h2><div id="barres"></div>
        <p class="note">Criticité maximale de chaque ligne de nomenclature. Cliquer sur une barre pour voir ses constats.</p></div>
    </div></div>`;
  barres($("#barres"), top);
}
function barres(cible, lignes) {
  const h = 24, w = 520, g = 230, H = lignes.length * h + 26;
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${H}`); svg.setAttribute("width", "100%"); svg.setAttribute("role", "img");
  let s = "";
  for (let k = 0; k <= 9; k += 3) { const x = g + (w - g - 20) * k / 9; s += `<line x1="${x}" y1="0" x2="${x}" y2="${H - 20}" stroke="#E3E9EF"/><text x="${x}" y="${H - 6}" font-size="11" fill="#5B6B7C" text-anchor="middle">${k}</text>`; }
  lignes.forEach((l, i) => {
    const y = i * h + 3, bw = (w - g - 20) * l.max / 9, lib = (l.id + " : " + l.designation);
    s += `<g style="cursor:pointer" onclick="filtrerLigne(${l.n})"><title>${esc(lib)} : criticité ${l.max}</title>
      <text x="${g - 8}" y="${y + 14}" font-size="12" text-anchor="end" fill="#1B2633">${esc(lib.length > 38 ? lib.slice(0, 37) + "…" : lib)}</text>
      <rect x="${g}" y="${y + 2}" width="${bw}" height="${h - 8}" rx="3" fill="${NIV[niveau(l.max)]}"/>
      <text x="${g + bw + 5}" y="${y + 14}" font-size="12" font-weight="700" fill="#1F3A5F">${l.max}</text></g>`;
  });
  svg.innerHTML = s; cible.appendChild(svg);
}

// ---------------------------------------------------------------- Radar
function vueRadar() {
  const fam = Object.keys(D.familles), dom = Object.keys(D.domaines);
  const R = 165, cx = 310, cy = 225, n = fam.length;
  const ang = i => -Math.PI / 2 + 2 * Math.PI * i / n;
  const pt = (i, v) => [cx + R * v / 9 * Math.cos(ang(i)), cy + R * v / 9 * Math.sin(ang(i))];
  let s = "";
  [3, 6, 9].forEach(v => { s += `<polygon points="${fam.map((_, i) => pt(i, v).join(",")).join(" ")}" fill="none" stroke="#D5DDE5"/>`;
    s += `<text x="${cx + 4}" y="${cy - R * v / 9 + 12}" font-size="10" fill="#9AA8B6">${v}</text>`; });
  fam.forEach((f, i) => {
    const [x, y] = pt(i, 9), [xl, yl] = pt(i, 10.6);
    s += `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#D5DDE5"/>`;
    const anchor = Math.abs(Math.cos(ang(i))) < 0.2 ? "middle" : Math.cos(ang(i)) > 0 ? "start" : "end";
    const court = D.familles[f].split(/[ /(]/)[0];
    s += `<text x="${xl}" y="${yl + 4}" font-size="13" font-weight="700" fill="#1F3A5F" text-anchor="${anchor}">${f} · ${esc(court)}</text>`;
  });
  const val = {}; D.constats.forEach(c => { const k = c.domaine + c.famille; val[k] = Math.max(val[k] || 0, c.crit); });
  dom.forEach(d => {
    if (!fam.some(f => val[d + f])) return;
    const pts = fam.map((f, i) => pt(i, val[d + f] || 0).join(",")).join(" ");
    s += `<polygon class="poly" data-d="${d}" points="${pts}" fill="${DOM_COUL[d]}" fill-opacity=".16" stroke="${DOM_COUL[d]}" stroke-width="2.5"/>`;
    fam.forEach((f, i) => { if (val[d + f]) { const [x, y] = pt(i, val[d + f]); s += `<circle cx="${x}" cy="${y}" r="4" fill="${DOM_COUL[d]}"><title>${D.domaines[d]}, famille ${f} : criticité max ${val[d + f]}</title></circle>`; } });
  });
  const leg = dom.map(d => `<span class="sw" style="background:${DOM_COUL[d]}"></span><span>${D.domaines[d]}</span>`).join("");
  const fams = fam.map(f => `<li><span><span class="code">${f}</span> ${esc(D.familles[f])}</span></li>`).join("");
  $("#vue-radar").innerHTML = panneau() + `<div class="page"><div class="bloc"><h2>Radar des causes d'obsolescence</h2>
    <div style="display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start">
      <svg viewBox="0 0 620 460" width="620" style="max-width:100%" role="img" aria-label="Radar des criticités par famille et domaine">${s}</svg>
      <div style="min-width:260px;flex:1"><h3 style="color:var(--marine);font-size:15px;margin:0 0 8px">Domaines</h3><div class="leg">${leg}</div>
        <h3 style="color:var(--marine);font-size:15px;margin:16px 0 8px">Familles de causes</h3><ul class="cibles">${fams}</ul>
        <p class="note">Chaque axe porte la criticité maximale (0 à 9) relevée dans une famille de causes. Plus la surface d'un domaine est grande, plus il concentre les risques.</p></div>
    </div></div></div>`;
}

// ---------------------------------------------------------------- Frise
function vueFrise() {
  const p = D.produit, ev = D.echeances;
  const t = iso => new Date(iso + "T00:00:00").getTime();
  const auj = new Date(D.genere + "T00:00:00").getTime();
  const dates = [t(p.mise_marche), t(p.horizon), auj, ...ev.map(e => t(e.date))];
  const y0 = new Date(Math.min(...dates)).getFullYear(), y1 = new Date(Math.max(...dates)).getFullYear() + 1;
  const g = 300, w = 1080, h = 26, top = 72, H = top + Math.max(ev.length, 1) * h + 30;
  const X = ms => g + (w - g - 20) * (ms - new Date(y0, 0, 1).getTime()) / (new Date(y1, 0, 1).getTime() - new Date(y0, 0, 1).getTime());
  let s = `<rect x="${X(t(p.mise_marche))}" y="${top - 8}" width="${X(t(p.horizon)) - X(t(p.mise_marche))}" height="${H - top - 14}" fill="#EAF5F5"/>`;
  for (let y = y0; y <= y1; y++) { const x = X(new Date(y, 0, 1).getTime());
    s += `<line x1="${x}" y1="${top - 8}" x2="${x}" y2="${H - 22}" stroke="#E3E9EF"/>`;
    if ((y - y0) % (y1 - y0 > 16 ? 2 : 1) === 0) s += `<text x="${x}" y="${H - 6}" font-size="11" text-anchor="middle" fill="#5B6B7C">${y}</text>`; }
  // repères verticaux ; libellés répartis sur trois niveaux pour éviter les chevauchements
  const HALO = 'stroke="#fff" stroke-width="3" paint-order="stroke"';
  const reperes = [[t(p.mise_marche), "Mise sur le marché", "#1A8C8C"], [auj, "Aujourd'hui", "#5B6B7C"],
                   [t(p.horizon), "Horizon " + p.duree_vie + " ans", "#1F3A5F"]];
  if (p.fin_support) reperes.push([t(p.fin_support), "Fin du support annoncé", "#B7791F"]);
  reperes.sort((a, b) => a[0] - b[0]);
  const finNiveau = [-1e9, -1e9, -1e9];
  reperes.forEach(([ms, lib, coul]) => {
    const x = X(ms), larg = lib.length * 6.6 + 8, fin = x > w - larg ? "end" : "start";
    const x0 = fin === "end" ? x - larg : x;
    let n = finNiveau.findIndex(f => f < x0); if (n < 0) n = 2; finNiveau[n] = x0 + larg;
    s += `<line x1="${x}" y1="${top - 8}" x2="${x}" y2="${H - 22}" stroke="${coul}" stroke-width="2" stroke-dasharray="5 4"/>
      <line x1="${x}" y1="${top - 22 - 16 * n}" x2="${x}" y2="${top - 8}" stroke="${coul}" stroke-width="1"/>
      <text x="${fin === "end" ? x - 4 : x + 4}" y="${top - 12 - 16 * n}" font-size="12" font-weight="700" fill="${coul}" text-anchor="${fin}" ${HALO}>${lib}</text>`;
  });
  ev.forEach((e, i) => {
    const y = top + i * h, x = X(t(e.date)), avant = t(e.date) < t(p.horizon);
    const critique = t(e.date) <= auj || (p.fin_support && t(e.date) < t(p.fin_support));
    const coul = critique ? "#E8735A" : avant ? "#E9A93B" : "#4FAE7B";
    const lib = e.id + " : " + e.nature;
    s += `<g><title>${esc(e.ligne)} : ${esc(e.nature)} le ${fr(e.date)} (${esc(e.source)})</title>
      <text x="${g - 10}" y="${y + 15}" font-size="12" text-anchor="end" fill="#1B2633">${esc(lib.length > 44 ? lib.slice(0, 43) + "…" : lib)}</text>
      ${t(e.date) > t(p.mise_marche) ? `<line x1="${X(t(p.mise_marche))}" y1="${y + 11}" x2="${x}" y2="${y + 11}" stroke="${coul}" stroke-width="3" stroke-opacity=".45"/>` : ""}
      <circle cx="${x}" cy="${y + 11}" r="6" fill="${coul}" stroke="#fff" stroke-width="1.5"/>
      <text x="${x + 10}" y="${y + 15}" font-size="11" fill="#5B6B7C" ${HALO}>${fr(e.date)}</text></g>`;
  });
  const vide = ev.length ? "" : `<p class="alerte">Aucune échéance datée : renseigner les colonnes date_fin_support, disponibilite_pieces_ans ou logiciel_produit.</p>`;
  $("#vue-frise").innerHTML = panneau() + `<div class="page"><div class="bloc" style="max-width:none"><h2>Frise des échéances</h2>${vide}
    <div><svg viewBox="0 0 ${w} ${H}" width="100%" style="max-width:${w}px;min-width:720px" role="img" aria-label="Frise des échéances">${s}</svg></div>
    <div class="leg" style="margin-top:10px;grid-template-columns:auto 1fr auto 1fr auto 1fr">
      <span class="sw" style="background:#E8735A"></span><span>Déjà passée ou avant la fin du support annoncé</span>
      <span class="sw" style="background:#E9A93B"></span><span>Avant l'horizon du produit</span>
      <span class="sw" style="background:#4FAE7B"></span><span>Après l'horizon</span></div>
    <p class="note">Bande verte claire : durée de vie cible du produit. Chaque point est une date de fin connue : fin de vie d'un logiciel (endoflife.date), fin de support déclarée, fin de disponibilité des pièces, dernière commande annoncée par un distributeur.</p>
  </div></div>`;
}

// ---------------------------------------------------------------- Constats
function vueConstats() {
  const opt = (id, lib, vals) => `<select id="${id}"><option value="">${lib}</option>${vals.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("")}</select>`;
  $("#vue-constats").innerHTML = `<div class="page"><div class="bloc" style="max-width:none"><h2>Constats classés par criticité</h2>
    <div class="outils">${opt("f-niv", "Tous niveaux", [["CRITIQUE", "Critique"], ["A SURVEILLER", "À surveiller"], ["FAIBLE", "Faible"]])}
      ${opt("f-dom", "Tous domaines", Object.entries(D.domaines))}
      ${opt("f-fam", "Toutes familles", Object.entries(D.familles).map(([k, v]) => [k, k + " : " + v]))}
      ${opt("f-lig", "Toutes lignes", D.lignes.filter(l => l.max).map(l => [String(l.n), l.id + " : " + l.designation]))}
      <input id="f-txt" type="search" placeholder="Rechercher…">
      <span class="aide" id="f-nb"></span></div>
    <table><thead><tr><th>Criticité</th><th>Ligne</th><th>Constat</th><th>Détail et recommandation</th><th>Preuve</th></tr></thead><tbody id="t-constats"></tbody></table></div></div>`;
  ["f-niv", "f-dom", "f-fam", "f-lig", "f-txt"].forEach(id => $("#" + id).addEventListener("input", majConstats));
  majConstats();
}
function majConstats() {
  const v = id => $("#" + id).value, txt = v("f-txt").toLowerCase();
  const liste = D.constats.filter(c => (!v("f-niv") || c.niveau === v("f-niv")) && (!v("f-dom") || c.domaine === v("f-dom"))
    && (!v("f-fam") || c.famille === v("f-fam")) && (!v("f-lig") || String(c.n) === v("f-lig"))
    && (!txt || (c.ligne + c.intitule + c.detail + c.reco).toLowerCase().includes(txt)));
  $("#f-nb").textContent = liste.length + " constat(s) sur " + D.constats.length;
  $("#t-constats").innerHTML = liste.map(c => `<tr><td class="num"><b style="font-size:18px;color:${NIV[c.niveau]}">${c.crit}</b><br>${pill(c.niveau)}</td>
    <td>${esc(c.ligne)}<br><span class="note">${D.domaines[c.domaine] || c.domaine}</span></td>
    <td><span class="code">${c.code}</span> ${esc(c.intitule)}<br><span class="note">exposition ${c.expo} × gravité ${c.grav}</span></td>
    <td>${esc(c.detail)}<div class="reco">${esc(c.reco)}</div></td><td>${lienPreuve(c.preuve)}${c.auto ? '<br><span class="note">automatique</span>' : ""}</td></tr>`).join("")
    || `<tr><td colspan="5" class="note">Aucun constat pour ce filtre.</td></tr>`;
}
function filtrer(f, d) { montrer("constats"); $("#f-fam").value = f; $("#f-dom").value = d; $("#f-lig").value = ""; majConstats(); }
function filtrerLigne(n) { montrer("constats"); $("#f-fam").value = ""; $("#f-dom").value = ""; $("#f-lig").value = String(n); majConstats(); }

// ---------------------------------------------------------------- Composants
function vueComposants() {
  const STAT = { PRODUCTION: "#4FAE7B", ACTIF: "#4FAE7B", NEW: "#4FAE7B", NOUVEAU: "#4FAE7B", NRND: "#E9A93B", LTB: "#E8735A", EOL: "#E8735A", OBSOLETE: "#E8735A", ARRET_DISTRIBUTEUR: "#E9A93B", INCONNU: "#9AA8B6" };
  const cyc = D.cycles.map(c => `<tr><td>${esc(c.ligne)}</td><td><code>${esc(c.mpn)}</code></td>
    <td><span class="pill" style="background:${STAT[c.statut] || "#9AA8B6"}">${esc(c.statut)}</span></td><td>${esc(c.source)}</td><td class="note">${esc(c.detail)}</td></tr>`).join("");
  const av = D.avertissements.map(a => `<div class="alerte">${esc(a)}</div>`).join("") || `<p class="note">Aucun avertissement.</p>`;
  $("#vue-composants").innerHTML = `<div class="page">
    <div class="bloc"><h2>Statuts de cycle de vie des composants électroniques</h2>
      ${cyc ? `<table><tr><th>Ligne</th><th>Référence</th><th>Statut</th><th>Source</th><th>Détail</th></tr>${cyc}</table>` : `<p class="note">Aucun composant électronique avec référence fabricant.</p>`}
      <p class="note">La source indique d'où vient le statut : distributeur interrogé (Mouser, DigiKey, Nexar) ou saisie dans la nomenclature.</p></div>
    <div class="bloc"><h2>Avertissements (données manquantes ou sources indisponibles)</h2>${av}</div></div>`;
}

// ---------------------------------------------------------------- Fichiers
function vueFichiers() {
  $("#vue-fichiers").innerHTML = `<div class="page">
    <div class="bloc"><h2>Fichiers produits par le radar</h2><div class="dl">
      <a href="rapport_obsolescence.md">rapport_obsolescence.md</a><a href="constats.csv">constats.csv</a><a href="constats.xlsx">constats.xlsx</a></div>
      <p class="note">Le rapport Markdown se lit dans tout éditeur de texte ou sur GitHub ; constats.xlsx se filtre dans Excel ou LibreOffice.</p></div>
    <div class="bloc"><h2>Sources de données ouvertes</h2><table>
      <tr><th>Source</th><th>Usage</th></tr>
      <tr><td><a href="https://endoflife.date" target="_blank" rel="noopener">endoflife.date</a></td><td>Fin de vie des systèmes, langages et bibliothèques</td></tr>
      <tr><td><a href="https://deps.dev" target="_blank" rel="noopener">deps.dev (Open Source Insights)</a></td><td>Paquets dépréciés, avis de sécurité, date de publication</td></tr>
      <tr><td><a href="https://scorecard.dev" target="_blank" rel="noopener">OpenSSF Scorecard</a></td><td>Maintenance des dépôts open source</td></tr>
      <tr><td><a href="https://www.mouser.com/en/api-search/" target="_blank" rel="noopener">Mouser Search API</a>, <a href="https://developer.digikey.com/" target="_blank" rel="noopener">DigiKey Product Information V4</a>, <a href="https://nexar.com/api" target="_blank" rel="noopener">Nexar</a></td><td>Cycle de vie des composants électroniques (clé gratuite)</td></tr>
      <tr><td><a href="https://openrepair.org/open-data/" target="_blank" rel="noopener">Open Repair Alliance</a></td><td>Pannes observées par catégorie de produit</td></tr></table></div>
    <div class="bloc"><h2>Licence</h2><p class="note">Visualiseur produit par l'outil libre PPC « radar-obsolescence » (code sous licence MIT). Méthode et documentation sous licence CC BY-SA 4.0 : réutilisation et adaptation libres, en citant « Association PPC » et en partageant sous la même licence.</p></div></div>`;
}

vueSynthese(); vueRadar(); vueFrise(); vueConstats(); vueComposants(); vueFichiers();
const depart = location.hash.slice(1);
montrer(VUES.some(v => v[0] === depart) ? depart : "synthese");
window.addEventListener("hashchange", () => { const h = location.hash.slice(1); if (VUES.some(v => v[0] === h)) montrer(h); });
</script>
</body>
</html>
"""
