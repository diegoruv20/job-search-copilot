const state = {
  jobs: [],
  jobIndex: new Map(),
  meta: { statuses: [], tiers: [] },
  editingJob: null,
  sankeyData: null,
  sankeySnapshots: [],
  sankeyFrames: [],
  sankeyFrameIndex: 0,
  sankeyGraph: null,
  sankeyPlaybackTimer: null,
  sankeyPlaying: false,
  sankeyRequestSequence: 0,
};

const $ = (selector) => document.querySelector(selector);
const slug = (value) => (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const displayDate = (value) => value
  ? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
  : "No date";
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, character => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
})[character]);
const onboardingPrompt = "Use the career-discovery agent. Interview me to build my job-search profile and experience inventory. Ask three to five simple questions at a time, update the files after every round, and help me identify realistic role families and positioning.";

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

function optionMarkup(values, selected = "") {
  return values.map(value => `<option value="${value}" ${value === selected ? "selected" : ""}>${value}</option>`).join("");
}

function tierChip(tier) {
  return `<span class="tier-chip tier-${slug(tier)}">${tier}</span>`;
}

function statusChip(status) {
  return `<span class="status-chip status-${slug(status)}">${status}</span>`;
}

function freshnessChip(job) {
  if (job.posting_age_days === null) {
    return `<span class="freshness-chip freshness-unknown">Age unknown</span>`;
  }
  return `<span class="freshness-chip freshness-${slug(job.freshness_bucket)}">${job.posting_age_days}d old</span>`;
}

async function loadAll() {
  const [meta, stats, recommendations, jobs, history, sankey, sankeySnapshots, workspace] = await Promise.all([
    api("/api/meta"),
    api("/api/stats"),
    api("/api/recommendations"),
    loadJobs(false),
    api("/api/history"),
    api("/api/sankey"),
    api("/api/sankey/snapshots"),
    api("/api/workspace"),
  ]);
  state.meta = meta;
  renderSelects();
  renderStats(stats);
  renderFreshness(stats.freshness_conversion);
  renderRecommendations(recommendations);
  renderWorkspace(workspace);
  renderHistory(history);
  renderSankeyHistory(sankeySnapshots, sankey);
  renderSankey(sankey);
  return jobs;
}

async function loadJobs(render = true) {
  const params = new URLSearchParams();
  const q = $("#search-input")?.value.trim();
  const status = $("#status-filter")?.value;
  const tier = $("#tier-filter")?.value;
  const archive = $("#archive-filter")?.value || "active";
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (tier) params.set("tier", tier);
  params.set("archive", archive);
  state.jobs = await api(`/api/jobs?${params}`);
  state.jobs.forEach(job => state.jobIndex.set(job.id, job));
  if (render) renderJobs();
  return state.jobs;
}

function renderSelects() {
  $("#status-filter").insertAdjacentHTML("beforeend", optionMarkup(state.meta.statuses));
  $("#tier-filter").insertAdjacentHTML("beforeend", optionMarkup(state.meta.tiers));
  $("#status").innerHTML = optionMarkup(state.meta.statuses);
  $("#recommendation-tier").innerHTML = optionMarkup(state.meta.tiers);
  $("#not-fit-category").innerHTML =
    `<option value="">Select primary reason</option>${optionMarkup(state.meta.not_fit_categories)}`;
  $("#freshness-confidence").innerHTML =
    `<option value="">Select confidence</option>${optionMarkup(state.meta.freshness_confidence)}`;
}

function renderStats(stats) {
  $("#active-stat").textContent = stats.active_applications;
  $("#applied-stat").textContent = stats.applied;
  $("#interview-stat").textContent = stats.interviews;
  $("#followup-stat").textContent = stats.follow_ups_due;
  $("#offer-stat").textContent = stats.offers;
}

function renderFreshness(rows) {
  const container = $("#freshness-conversion");
  container.innerHTML = rows.map(row => `
    <article class="freshness-card">
      <span>${escapeHtml(row.bucket)}</span>
      <strong>${row.conversion_rate === null ? "—" : `${row.conversion_rate}%`}</strong>
      <small>${row.recruiter_screens}/${row.applications} reached recruiter screen</small>
    </article>
  `).join("");
}

