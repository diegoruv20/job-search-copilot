const state = {
  jobs: [],
  jobIndex: new Map(),
  meta: { statuses: [], tiers: [] },
  editingJob: null,
  sankeyData: null,
  sankeyTimeline: { daily: [], highlights: [], all_activity: [] },
  sankeyTimelineMode: "daily",
  sankeyPlaybackSpeed: 1,
  sankeyLiveData: null,
  sankeyFrames: [],
  sankeyFrameIndex: 0,
  sankeyGraph: null,
  sankeyPlaybackTimer: null,
  sankeyPlaying: false,
  sankeyRequestSequence: 0,
  dashboardRevision: null,
  dashboardPendingRevision: null,
  dashboardRefreshPromise: null,
  dashboardRevisionCheckPromise: null,
  workflow: "new",
  jobPage: 1,
  visibleJobFilters: new Set(),
};

const DASHBOARD_REFRESH_INTERVAL_MS = 5000;
const JOBS_PAGE_SIZE = 10;
const workflowViews = {
  new: {
    title: "New opportunities",
    note: "Unapplied active roles, freshest first",
    archive: "active",
    sort: "freshest",
  },
  applications: {
    title: "My applications",
    note: "Submitted roles and outcomes, ordered by the next action",
    archive: "all",
    sort: "default",
  },
  pursuits: {
    title: "Current pursuits",
    note: "Confirmed recruiter conversations and active interview stages",
    archive: "active",
    sort: "default",
  },
  all: {
    title: "All jobs",
    note: "Every tracked role with full filtering and sorting",
    archive: "all",
    sort: "default",
  },
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

function sortJobs(jobs) {
  const mode = $("#jobs-sort")?.value || "default";
  if (mode === "default") return jobs;
  const direction = mode === "freshest" ? -1 : 1;
  return [...jobs].sort((left, right) => {
    if (!left.first_published_date && !right.first_published_date) return 0;
    if (!left.first_published_date) return 1;
    if (!right.first_published_date) return -1;
    return left.first_published_date.localeCompare(right.first_published_date) * direction;
  });
}

async function loadAll() {
  const [meta, stats, recommendations, jobs, history, sankey, sankeyTimeline, workspace, revision] = await Promise.all([
    api("/api/meta"),
    api("/api/stats"),
    api("/api/recommendations"),
    loadJobs(false),
    api("/api/history"),
    api("/api/sankey"),
    api("/api/sankey/timeline"),
    api("/api/workspace"),
    api("/api/revision"),
  ]);
  state.meta = meta;
  state.dashboardRevision = revision.revision;
  renderSelects();
  renderStats(stats);
  renderFreshness(stats.freshness_conversion);
  renderRecommendations(recommendations);
  renderWorkspace(workspace);
  renderHistory(history);
  renderSankeyHistory(sankeyTimeline, sankey);
  renderSankey(sankey);
  return jobs;
}

async function loadJobs(render = true) {
  const params = new URLSearchParams();
  const q = $("#search-input")?.value.trim();
  const status = $("#status-filter")?.value;
  const tier = $("#tier-filter")?.value;
  const archive = $("#archive-filter")?.value || "active";
  const sort = $("#jobs-sort")?.value || "default";
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (tier) params.set("tier", tier);
  params.set("archive", archive);
  params.set("workflow", state.workflow);
  params.set("sort", sort);
  state.jobs = sortJobs(await api(`/api/jobs?${params}`));
  state.jobIndex.clear();
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
      <div class="recommendation-actions">
        ${job.url
          ? `<a class="button button-primary recommendation-link" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer" data-job-link aria-label="View and apply to ${escapeHtml(job.role)} at ${escapeHtml(job.company)} in a new tab">View &amp; apply <span aria-hidden="true">↗</span></a>`
          : `<span class="recommendation-link-unavailable">Posting link unavailable</span>`}
        ${job.resume_url
          ? `<a class="recommendation-link resume-link" href="${escapeHtml(job.resume_url)}" target="_blank" rel="noopener noreferrer" data-job-link aria-label="Open prepared resume for ${escapeHtml(job.role)} at ${escapeHtml(job.company)} in a new tab">Open resume <span aria-hidden="true">↗</span></a>`
          : ""}
      </div>
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
  if ([
    "Initial screen",
    "Active initial screen",
    "Technical interview",
    "Active technical interview",
    "Final / onsite",
    "Final interview active",
    "Advanced to interviews",
    "Active interviewing",
    "Final interview",
  ].includes(name)) return "#35d39a";
  if (["Applied", "Resume review", "No response yet"].includes(name)) return "#4ea5ff";
  if (["Not applied", "Ready to apply", "Referral prep", "Preparing", "Researching / preparing", "On hold"].includes(name)) return "#8b7cf6";
  return "#64748b";
}

const sankeyNodeOrder = new Map([
  ["Tracked roles", 0],
  ["Applied", 10],
  ["Resume review", 20],
  ["Initial screen", 30],
  ["Advanced to interviews", 31],
  ["No response yet", 40],
  ["Rejected at resume review", 50],
  ["Withdrawn", 55],
  ["Technical interview", 60],
  ["Active initial screen", 70],
  ["Active technical interview", 71],
  ["Active interviewing", 72],
  ["Rejected during interviews", 80],
  ["Final / onsite", 85],
  ["Final interview", 86],
  ["Offer", 90],
  ["Final interview active", 100],
  ["Rejected after final interview", 110],
  ["Not applied", 130],
  ["Ready to apply", 140],
  ["Referral prep", 150],
  ["Preparing", 160],
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
  if (["Resume review", "Ready to apply", "Referral prep", "Preparing", "Researching / preparing", "On hold", "Not a fit"].includes(name)) return 2;
  if (["No response yet", "Rejected at resume review", "Initial screen", "Advanced to interviews", "Withdrawn"].includes(name)) return 3;
  if (["Active initial screen", "Technical interview", "Active interviewing", "Rejected during interviews"].includes(name)) return 4;
  if (["Active technical interview", "Final / onsite", "Final interview"].includes(name)) return 5;
  if (["Final interview active", "Rejected after final interview", "Offer"].includes(name)) return 6;
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

function measureSankeyText(text, font) {
  const canvas = measureSankeyText.canvas || document.createElement("canvas");
  measureSankeyText.canvas = canvas;
  const context = canvas.getContext("2d");
  context.font = font;
  return context.measureText(text).width;
}

function sankeyLayoutMetrics(data, isNarrow) {
  const nodeWidth = 18;
  const labelOffset = 8;
  const stageBuffer = isNarrow ? 20 : 18;
  const edgePadding = isNarrow ? 24 : 18;
  const labelFont = "600 12px Inter, sans-serif";
  const countFont = "500 10px Inter, sans-serif";
  const continuingNodeNames = new Set(data.links.map(link => {
    const source = link.source;
    if (typeof source === "object") return source.name;
    if (Number.isInteger(source)) return data.nodes[source]?.name;
    return source;
  }));
  const labelWidths = new Map();
  const continuingLabelWidths = new Map();
  let maxDepth = 0;

  data.nodes.forEach(node => {
    const depth = sankeyDepth(node.name);
    const countLabel = `${node.value ?? 999} roles`;
    const labelWidth = Math.ceil(Math.max(
      measureSankeyText(node.name, labelFont),
      measureSankeyText(countLabel, countFont),
    )) + 8;
    labelWidths.set(node.name, labelWidth);
    if (continuingNodeNames.has(node.name) || depth < 3) {
      continuingLabelWidths.set(
        depth,
        Math.max(continuingLabelWidths.get(depth) || 0, labelWidth),
      );
    }
    maxDepth = Math.max(maxDepth, depth);
  });

  const stageOffsets = new Map([[0, 0]]);
  for (let depth = 1; depth <= maxDepth; depth += 1) {
    const previousOffset = stageOffsets.get(depth - 1);
    const previousLabelWidth = continuingLabelWidths.get(depth - 1) || 0;
    stageOffsets.set(
      depth,
      previousOffset + nodeWidth + labelOffset + previousLabelWidth + stageBuffer,
    );
  }

  const contentWidth = Math.max(...data.nodes.map(node => (
    stageOffsets.get(sankeyDepth(node.name))
    + nodeWidth
    + labelOffset
    + labelWidths.get(node.name)
  )));
  return {
    contentWidth,
    edgePadding,
    labelOffset,
    maxDepth,
    minimumWidth: Math.ceil(contentWidth + edgePadding * 2),
    nodeWidth,
    stageOffsets,
  };
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

function compactFrameDate(value, includeTime = true) {
  const options = { month: "short", day: "numeric" };
  if (includeTime) {
    options.hour = "numeric";
    options.minute = "2-digit";
  }
  return new Date(value).toLocaleString(undefined, options);
}

function compactFrameSubject(frame) {
  if (frame.empty_state) return "Empty";
  if (frame.reason.startsWith("Estimated replay")) return "Daily snapshot";
  if (frame.reason === "History tracking started") return "History started";
  const added = frame.reason.match(/^Added ([^—]+?)(?:\s+—|$)/);
  if (added) return added[1].trim();
  const changed = frame.reason.match(/^([^:]+):/);
  if (changed) return changed[1].trim();
  return frame.reason.length > 24 ? `${frame.reason.slice(0, 23)}…` : frame.reason;
}

function frameLabel(frame, index) {
  if (frame.live) return "Live view";
  if (frame.empty_state) return `Start · ${compactFrameDate(frame.created_at, false)}`;
  const grouped = frame.grouped_count > 1 ? ` · ${frame.grouped_count} updates grouped` : "";
  return `Frame ${index + 1} · ${compactFrameDate(frame.created_at, false)}${grouped}`;
}

function rebuildSankeyFrames(mode = state.sankeyTimelineMode) {
  state.sankeyRequestSequence += 1;
  state.sankeyTimelineMode = mode;
  const snapshots = state.sankeyTimeline[mode] || [];
  state.sankeyFrames = [
    ...snapshots.map(snapshot => ({
      ...snapshot,
      live: false,
      data: snapshot.data || null,
    })),
    { id: "", live: true, reason: "Live view", created_at: new Date().toISOString(), grouped_count: 1, data: state.sankeyLiveData },
  ];
  $("#sankey-timeline-mode").value = mode;
  const snapshotOptions = snapshots.map((snapshot, index) => {
    const grouped = snapshot.grouped_count > 1 ? ` · ${snapshot.grouped_count} grouped` : "";
    const label = `${index + 1} · ${compactFrameDate(snapshot.created_at, !snapshot.empty_state)} · ${compactFrameSubject(snapshot)}${grouped}`;
    const title = `${new Date(snapshot.created_at).toLocaleString()} — ${snapshot.reason}`;
    return `<option value="${snapshot.id}" title="${escapeHtml(title)}">${escapeHtml(label)}</option>`;
  }).reverse();
  $("#sankey-snapshot-select").innerHTML = [
    `<option value="">Live view</option>`,
    ...snapshotOptions,
  ].join("");
  const range = $("#sankey-timeline-range");
  range.max = String(Math.max(0, state.sankeyFrames.length - 1));
  const firstHistorical = state.sankeyFrames.find(frame => !frame.live);
  $("#sankey-timeline-start").textContent = firstHistorical
    ? new Date(firstHistorical.created_at).toLocaleDateString()
    : "First snapshot";
}

function renderSankeyHistory(timeline, liveData) {
  state.sankeyTimeline = timeline;
  state.sankeyLiveData = liveData;
  rebuildSankeyFrames();
  state.sankeyFrameIndex = state.sankeyFrames.length - 1;
  $("#sankey-view-note").textContent = "Current pipeline";
  updateSankeyPlaybackControls();
}

function updateSankeyPlaybackControls() {
  const lastIndex = state.sankeyFrames.length - 1;
  const currentFrame = state.sankeyFrames[state.sankeyFrameIndex];
  $("#sankey-timeline-range").value = String(state.sankeyFrameIndex);
  $("#sankey-timeline-label").textContent = currentFrame
    ? frameLabel(currentFrame, state.sankeyFrameIndex)
    : "Live view";
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
  const snapshotSelect = $("#sankey-snapshot-select");
  snapshotSelect.value = frame.live ? "" : String(frame.id);
  snapshotSelect.title = frame.live
    ? "Live view"
    : `${new Date(frame.created_at).toLocaleString()} — ${frame.reason}`;
  $("#sankey-view-note").textContent = frame.live
    ? "Current pipeline"
    : frame.empty_state
      ? `Empty starting state from ${new Date(frame.created_at).toLocaleDateString()}`
    : `${frame.reason.startsWith("Estimated replay") ? "Estimated historical view" : "Exact snapshot"} from ${new Date(frame.created_at).toLocaleString()}${frame.grouped_count > 1 ? ` · ${frame.grouped_count} updates grouped into this highlight` : ""}`;
  updateSankeyPlaybackControls();

  const requestSequence = ++state.sankeyRequestSequence;
  if (!frame.data) frame.data = await api(`/api/sankey/snapshots/${frame.id}/view`);
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
  const current = state.sankeyFrames[state.sankeyFrameIndex];
  const next = state.sankeyFrames[state.sankeyFrameIndex + 1];
  state.sankeyPlaybackTimer = setTimeout(async () => {
    await showSankeyFrame(state.sankeyFrameIndex + 1);
    scheduleSankeyPlayback();
  }, sankeyPlaybackDelay(current, next));
}

function sankeyPlaybackDelay(current, next) {
  const speed = Math.max(1, state.sankeyPlaybackSpeed);
  if (!current || !next) return 1100 / speed;
  const currentDate = new Date(current.created_at);
  const nextDate = new Date(next.created_at);
  currentDate.setHours(0, 0, 0, 0);
  nextDate.setHours(0, 0, 0, 0);
  const gapDays = Math.max(0, Math.round((nextDate - currentDate) / 86400000));
  if (gapDays === 0) return 1100 / speed;
  if (gapDays === 1) return 1500 / speed;
  return 1900 / speed;
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
  const scrollHint = $("#sankey-scroll-hint");
  if (!window.d3 || !d3.sankey || !data.links.length) {
    const currentFrame = state.sankeyFrames[state.sankeyFrameIndex];
    const message = currentFrame?.empty_state
      ? "Timeline starts empty so the first update can build the application flow."
      : "Application flow will appear after jobs are added.";
    container.innerHTML = "";
    container.classList.remove("is-scrollable");
    scrollHint.hidden = true;
    state.sankeyGraph = null;
    container.innerHTML = `<div class="empty-state">${message}</div>`;
    return;
  }

  const availableWidth = container.clientWidth;
  const isMobile = window.innerWidth <= 760;
  const isNarrow = availableWidth < 980;
  const layout = sankeyLayoutMetrics(data, isNarrow);
  const minimumWidth = layout.minimumWidth;
  const width = Math.max(availableWidth, minimumWidth);
  const height = isNarrow ? 600 : 460;
  const margin = isMobile || isNarrow
    ? { top: 20, bottom: 20 }
    : { top: 14, bottom: 14 };
  const fillsAvailableWidth = layout.maxDepth > 0;
  const targetLayoutWidth = fillsAvailableWidth ? width : minimumWidth;
  const extraStageGap = layout.maxDepth > 0
    ? (targetLayoutWidth - minimumWidth) / layout.maxDepth
    : 0;
  const horizontalOffset = (
    layout.edgePadding
    + Math.max(0, (width - targetLayoutWidth) / 2)
  );
  const isScrollable = width > availableWidth + 1;
  container.classList.toggle("is-scrollable", isScrollable);
  scrollHint.hidden = !isScrollable;
  const previousGraph = state.sankeyGraph;
  const graph = d3.sankey()
    .nodeWidth(layout.nodeWidth)
    .nodePadding(isNarrow ? 22 : 17)
    .nodeAlign((node, columns) => Math.min(sankeyDepth(node.name), columns - 1))
    .nodeSort((left, right) => sankeyOrder(left.name) - sankeyOrder(right.name))
    .linkSort((left, right) => sankeyOrder(left.target.name) - sankeyOrder(right.target.name))
    .extent([[horizontalOffset, margin.top], [width - horizontalOffset, height - margin.bottom]])({
      nodes: data.nodes.map(node => ({ ...node })),
      links: data.links.map(link => ({ ...link })),
    });
  graph.nodes.forEach(node => {
    const depth = sankeyDepth(node.name);
    node.x0 = (
      horizontalOffset
      + layout.stageOffsets.get(depth)
      + depth * extraStageGap
    );
    node.x1 = node.x0 + layout.nodeWidth;
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
    .attr("preserveAspectRatio", "xMidYMid meet")
    .style("min-width", `${width}px`)
    .style("height", `${height}px`);

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
    .attr("x", node => node.x1 + layout.labelOffset)
    .attr("y", node => (node.y0 + node.y1) / 2 - 2)
    .attr("text-anchor", "start")
    .style("opacity", 1);

  mergedNodes.select(".node-count")
    .text(node => `${node.value} ${node.value === 1 ? "role" : "roles"}`)
    .transition(transition)
    .attr("x", node => node.x1 + layout.labelOffset)
    .attr("y", node => (node.y0 + node.y1) / 2 + 12)
    .attr("text-anchor", "start")
    .style("opacity", 1);

  state.sankeyGraph = graph;
}

function renderJobs() {
  const jobCount = state.jobs.length;
  const pageCount = Math.max(1, Math.ceil(jobCount / JOBS_PAGE_SIZE));
  state.jobPage = Math.min(Math.max(1, state.jobPage), pageCount);
  const pageStart = (state.jobPage - 1) * JOBS_PAGE_SIZE;
  const pageJobs = state.jobs.slice(pageStart, pageStart + JOBS_PAGE_SIZE);
  const pageEnd = Math.min(jobCount, pageStart + pageJobs.length);
  $("#result-count").textContent = jobCount
    ? `${pageStart + 1}-${pageEnd} of ${jobCount} jobs`
    : "0 jobs";
  $("#empty-state").hidden = jobCount !== 0;
  const hasFilters = Boolean(
    $("#search-input")?.value.trim()
    || $("#status-filter")?.value
    || $("#tier-filter")?.value
  );
  const emptyCopy = {
    new: [
      "No new opportunities yet.",
      "Add a verified opportunity, or switch to All jobs to review roles already classified.",
    ],
    applications: [
      "No applications yet.",
      "When a role is recorded as applied, it will appear here with its next action and outcome.",
    ],
    pursuits: [
      "No current pursuits yet.",
      "Confirmed recruiter conversations and active interview stages will appear here automatically.",
    ],
    all: [
      "Start your private job-search workspace.",
      "Add your first verified role here, or ask Copilot to load fictional demo data through the local tracker MCP server.",
    ],
  }[state.workflow];
  $("#empty-state-title").textContent = hasFilters ? "No jobs match these filters." : emptyCopy[0];
  $("#empty-state-copy").textContent = hasFilters
    ? "Clear advanced filters or choose another workflow view."
    : emptyCopy[1];
  $("#empty-add-job").textContent = ["applications", "pursuits"].includes(state.workflow)
    ? "Add a job"
    : "Add an opportunity";
  $("#jobs-table").innerHTML = pageJobs.map(job => `
    <tr data-job-id="${job.id}">
      <td>
        <span class="company-name">${escapeHtml(job.company)}</span>
        <span class="role-name">${escapeHtml(job.role)}</span>
        <span class="job-meta">${escapeHtml(job.location || "")}</span>
        <span class="job-meta">${freshnessChip(job)}${job.first_published_date ? ` First published ${displayDate(job.first_published_date)}` : ""}</span>
        <span class="job-resource-links">
          ${job.url ? `<a class="job-link" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer" data-job-link>Open job ↗</a>` : ""}
          ${job.resume_url ? `<a class="job-link resume-link" href="${escapeHtml(job.resume_url)}" target="_blank" rel="noopener noreferrer" data-job-link>Open resume ↗</a>` : ""}
        </span>
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

  $("#mobile-job-list").innerHTML = pageJobs.map(job => `
    <article class="mobile-job-card" data-job-id="${job.id}">
      <div class="card-row"><div><span class="company-name">${escapeHtml(job.company)}</span><span class="role-name">${escapeHtml(job.role)}</span></div>${statusChip(job.status)}</div>
      <div class="job-meta">${escapeHtml(job.location || "")}</div>
      <div style="margin-top:10px">${tierChip(job.recommendation_tier)} ${freshnessChip(job)}</div>
      <span class="next-action ${job.follow_up_due ? "due" : ""}">${escapeHtml(job.next_action || "No action set")}</span>
      <span class="job-meta">${job.next_action_date ? displayDate(job.next_action_date) : ""}</span>
      <span class="job-resource-links">
        ${job.url ? `<a class="job-link" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer" data-job-link>Open job ↗</a>` : ""}
        ${job.resume_url ? `<a class="job-link resume-link" href="${escapeHtml(job.resume_url)}" target="_blank" rel="noopener noreferrer" data-job-link>Open resume ↗</a>` : ""}
      </span>
    </article>
  `).join("");
  renderJobPagination(jobCount, pageCount);
  renderActiveFilters();
}

function renderJobPagination(jobCount, pageCount) {
  const pagination = $("#jobs-pagination");
  pagination.hidden = jobCount <= JOBS_PAGE_SIZE;
  $("#jobs-page-status").textContent = `Page ${state.jobPage} of ${pageCount}`;
  $("#jobs-page-previous").disabled = state.jobPage <= 1;
  $("#jobs-page-next").disabled = state.jobPage >= pageCount;
}

function currentFilterState() {
  const view = workflowViews[state.workflow] || workflowViews.new;
  return [
    { key: "search", label: "Search", value: $("#search-input")?.value.trim() || "", defaultValue: "" },
    { key: "status", label: "Status", value: $("#status-filter")?.value || "", defaultValue: "" },
    { key: "tier", label: "Recommendation", value: $("#tier-filter")?.value || "", defaultValue: "" },
    { key: "archive", label: "Visibility", value: $("#archive-filter")?.value || "active", defaultValue: view.archive },
    { key: "sort", label: "Sort", value: $("#jobs-sort")?.value || "default", defaultValue: view.sort },
  ].filter(filter => filter.value !== filter.defaultValue);
}

function renderActiveFilters() {
  const filters = currentFilterState();
  const container = $("#active-filters");
  filters.forEach(filter => state.visibleJobFilters.add(filter.key));
  $("#clear-filters").disabled = filters.length === 0 && state.visibleJobFilters.size === 0;
  document.querySelectorAll("[data-filter-control]").forEach(control => {
    control.hidden = !state.visibleJobFilters.has(control.dataset.filterControl);
  });
  document.querySelectorAll("[data-add-filter]").forEach(button => {
    button.hidden = state.visibleJobFilters.has(button.dataset.addFilter);
  });
  $("#add-filter-menu").hidden = state.visibleJobFilters.size === 4;
  container.textContent = filters.length
    ? `${filters.length} customized filter${filters.length === 1 ? "" : "s"} applied.`
    : `Using ${workflowViews[state.workflow].title} defaults.`;
}

function activateWorkflow(workflow, applyDefaults = true) {
  const view = workflowViews[workflow] || workflowViews.new;
  state.workflow = workflowViews[workflow] ? workflow : "new";
  document.querySelectorAll("[data-workflow]").forEach(button => {
    const active = button.dataset.workflow === state.workflow;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $("#jobs-view-title").textContent = view.title;
  $("#jobs-view-note").textContent = view.note;
  if (applyDefaults) {
    $("#archive-filter").value = view.archive;
    $("#jobs-sort").value = view.sort;
  }
}

function clearAdvancedFilters() {
  $("#search-input").value = "";
  $("#status-filter").value = "";
  $("#tier-filter").value = "";
  state.visibleJobFilters.clear();
  state.jobPage = 1;
  activateWorkflow(state.workflow);
  return loadJobs();
}

function clearFilter(key) {
  const view = workflowViews[state.workflow] || workflowViews.new;
  if (key === "search") $("#search-input").value = "";
  if (key === "status") $("#status-filter").value = "";
  if (key === "tier") $("#tier-filter").value = "";
  if (key === "archive") $("#archive-filter").value = view.archive;
  if (key === "sort") $("#jobs-sort").value = view.sort;
  state.visibleJobFilters.delete(key);
  state.jobPage = 1;
  return loadJobs();
}

function addFilter(key) {
  const control = document.querySelector(`[data-filter-control="${key}"]`);
  if (!control) return;
  state.visibleJobFilters.add(key);
  $("#add-filter-menu").open = false;
  renderActiveFilters();
  control.querySelector("select")?.focus();
}

function loadJobsFromFirstPage() {
  state.jobPage = 1;
  return loadJobs();
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

function closeDialog() {
  $("#job-dialog").close();
  void checkDashboardRevision();
}

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

function setDashboardSyncStatus(message, status = "live") {
  const indicator = $("#dashboard-sync-status");
  if (!indicator) return;
  indicator.dataset.state = status;
  indicator.setAttribute("aria-label", message);
  const text = indicator.querySelector(".sync-status-text");
  if (text) text.textContent = message;
}

function canAutoRefreshDashboard() {
  const currentFrame = state.sankeyFrames[state.sankeyFrameIndex];
  return !$("#job-dialog")?.open
    && !state.sankeyPlaying
    && (!currentFrame || currentFrame.live);
}

async function refreshDashboard() {
  if (state.dashboardRefreshPromise) return state.dashboardRefreshPromise;
  state.dashboardRefreshPromise = (async () => {
    const [stats, recommendations, history, sankey, sankeyTimeline, workspace, revision] = await Promise.all([
      api("/api/stats"),
      api("/api/recommendations"),
      api("/api/history"),
      api("/api/sankey"),
      api("/api/sankey/timeline"),
      api("/api/workspace"),
      api("/api/revision"),
    ]);
    await loadJobs();
    renderStats(stats);
    renderFreshness(stats.freshness_conversion);
    renderRecommendations(recommendations);
    renderWorkspace(workspace);
    renderHistory(history);
    renderSankeyHistory(sankeyTimeline, sankey);
    renderSankey(sankey);
    state.dashboardRevision = revision.revision;
    state.dashboardPendingRevision = null;
    setDashboardSyncStatus("Updated just now");
  })();
  try {
    return await state.dashboardRefreshPromise;
  } finally {
    state.dashboardRefreshPromise = null;
  }
}

async function checkDashboardRevision() {
  if (state.dashboardRevisionCheckPromise) return;
  state.dashboardRevisionCheckPromise = (async () => {
    try {
      const revision = await api("/api/revision");
      if (state.dashboardRevision === null) {
        state.dashboardRevision = revision.revision;
        setDashboardSyncStatus("Live updates on");
        return;
      }
      if (revision.revision === state.dashboardRevision) {
        if (!state.dashboardPendingRevision) setDashboardSyncStatus("Live updates on");
        return;
      }
      state.dashboardPendingRevision = revision.revision;
      if (!canAutoRefreshDashboard()) {
        setDashboardSyncStatus("Update available", "pending");
        return;
      }
      setDashboardSyncStatus("Updating dashboard", "updating");
      await refreshDashboard();
    } catch (error) {
      console.warn("Dashboard live update check failed", error);
      setDashboardSyncStatus("Live updates reconnecting", "error");
    }
  })();
  try {
    await state.dashboardRevisionCheckPromise;
  } finally {
    state.dashboardRevisionCheckPromise = null;
  }
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

$("#sankey-timeline-mode").addEventListener("change", async event => {
  stopSankeyPlayback();
  const currentFrame = state.sankeyFrames[state.sankeyFrameIndex];
  rebuildSankeyFrames(event.target.value);
  let frameIndex = state.sankeyFrames.length - 1;
  if (currentFrame && !currentFrame.live) {
    frameIndex = state.sankeyFrames.findIndex(
      frame => String(frame.id) === String(currentFrame.id)
    );
    if (frameIndex < 0) {
      const currentTime = new Date(currentFrame.created_at).getTime();
      frameIndex = state.sankeyFrames
        .map((frame, index) => ({
          index,
          distance: frame.live
            ? Number.MAX_SAFE_INTEGER
            : Math.abs(new Date(frame.created_at).getTime() - currentTime),
        }))
        .sort((left, right) => left.distance - right.distance)[0].index;
    }
  }
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

$("#sankey-playback-speed").addEventListener("change", event => {
  state.sankeyPlaybackSpeed = Number(event.target.value) || 1;
  if (state.sankeyPlaying) scheduleSankeyPlayback();
});

$("#sankey-next").addEventListener("click", async () => {
  stopSankeyPlayback();
  await showSankeyFrame(state.sankeyFrameIndex + 1);
});

$("#sankey-live").addEventListener("click", async () => {
  stopSankeyPlayback();
  await showSankeyFrame(state.sankeyFrames.length - 1);
  void checkDashboardRevision();
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
$("#search-input").addEventListener("input", () => loadJobsFromFirstPage());
$("#status-filter").addEventListener("change", () => loadJobsFromFirstPage());
$("#tier-filter").addEventListener("change", () => loadJobsFromFirstPage());
$("#archive-filter").addEventListener("change", () => loadJobsFromFirstPage());
$("#jobs-sort").addEventListener("change", () => loadJobsFromFirstPage());
$("#clear-filters").addEventListener("click", () => clearAdvancedFilters());
$("#jobs-page-previous").addEventListener("click", () => {
  state.jobPage = Math.max(1, state.jobPage - 1);
  renderJobs();
});
$("#jobs-page-next").addEventListener("click", () => {
  state.jobPage += 1;
  renderJobs();
});
$("#add-filter-menu").addEventListener("click", event => {
  const filter = event.target.closest("[data-add-filter]");
  if (filter) addFilter(filter.dataset.addFilter);
});
$("#filter-controls").addEventListener("click", event => {
  const filter = event.target.closest("[data-remove-filter]");
  if (filter) clearFilter(filter.dataset.removeFilter);
});
document.querySelectorAll("[data-workflow]").forEach(button => {
  button.addEventListener("click", () => {
    activateWorkflow(button.dataset.workflow);
    loadJobsFromFirstPage();
  });
});
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
  if (event.target.closest("[data-job-link]")) return;
  const edit = event.target.closest("[data-edit-id]");
  const card = event.target.closest("[data-job-id]");
  const id = Number(edit?.dataset.editId || card?.dataset.jobId);
  if (id) openDialog(state.jobIndex.get(id) || null);
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") void checkDashboardRevision();
});
window.addEventListener("focus", () => void checkDashboardRevision());
window.setInterval(() => void checkDashboardRevision(), DASHBOARD_REFRESH_INTERVAL_MS);

$("#today-label").textContent = new Date().toLocaleDateString(undefined, {
  weekday: "long", month: "long", day: "numeric", year: "numeric"
});

activateWorkflow("new");
loadAll().then(renderJobs).catch(error => {
  console.error(error);
  const message = `Unable to load dashboard: ${escapeHtml(error.message)}`;
  $("#recommendations").innerHTML = `<div class="empty-state error-state" role="alert">${message}</div>`;
  $("#jobs-table").innerHTML = `<tr><td colspan="5" class="error-state" role="alert">${message}</td></tr>`;
  $("#mobile-job-list").innerHTML = `<div class="empty-state error-state" role="alert">${message}</div>`;
});
