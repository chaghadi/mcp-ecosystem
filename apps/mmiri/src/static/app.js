// app.js — render the 8 ogbe with their MCP tiles, handle modal expansion,
// poll the live status of mcp-analytics from the FastAPI backend.

const CATEGORY_LABELS = {
  data:       "postgres · redis · storage · search",
  business:   "auth · users · billing · comms · analytics · webhooks",
  dev:        "scaffold · git · docker · tests · linting · deps",
  infra:      "vercel · digitalocean · cloudflare · ssl · monitor · backup",
  marketing:  "social · content · SEO · email · A/B · press",
  scheduling: "calendar · cron · releases · standups · time",
  launch:     "payments · app stores · waitlist · product hunt",
  team:       "slack · docs · onboarding · code review · figma",
};

// Each animal chosen for what its nature mirrors in the MCP's job.
// Hippo on mcp-docs is a deliberate Niger reference.
const ANIMALS = {
  // data — the foundation
  "mcp-postgres":      { emoji: "🐘", reason: "long memory, holds the whole record" },
  "mcp-redis":         { emoji: "🐇", reason: "speed — in-memory cache" },
  "mcp-storage":       { emoji: "🦫", reason: "builder, gatherer of files" },
  "mcp-search":        { emoji: "🦅", reason: "sharp vision, finds from afar" },

  // business — the spine
  "mcp-auth":          { emoji: "🦉", reason: "watchful guardian at the gate" },
  "mcp-user-mgmt":     { emoji: "🐝", reason: "the community, organised" },
  "mcp-billing":       { emoji: "🐿️", reason: "saves, collects, accounts" },
  "mcp-notifications": { emoji: "🕊️", reason: "the messenger" },
  "mcp-analytics":     { emoji: "🦊", reason: "observant, follows the trail" },
  "mcp-webhooks":      { emoji: "🐓", reason: "announces every event" },

  // dev — the workshop
  "mcp-blueprint":     { emoji: "🕷️", reason: "weaves the architecture" },
  "mcp-git-ops":       { emoji: "🐙", reason: "many arms, many branches" },
  "mcp-scaffold":      { emoji: "🐦", reason: "nest-builder" },
  "mcp-env":           { emoji: "🦎", reason: "adapts to its surroundings" },
  "mcp-docker-ops":    { emoji: "🐳", reason: "carries containers" },
  "mcp-test-runner":   { emoji: "🐆", reason: "fastest creature for fast checks" },
  "mcp-linter":        { emoji: "🦝", reason: "picky, washes everything first" },
  "mcp-changelog":     { emoji: "🐢", reason: "slow, holds the whole history" },
  "mcp-deps":          { emoji: "🐜", reason: "an interconnected colony" },

  // infra — the ground
  "mcp-vercel":        { emoji: "🐎", reason: "fast delivery" },
  "mcp-digitalocean":  { emoji: "🐬", reason: "lives in the ocean" },
  "mcp-cloudflare":    { emoji: "🦢", reason: "graceful, lives in the sky" },
  "mcp-ssl":           { emoji: "🦔", reason: "armored — its job is to protect" },
  "mcp-monitor":       { emoji: "🦦", reason: "always watching the surface" },
  "mcp-backup":        { emoji: "🦡", reason: "stores reserves underground" },

  // marketing — outward voice
  "mcp-social-post":   { emoji: "🦜", reason: "broadcasts, repeats" },
  "mcp-social-listen": { emoji: "🦇", reason: "ear-first, hears chatter" },
  "mcp-content-gen":   { emoji: "🦚", reason: "creative display" },
  "mcp-seo":           { emoji: "🐠", reason: "climbs the rankings" },
  "mcp-email-campaign":{ emoji: "🦋", reason: "delicate at scale" },
  "mcp-ab-test":       { emoji: "🦓", reason: "two patterns, side by side" },
  "mcp-press":         { emoji: "🦁", reason: "the loudest roar" },

  // scheduling — time
  "mcp-calendar":      { emoji: "🐧", reason: "punctual, formal" },
  "mcp-cron":          { emoji: "🦗", reason: "rhythmic, regular chirp" },
  "mcp-release-plan":  { emoji: "🦒", reason: "the long view, milestones reached" },
  "mcp-standup":       { emoji: "🦌", reason: "the herd, gathered" },
  "mcp-time-track":    { emoji: "🐹", reason: "the wheel that keeps turning" },

  // launch — going to market
  "mcp-coinbase":      { emoji: "🐉", reason: "hoards gold" },
  "mcp-appstore":      { emoji: "🦩", reason: "premium, stands out" },
  "mcp-playstore":     { emoji: "🐸", reason: "ubiquitous, lives everywhere" },
  "mcp-product-hunt":  { emoji: "🐺", reason: "the hunter" },
  "mcp-waitlist":      { emoji: "🦆", reason: "the orderly queue" },

  // team — inside the house
  "mcp-slack-ops":     { emoji: "🐒", reason: "social, always chattering" },
  "mcp-docs":          { emoji: "🦛", reason: "the river's resident — knows it all" },
  "mcp-onboarding":    { emoji: "🦘", reason: "carries the new one in the pouch" },
  "mcp-code-review":   { emoji: "🐕", reason: "loyal, faithful inspector" },
  "mcp-figma-ops":     { emoji: "🪼", reason: "fluid, takes any shape" },
};