function renderRecommendations(jobs) {
  const container = $("#recommendations");
  jobs.forEach(job => state.jobIndex.set(job.id, job));
  if (!jobs.length) {
    container.innerHTML = `<div class="empty-state">No recommendations queued.</div>`;
    return;
  }
  container.innerHTML = jobs.map((job, index) => `
    <article class="recommendation-card" data-job-id="${job.id}">
      <span class="rank">${job.recommendation_rank || index + 1}</span>
      ${tierChip(job.recommendation_tier)}
      ${freshnessChip(job)}
      <h3>${escapeHtml(job.company)}</h3>
      <p class="role">${escapeHtml(job.role)}</p>
      <p class="fit">${escapeHtml(job.fit_summary || job.next_action || "Review this opportunity.")}</p>
    </article>
  `).join("");
}

function renderWorkspace(workspace) {
  const panel = $("#workspace-panel");
  panel.hidden = workspace.profile.ready;
  if (workspace.profile.ready) return;

  const checks = [
    ["Tracker database", workspace.checks.database_exists],
    ["Tracker MCP", workspace.checks.mcp_configured],
    ["Playwright MCP", workspace.checks.playwright_mcp_configured && workspace.checks.node_available],
    ["Career profile", workspace.checks.profile_ready],
  ];
  $("#readiness-list").innerHTML = checks.map(([label, ready]) => `
    <div class="readiness-item">
      <span class="readiness-icon ${ready ? "is-ready" : ""}">${ready ? "✓" : "·"}</span>
      <div><strong>${escapeHtml(label)}</strong><small>${ready ? "Ready" : "Action needed"}</small></div>
    </div>
  `).join("");
}

function sankeyColor(name) {
  if (name === "Not a fit" || name === "Withdrawn" || name.startsWith("Rejected ")) return "#f87171";
  if (name === "Offer") return "#f5b84b";
  if (["Advanced to interviews", "Active interviewing", "Final interview", "Final interview active"].includes(name)) return "#35d39a";
  if (["Applied", "Resume review", "No response yet"].includes(name)) return "#4ea5ff";
  if (["Not applied", "Ready to apply", "Referral prep", "Researching / preparing", "On hold"].includes(name)) return "#8b7cf6";
  return "#64748b";
}

const sankeyNodeOrder = new Map([
  ["Tracked roles", 0],
  ["Applied", 10],
  ["Resume review", 20],
  ["Advanced to interviews", 30],
  ["No response yet", 40],
  ["Rejected at resume review", 50],
  ["Withdrawn", 55],
  ["Final interview", 60],
  ["Active interviewing", 70],
  ["Rejected during interviews", 80],
  ["Offer", 90],
  ["Final interview active", 100],
  ["Rejected after final interview", 110],
  ["Not applied", 130],
  ["Ready to apply", 140],
  ["Referral prep", 150],
  ["Researching / preparing", 160],
  ["On hold", 170],
  ["Not a fit", 180],
  ["Required experience / seniority", 190],
  ["Required technology stack", 200],
  ["Role specialization mismatch", 210],
  ["Work-life / on-call", 220],
  ["Location / office requirement", 230],
  ["Compensation insufficient", 240],
  ["Posting stale / high competition", 250],
  ["Superseded by stronger opportunity", 260],
  ["Excluded company / industry", 270],
  ["Other documented reason", 280],
]);

function sankeyOrder(name) {
  return sankeyNodeOrder.get(name) ?? Number.MAX_SAFE_INTEGER;
}

function sankeyDepth(name) {
  if (name === "Tracked roles") return 0;
  if (["Applied", "Not applied"].includes(name)) return 1;
  if (["Resume review", "Ready to apply", "Referral prep", "Researching / preparing", "On hold", "Not a fit"].includes(name)) return 2;
  if (["No response yet", "Rejected at resume review", "Advanced to interviews", "Withdrawn"].includes(name)) return 3;
  if (["Active interviewing", "Rejected during interviews", "Final interview"].includes(name)) return 4;
  if (["Final interview active", "Rejected after final interview", "Offer"].includes(name)) return 5;
  if (
    [
      "Required experience / seniority",
      "Required technology stack",
      "Role specialization mismatch",
      "Work-life / on-call",
      "Location / office requirement",
      "Compensation insufficient",
      "Posting stale / high competition",
      "Superseded by stronger opportunity",
      "Excluded company / industry",
      "Other documented reason",
    ].includes(name)
  ) return 3;
  return 2;
}

