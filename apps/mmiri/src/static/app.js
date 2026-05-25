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
      const tile = document.createElement("article");
      tile.className = "tile";
      tile.style.setProperty("--tile-color", color);
      tile.innerHTML = `
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