const CATEGORY_COLORS = {
  data: "#38BDF8", business: "#2DD4BF", dev: "#818CF8", infra: "#FB923C",
  marketing: "#F472B6", scheduling: "#34D399", launch: "#FBBF24", team: "#C084FC",
};

async function loadCatalog() {
  const res = await fetch("/static/catalog.json");
  return res.json();
}

function renderOgbe(catalog) {
  const container = document.getElementById("ogbe-list");
  const grouped = {};
  for (const mcp of Object.values(catalog)) {
    (grouped[mcp.category] = grouped[mcp.category] || []).push(mcp);
  }

  const order = ["data","business","dev","infra","marketing","scheduling","launch","team"];
  for (const cat of order) {
    const mcps = grouped[cat];
    if (!mcps) continue;
    const color = CATEGORY_COLORS[cat];
    const metaText = CATEGORY_LABELS[cat] || "";

    const section = document.createElement("section");
    section.className = "ogbe";
    section.innerHTML = `
      <div class="ogbe-header">
        <span class="ogbe-cat-stripe" style="background:${color}"></span>
        <h2 class="ogbe-name">${cat}</h2>
        <span class="ogbe-count">${mcps.length} MCPs · ${mcps.reduce((s, m) => s + m.tool_count, 0)} tools</span>
        <span class="ogbe-meta">${metaText}</span>
      </div>
      <div class="tile-grid" id="grid-${cat}"></div>
    `;
    container.appendChild(section);

    const grid = section.querySelector(".tile-grid");
    mcps.sort((a, b) => a.name.localeCompare(b.name));
    for (const mcp of mcps) {
      const animal = ANIMALS[mcp.name] || { emoji: "🌊", reason: "" };
      const tile = document.createElement("article");
      tile.className = "tile";
      tile.setAttribute("data-cat", cat);
      tile.style.setProperty("--tile-color", color);
      tile.innerHTML = `
        <div class="tile-animal" aria-hidden="true">${animal.emoji}</div>
        <div class="tile-name">${mcp.name}</div>
        <div class="tile-row">
          <span class="tile-status">
            <span class="dot ${mcp.status}"></span>
            <span>${mcp.status === "live" ? "live" : "pending"}</span>
          </span>
          <span class="tile-tools">${mcp.tool_count} tools</span>
        </div>
      `;
      tile.addEventListener("click", () => openModal(mcp, color));
      grid.appendChild(tile);
    }
  }
}

function openModal(mcp, color) {
  const modal = document.getElementById("modal");
  const animal = ANIMALS[mcp.name] || { emoji: "🌊", reason: "" };
  document.getElementById("modal-animal").textContent = animal.emoji;
  document.getElementById("modal-animal-reason").textContent =
    animal.reason ? `— ${animal.reason}` : "";
  document.getElementById("modal-cat").textContent = mcp.category;
  document.getElementById("modal-cat").style.background = color;
  document.getElementById("modal-title").textContent = mcp.name;
  document.getElementById("modal-desc").textContent = mcp.description || "—";
  document.getElementById("modal-status").innerHTML =
    `<span class="dot ${mcp.status}"></span>${mcp.status === "live" ? "live" : "pending credentials"}`;
  document.getElementById("modal-count").textContent = `${mcp.tool_count} tools`;
  document.querySelector(".modal-card").style.setProperty("--tile-color", color);

  const list = document.getElementById("modal-tools");
  list.innerHTML = "";
  for (const t of mcp.tools) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="tool-name">${t.name}()</span>
      <span class="tool-doc">${t.doc || ""}</span>
    `;
    list.appendChild(li);
  }
  modal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  document.getElementById("modal").hidden = true;
  document.body.style.overflow = "";
}

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-backdrop").addEventListener("click", closeModal);
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

// Live hero status
async function refreshStatus() {
  const dot     = document.getElementById("dot");
  const text    = document.getElementById("hero-status-text");
  const visits  = document.getElementById("hero-visits");
  try {
    const h = await fetch("/api/health").then(r => r.json());
    if (h.ok && h.mcp_analytics === "connected") {
      dot.className = "dot connected";
      text.textContent = "mcp-analytics · connected";
    } else {
      dot.className = "dot error";
      text.textContent = `mcp-analytics · ${h.details?.error || "error"}`;
    }
  } catch {
    dot.className = "dot error";
    text.textContent = "mcp-analytics · unreachable";
    return;
  }
  try {
    const v = await fetch("/api/visit-count").then(r => r.json());
    if (v.ok) {
      visits.textContent = `${(v.page_views || 0).toLocaleString()} visits`;
    } else {
      visits.textContent = "— visits";
    }
  } catch {
    visits.textContent = "— visits";
  }
}

(async function init() {
  const catalog = await loadCatalog();
  renderOgbe(catalog);
  refreshStatus();
  setInterval(refreshStatus, 10000);
})();