function sankeyLinkId(link) {
  const source = typeof link.source === "object" ? link.source.name : link.source;
  const target = typeof link.target === "object" ? link.target.name : link.target;
  return `${source}→${target}`;
}

function sankeyNodeCenter(node) {
  return (node.y0 + node.y1) / 2;
}

function collapsedLink(link, atTarget = false) {
  const anchor = atTarget ? link.target : link.source;
  const x = atTarget ? anchor.x0 : anchor.x1;
  const y = sankeyNodeCenter(anchor);
  return {
    ...link,
    source: { ...link.source, x1: x },
    target: { ...link.target, x0: x },
    y0: y,
    y1: y,
  };
}

function enteringNodeGeometry(node, previousGraph) {
  const previousNodes = new Map((previousGraph?.nodes || []).map(item => [item.name, item]));
  const previousNode = previousNodes.get(node.name);
  if (previousNode) return previousNode;

  const sourceName = node.targetLinks[0]?.source?.name;
  const source = previousNodes.get(sourceName);
  if (source) {
    const center = sankeyNodeCenter(source);
    return { x0: source.x1, x1: source.x1 + 1, y0: center, y1: center };
  }

  const center = sankeyNodeCenter(node);
  return { x0: node.x0, x1: node.x1, y0: center, y1: center };
}

function exitingNodeGeometry(node, nextGraph) {
  const nextNodes = new Map((nextGraph?.nodes || []).map(item => [item.name, item]));
  const sourceName = node.targetLinks[0]?.source?.name;
  const source = nextNodes.get(sourceName);
  if (source) {
    const center = sankeyNodeCenter(source);
    return { x0: source.x1, x1: source.x1 + 1, y0: center, y1: center };
  }
  const center = sankeyNodeCenter(node);
  return { x0: node.x0, x1: node.x1, y0: center, y1: center };
}

function frameLabel(frame) {
  if (frame.live) return "Live view";
  const prefix = frame.reason.startsWith("Estimated replay") ? "Estimated" : "Exact";
  return `${prefix} · ${new Date(frame.created_at).toLocaleDateString()}`;
}

function renderSankeyHistory(snapshots, liveData) {
  state.sankeySnapshots = snapshots;
  state.sankeyFrames = [
    ...snapshots.slice().reverse().map(snapshot => ({ ...snapshot, live: false, data: null })),
    { id: "", live: true, reason: "Live view", created_at: new Date().toISOString(), data: liveData },
  ];
  state.sankeyFrameIndex = state.sankeyFrames.length - 1;
  $("#sankey-snapshot-select").innerHTML = [
    `<option value="">Live view</option>`,
    ...snapshots.map(snapshot => {
      const label = `${new Date(snapshot.created_at).toLocaleString()} — ${snapshot.reason}`;
      return `<option value="${snapshot.id}">${escapeHtml(label)}</option>`;
    }),
  ].join("");
  $("#sankey-view-note").textContent = "Current pipeline";
  const range = $("#sankey-timeline-range");
  range.max = String(Math.max(0, state.sankeyFrames.length - 1));
  range.value = String(state.sankeyFrameIndex);
  const firstHistorical = state.sankeyFrames.find(frame => !frame.live);
  $("#sankey-timeline-start").textContent = firstHistorical
    ? new Date(firstHistorical.created_at).toLocaleDateString()
    : "First snapshot";
  updateSankeyPlaybackControls();
}

function updateSankeyPlaybackControls() {
  const lastIndex = state.sankeyFrames.length - 1;
  const currentFrame = state.sankeyFrames[state.sankeyFrameIndex];
  $("#sankey-timeline-range").value = String(state.sankeyFrameIndex);
  $("#sankey-timeline-label").textContent = currentFrame ? frameLabel(currentFrame) : "Live view";
  $("#sankey-rewind").disabled = state.sankeyFrameIndex <= 0;
  $("#sankey-previous").disabled = state.sankeyFrameIndex <= 0;
  $("#sankey-next").disabled = state.sankeyFrameIndex >= lastIndex;
  $("#sankey-live").disabled = state.sankeyFrameIndex >= lastIndex;
  const playButton = $("#sankey-play");
  playButton.textContent = state.sankeyPlaying ? "Pause" : "Play";
  playButton.setAttribute("aria-label", state.sankeyPlaying ? "Pause history" : "Play history");
  playButton.classList.toggle("is-playing", state.sankeyPlaying);
}

function stopSankeyPlayback() {
  state.sankeyPlaying = false;
  clearTimeout(state.sankeyPlaybackTimer);
  state.sankeyPlaybackTimer = null;
  updateSankeyPlaybackControls();
}

async function showSankeyFrame(index) {
  const boundedIndex = Math.max(0, Math.min(index, state.sankeyFrames.length - 1));
  const frame = state.sankeyFrames[boundedIndex];
  if (!frame) return;

  state.sankeyFrameIndex = boundedIndex;
  $("#sankey-snapshot-select").value = frame.live ? "" : String(frame.id);
  $("#sankey-view-note").textContent = frame.live
    ? "Current pipeline"
    : `${frame.reason.startsWith("Estimated replay") ? "Estimated historical view" : "Exact snapshot"} from ${new Date(frame.created_at).toLocaleString()}`;
  updateSankeyPlaybackControls();

  const requestSequence = ++state.sankeyRequestSequence;
  if (!frame.data) frame.data = await api(`/api/sankey/snapshots/${frame.id}`);
  if (requestSequence !== state.sankeyRequestSequence) return;
  renderSankey(frame.data);
}

function scheduleSankeyPlayback() {
  clearTimeout(state.sankeyPlaybackTimer);
  if (!state.sankeyPlaying) return;
  if (state.sankeyFrameIndex >= state.sankeyFrames.length - 1) {
    stopSankeyPlayback();
    return;
  }
  state.sankeyPlaybackTimer = setTimeout(async () => {
    await showSankeyFrame(state.sankeyFrameIndex + 1);
    scheduleSankeyPlayback();
  }, 1200);
}

async function startSankeyPlayback() {
  if (state.sankeyFrames.length <= 1) return;
  if (state.sankeyFrameIndex >= state.sankeyFrames.length - 1) {
    await showSankeyFrame(0);
  }
  state.sankeyPlaying = true;
  updateSankeyPlaybackControls();
  scheduleSankeyPlayback();
}

function renderSankey(data) {
  state.sankeyData = data;
  const container = $("#sankey-chart");
  if (!window.d3 || !d3.sankey || !data.links.length) {
    container.innerHTML = "";
    state.sankeyGraph = null;
    container.innerHTML = `<div class="empty-state">Application flow will appear after jobs are added.</div>`;
    return;
  }

  const width = Math.max(container.clientWidth, 760);
  const height = window.innerWidth <= 760 ? 330 : 390;
  const margin = { top: 14, right: 150, bottom: 14, left: 125 };
  const previousGraph = state.sankeyGraph;
  const graph = d3.sankey()
    .nodeWidth(16)
    .nodePadding(17)
    .nodeAlign((node, columns) => Math.min(sankeyDepth(node.name), columns - 1))
    .nodeSort((left, right) => sankeyOrder(left.name) - sankeyOrder(right.name))
    .linkSort((left, right) => sankeyOrder(left.target.name) - sankeyOrder(right.target.name))
    .extent([[margin.left, margin.top], [width - margin.right, height - margin.bottom]])({
      nodes: data.nodes.map(node => ({ ...node })),
      links: data.links.map(link => ({ ...link })),
    });

  d3.select(container).select(".empty-state").remove();
  let svg = d3.select(container).select("svg");
  if (svg.empty()) {
    svg = d3.select(container).append("svg");
    svg.append("g").attr("class", "sankey-links");
    svg.append("g").attr("class", "sankey-flow-layer");
    svg.append("g").attr("class", "sankey-nodes");
  }
  svg
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  let tooltip = document.querySelector(".sankey-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "sankey-tooltip";
    document.body.appendChild(tooltip);
  }

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const transition = svg.transition()
    .duration(reducedMotion ? 0 : 900)
    .ease(d3.easeCubicInOut);
  const linkPath = d3.sankeyLinkHorizontal();

  const links = svg.select(".sankey-links")
    .selectAll("path")
    .data(graph.links, sankeyLinkId);

  links.exit()
    .transition(transition)
    .attr("d", link => linkPath(collapsedLink(link, true)))
    .attr("stroke-width", 0)
    .style("opacity", 0)
    .remove();

  links.enter()
    .append("path")
    .attr("class", "sankey-link")
    .attr("data-link-id", sankeyLinkId)
    .attr("d", link => linkPath(collapsedLink(link)))
    .attr("stroke", link => sankeyColor(link.target.name))
    .attr("stroke-width", 0)
    .style("opacity", 0)
    .merge(links)
    .attr("data-link-id", sankeyLinkId)
    .on("mousemove", (event, link) => {
      tooltip.style.opacity = "1";
      tooltip.style.left = `${event.clientX}px`;
      tooltip.style.top = `${event.clientY}px`;
      tooltip.textContent = `${link.source.name} → ${link.target.name}: ${link.value}`;
    })
    .on("mouseleave", () => { tooltip.style.opacity = "0"; })
    .transition(transition)
    .attr("d", linkPath)
    .attr("stroke", link => sankeyColor(link.target.name))
    .attr("stroke-width", link => Math.max(1, link.width))
    .style("opacity", 1);

  const flowLinks = svg.select(".sankey-flow-layer")
    .selectAll("path")
    .data(graph.links, sankeyLinkId);

  flowLinks.exit()
    .transition(transition)
    .attr("d", link => linkPath(collapsedLink(link, true)))
    .style("opacity", 0)
    .remove();

  flowLinks.enter()
    .append("path")
    .attr("class", "sankey-flow-motion")
    .attr("data-link-id", sankeyLinkId)
    .attr("pathLength", 100)
    .attr("d", link => linkPath(collapsedLink(link)))
    .attr("stroke", link => sankeyColor(link.target.name))
    .style("opacity", 0)
    .merge(flowLinks)
    .attr("data-link-id", sankeyLinkId)
    .transition(transition)
    .attr("d", linkPath)
    .attr("stroke", link => sankeyColor(link.target.name))
    .style("opacity", reducedMotion ? 0 : 0.7);

  const nodes = svg.select(".sankey-nodes")
    .selectAll("g")
    .data(graph.nodes, node => node.name);

  const exitingNodes = nodes.exit();
  exitingNodes.each(function(node) {
    const collapsed = exitingNodeGeometry(node, graph);
    const selection = d3.select(this);
    selection.select("rect")
      .transition(transition)
      .attr("x", collapsed.x0)
      .attr("y", collapsed.y0)
      .attr("width", Math.max(1, collapsed.x1 - collapsed.x0))
      .attr("height", 0);
    selection.selectAll("text")
      .transition(transition)
      .attr("x", collapsed.x0)
      .attr("y", collapsed.y0)
      .style("opacity", 0);
  });
  exitingNodes.transition(transition).style("opacity", 0).remove();

  const enteringNodes = nodes.enter()
    .append("g")
    .attr("class", "sankey-node")
    .attr("data-node-name", node => node.name)
    .style("opacity", 0);

  enteringNodes.append("rect")
    .attr("rx", 3)
    .each(function(node) {
      const initial = enteringNodeGeometry(node, previousGraph);
      d3.select(this)
        .attr("x", initial.x0)
        .attr("y", initial.y0)
        .attr("height", Math.max(0, initial.y1 - initial.y0))
        .attr("width", Math.max(1, initial.x1 - initial.x0))
        .attr("fill", sankeyColor(node.name));
    });

  enteringNodes.append("text");
  enteringNodes.append("text").attr("class", "node-count");

  const mergedNodes = enteringNodes.merge(nodes)
    .attr("data-node-name", node => node.name)
    .on("mousemove", (event, node) => {
      tooltip.style.opacity = "1";
      tooltip.style.left = `${event.clientX}px`;
      tooltip.style.top = `${event.clientY}px`;
      tooltip.textContent = `${node.name}: ${node.value}`;
    })
    .on("mouseleave", () => { tooltip.style.opacity = "0"; });

  mergedNodes.transition(transition).style("opacity", 1);

  mergedNodes.select("rect")
    .transition(transition)
    .attr("x", node => node.x0)
    .attr("y", node => node.y0)
    .attr("height", node => Math.max(2, node.y1 - node.y0))
    .attr("width", node => node.x1 - node.x0)
    .attr("fill", node => sankeyColor(node.name));

  mergedNodes.select("text:not(.node-count)")
    .text(node => node.name)
    .transition(transition)
    .attr("x", node => node.x0 < width / 2 ? node.x1 + 8 : node.x0 - 8)
    .attr("y", node => (node.y0 + node.y1) / 2 - 2)
    .attr("text-anchor", node => node.x0 < width / 2 ? "start" : "end")
    .style("opacity", 1);

  mergedNodes.select(".node-count")
    .text(node => `${node.value} ${node.value === 1 ? "role" : "roles"}`)
    .transition(transition)
    .attr("x", node => node.x0 < width / 2 ? node.x1 + 8 : node.x0 - 8)
    .attr("y", node => (node.y0 + node.y1) / 2 + 12)
    .attr("text-anchor", node => node.x0 < width / 2 ? "start" : "end")
    .style("opacity", 1);

  state.sankeyGraph = graph;
}

function renderJobs() {
  $("#result-count").textContent = `${state.jobs.length} ${state.jobs.length === 1 ? "job" : "jobs"}`;
  $("#empty-state").hidden = state.jobs.length !== 0;
  const hasFilters = Boolean(
    $("#search-input")?.value.trim()
    || $("#status-filter")?.value
    || $("#tier-filter")?.value
    || ($("#archive-filter")?.value || "active") !== "active"
  );
  $("#empty-state-title").textContent = hasFilters ? "No jobs match these filters." : "Start your private job-search workspace.";
  $("#empty-state-copy").textContent = hasFilters
    ? "Adjust the filters or add a new opportunity."
    : "Add your first verified role here, or ask Copilot to load fictional demo data through the local tracker MCP server.";
  $("#jobs-table").innerHTML = state.jobs.map(job => `
    <tr data-job-id="${job.id}">
      <td>
        <span class="company-name">${escapeHtml(job.company)}</span>
        <span class="role-name">${escapeHtml(job.role)}</span>
        <span class="job-meta">${escapeHtml(job.location || "")}</span>
        <span class="job-meta">${freshnessChip(job)}${job.first_published_date ? ` First published ${displayDate(job.first_published_date)}` : ""}</span>
        ${job.url ? `<a class="job-link" href="${escapeHtml(job.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Open job ↗</a>` : ""}
      </td>
      <td>${statusChip(job.status)}${job.applied_date ? `<span class="job-meta">Applied ${displayDate(job.applied_date)}</span>` : ""}</td>
      <td>${tierChip(job.recommendation_tier)}</td>
      <td>
        <span class="next-action ${job.follow_up_due ? "due" : ""}">${escapeHtml(job.next_action || "No action set")}</span>
        <span class="job-meta">${job.next_action_date ? displayDate(job.next_action_date) : ""}</span>
      </td>
      <td><button class="edit-button" data-edit-id="${job.id}">Edit</button></td>
    </tr>
  `).join("");

  $("#mobile-job-list").innerHTML = state.jobs.map(job => `
    <article class="mobile-job-card" data-job-id="${job.id}">
      <div class="card-row"><div><span class="company-name">${escapeHtml(job.company)}</span><span class="role-name">${escapeHtml(job.role)}</span></div>${statusChip(job.status)}</div>
      <div class="job-meta">${escapeHtml(job.location || "")}</div>
      <div style="margin-top:10px">${tierChip(job.recommendation_tier)} ${freshnessChip(job)}</div>
      <span class="next-action ${job.follow_up_due ? "due" : ""}">${escapeHtml(job.next_action || "No action set")}</span>
    </article>
  `).join("");
}

function renderHistory(items) {
  $("#activity-list").innerHTML = items.length ? items.map(item => `
    <article class="activity-item">
      <strong>${escapeHtml(item.company)}</strong>
      <p>${escapeHtml(item.old_status ? `${item.old_status} → ` : "")}${escapeHtml(item.new_status)}${item.note ? ` · ${escapeHtml(item.note)}` : ""}</p>
      <time>${new Date(item.created_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</time>
    </article>
  `).join("") : `<div class="empty-state">No activity yet.</div>`;
}

function fieldValue(id) { return $(`#${id}`).value; }
function setField(id, value) { $(`#${id}`).value = value || ""; }

function updateNotFitRequirements() {
  const required = fieldValue("status") === "Not a Fit";
  $("#not-fit-category").required = required;
  $("#decision").required = required;
}

function openDialog(job = null) {
  state.editingJob = job;
  $("#job-form").reset();
  $("#form-message").textContent = "";
  $("#dialog-title").textContent = job ? "Edit job" : "Add job";
  $("#delete-job").hidden = !job;
  $("#job-id").value = job?.id || "";
  setField("company", job?.company);
  setField("role", job?.role);
  setField("status", job?.status || "Researching");
  setField("stage", job?.stage);
  setField("recommendation-tier", job?.recommendation_tier || "Monitor");
  setField("recommendation-rank", job?.recommendation_rank);
  setField("url", job?.url);
  setField("location", job?.location);
  setField("compensation", job?.compensation);
  setField("applied-date", job?.applied_date);
  setField("next-action-date", job?.next_action_date);
  setField("first-published-date", job?.first_published_date);
  setField("posting-updated-date", job?.posting_updated_date);
  setField("linkedin-reposted-date", job?.linkedin_reposted_date);
  setField("last-verified-date", job?.last_verified_date);
  setField("freshness-source", job?.freshness_source);
  setField("freshness-confidence", job?.freshness_confidence);
  setField("fit-summary", job?.fit_summary);
  setField("not-fit-category", job?.not_fit_category);
  setField("decision", job?.decision);
  setField("next-action", job?.next_action);
  setField("on-call", job?.on_call);
  setField("risk", job?.risk);
  setField("notes", job?.notes);
  $("#archived").checked = Boolean(job?.archived);
  setField("status-note", "");
  updateNotFitRequirements();
  $("#job-dialog").showModal();
}

function closeDialog() { $("#job-dialog").close(); }

function formPayload() {
  return {
    company: fieldValue("company"),
    role: fieldValue("role"),
    status: fieldValue("status"),
    stage: fieldValue("stage"),
    recommendation_tier: fieldValue("recommendation-tier"),
    recommendation_rank: fieldValue("recommendation-rank"),
    url: fieldValue("url"),
    location: fieldValue("location"),
    compensation: fieldValue("compensation"),
    applied_date: fieldValue("applied-date"),
    next_action_date: fieldValue("next-action-date"),
    first_published_date: fieldValue("first-published-date"),
    posting_updated_date: fieldValue("posting-updated-date"),
    linkedin_reposted_date: fieldValue("linkedin-reposted-date"),
    last_verified_date: fieldValue("last-verified-date"),
    freshness_source: fieldValue("freshness-source"),
    freshness_confidence: fieldValue("freshness-confidence"),
    fit_summary: fieldValue("fit-summary"),
    not_fit_category: fieldValue("not-fit-category"),
    decision: fieldValue("decision"),
    next_action: fieldValue("next-action"),
    on_call: fieldValue("on-call"),
    risk: fieldValue("risk"),
    notes: fieldValue("notes"),
    archived: $("#archived").checked,
    status_note: fieldValue("status-note"),
  };
}

async function refreshDashboard() {
  const [stats, recommendations, history, sankey, sankeySnapshots, workspace] = await Promise.all([
    api("/api/stats"),
    api("/api/recommendations"),
    api("/api/history"),
    api("/api/sankey"),
    api("/api/sankey/snapshots"),
    api("/api/workspace"),
  ]);
  await loadJobs();
  renderStats(stats);
  renderFreshness(stats.freshness_conversion);
  renderRecommendations(recommendations);
  renderWorkspace(workspace);
  renderHistory(history);
  renderSankeyHistory(sankeySnapshots, sankey);
  renderSankey(sankey);
}

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.sankeyData) renderSankey(state.sankeyData);
  }, 180);
});

$("#sankey-snapshot-select").addEventListener("change", async event => {
  stopSankeyPlayback();
  const snapshotId = event.target.value;
  const frameIndex = snapshotId
    ? state.sankeyFrames.findIndex(frame => String(frame.id) === snapshotId)
    : state.sankeyFrames.length - 1;
  await showSankeyFrame(frameIndex);
});

$("#sankey-rewind").addEventListener("click", async () => {
  stopSankeyPlayback();
  await showSankeyFrame(0);
});

$("#sankey-previous").addEventListener("click", async () => {
  stopSankeyPlayback();
  await showSankeyFrame(state.sankeyFrameIndex - 1);
});

$("#sankey-play").addEventListener("click", async () => {
  if (state.sankeyPlaying) {
    stopSankeyPlayback();
    return;
  }
  await startSankeyPlayback();
});

$("#sankey-next").addEventListener("click", async () => {
  stopSankeyPlayback();
  await showSankeyFrame(state.sankeyFrameIndex + 1);
});

$("#sankey-live").addEventListener("click", async () => {
  stopSankeyPlayback();
  await showSankeyFrame(state.sankeyFrames.length - 1);
});

$("#sankey-timeline-range").addEventListener("input", async event => {
  const frameIndex = Number(event.target.value);
  stopSankeyPlayback();
  await showSankeyFrame(frameIndex);
});

$("#job-form").addEventListener("submit", async event => {
  event.preventDefault();
  $("#form-message").textContent = "";
  try {
    const id = $("#job-id").value;
    await api(id ? `/api/jobs/${id}` : "/api/jobs", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(formPayload()),
    });
    closeDialog();
    await refreshDashboard();
  } catch (error) {
    $("#form-message").textContent = error.message;
  }
});

$("#delete-job").addEventListener("click", async () => {
  if (!state.editingJob || !confirm(`Delete ${state.editingJob.company} - ${state.editingJob.role}?`)) return;
  await api(`/api/jobs/${state.editingJob.id}`, { method: "DELETE" });
  closeDialog();
  await refreshDashboard();
});

$("#add-job-button").addEventListener("click", () => openDialog());
$("#empty-add-job").addEventListener("click", () => openDialog());
$("#close-dialog").addEventListener("click", closeDialog);
$("#cancel-dialog").addEventListener("click", closeDialog);
$("#search-input").addEventListener("input", () => loadJobs());
$("#status-filter").addEventListener("change", () => loadJobs());
$("#tier-filter").addEventListener("change", () => loadJobs());
$("#archive-filter").addEventListener("change", () => loadJobs());
$("#status").addEventListener("change", updateNotFitRequirements);
$("#copy-onboarding-prompt").addEventListener("click", async () => {
  const confirmation = $("#copy-confirmation");
  try {
    await navigator.clipboard.writeText(onboardingPrompt);
    confirmation.textContent = "Interview prompt copied.";
  } catch {
    confirmation.textContent = `Copy this prompt: ${onboardingPrompt}`;
  }
});

document.addEventListener("click", event => {
  const edit = event.target.closest("[data-edit-id]");
  const card = event.target.closest("[data-job-id]");
  const id = Number(edit?.dataset.editId || card?.dataset.jobId);
  if (id) openDialog(state.jobIndex.get(id) || null);
});

$("#today-label").textContent = new Date().toLocaleDateString(undefined, {
  weekday: "long", month: "long", day: "numeric", year: "numeric"
});

loadAll().then(renderJobs).catch(error => {
  console.error(error);
  $("#jobs-table").innerHTML = `<tr><td colspan="5">Unable to load dashboard: ${error.message}</td></tr>`;
});
