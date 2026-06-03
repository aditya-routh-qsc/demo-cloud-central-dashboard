const state = {
  filters: {
    search: "",
    statuses: [],
    assignees: [],
    excludedStatuses: [],
    excludedAssignees: [],
    boardId: "",
    offset: 0,
  },
  filterOptions: {
    statuses: [],
    assignees: [],
  },
  sync: null,
  metrics: null,
  tickets: [],
  ticketGroups: [],
  ticketTotal: 0,
  network: null,
  networkLoadError: "",
  jiraDomain: "qsc.atlassian.net",
  charts: {},
  cy: null,
  ui: {
    advancedFiltersOpen: true,
  },
};

const pollIntervalMs = 15000;
const mobileBreakpoint = 900;
const maxTicketLimit = 1000;

const GRAPH_SEMANTICS = {
  issueTypes: [
    { key: "bug", label: "Bug", color: "#ff6b6b" },
    { key: "story", label: "Story", color: "#1dd3ff" },
    { key: "task", label: "Task", color: "#3ad29f" },
    { key: "epic", label: "Epic", color: "#9b7bff" },
    { key: "sub_task", label: "Sub-task", color: "#f7b267" },
    { key: "unknown", label: "Unknown", color: "#7b8ca6" },
  ],
  dependencyTypes: [
    { key: "blockers", label: "Blockers", color: "#ff9f43" },
    { key: "blocks", label: "Blocks", color: "#ff6b6b" },
    { key: "depends_on", label: "Depends on", color: "#3ad29f" },
    { key: "relates_to", label: "Relates to", color: "#1dd3ff" },
    { key: "duplicates", label: "Duplicates", color: "#f85d9f" },
    { key: "unknown", label: "Unknown", color: "#7b8ca6" },
  ],
  classifications: [
    { key: "intra_team", label: "Intra-team", lineStyle: "solid", color: "#3ad29f" },
    { key: "inter_team", label: "Inter-team", lineStyle: "dashed", color: "#ff9f43" },
    { key: "unknown", label: "Unknown", lineStyle: "solid", color: "#7b8ca6" },
  ],
};

const ISSUE_TYPE_BY_KEY = new Map(GRAPH_SEMANTICS.issueTypes.map((entry) => [entry.key, entry]));
const DEPENDENCY_TYPE_BY_KEY = new Map(GRAPH_SEMANTICS.dependencyTypes.map((entry) => [entry.key, entry]));
const CLASSIFICATION_BY_KEY = new Map(GRAPH_SEMANTICS.classifications.map((entry) => [entry.key, entry]));
const ISSUE_TYPE_ALIASES = new Map([
  ["subtask", "sub_task"],
  ["sub_task", "sub_task"],
  ["sub-task", "sub_task"],
  ["technical_task", "task"],
  ["development_task", "task"],
  ["feature", "story"],
]);
const DEPENDENCY_TYPE_ALIASES = new Map([
  ["blocking", "blocks"],
  ["blocker", "blockers"],
  ["blockers", "blockers"],
  ["blocks", "blocks"],
  ["depends_upon", "depends_on"],
  ["depends_on", "depends_on"],
  ["relates", "relates_to"],
  ["relates_to", "relates_to"],
  ["duplicate", "duplicates"],
  ["duplicates", "duplicates"],
]);

const el = {
  syncChip: document.getElementById("syncChip"),
  manualSyncBtn: document.getElementById("manualSyncBtn"),
  toggleAdvancedFiltersBtn: document.getElementById("toggleAdvancedFiltersBtn"),
  advancedFilters: document.getElementById("advancedFilters"),
  searchInput: document.getElementById("searchInput"),
  statusSelect: document.getElementById("statusSelect"),
  assigneeSelect: document.getElementById("assigneeSelect"),
  statusSummary: document.getElementById("statusSummary"),
  assigneeSummary: document.getElementById("assigneeSummary"),
  boardInput: document.getElementById("boardInput"),
  applyFiltersBtn: document.getElementById("applyFiltersBtn"),
  resetFiltersBtn: document.getElementById("resetFiltersBtn"),
  ticketsGroups: document.getElementById("ticketsGroups"),
  nodeDetails: document.getElementById("nodeDetails"),
  networkLegend: document.getElementById("networkLegend"),
  networkEmptyState: document.getElementById("networkEmptyState"),
  networkMobileSummary: document.getElementById("networkMobileSummary"),
  networkGraph: document.getElementById("networkGraph"),
  kpiTotalActive: document.getElementById("kpiTotalActive"),
  kpiOpenBugs: document.getElementById("kpiOpenBugs"),
  kpiStale: document.getElementById("kpiStale"),
  kpiFilteredTotal: document.getElementById("kpiFilteredTotal"),
};

function isNarrowViewport() {
  return window.innerWidth <= mobileBreakpoint;
}

function syncAdvancedFiltersDisclosure() {
  if (!el.toggleAdvancedFiltersBtn || !el.advancedFilters) {
    return;
  }

  const isOpen = state.ui.advancedFiltersOpen;
  el.toggleAdvancedFiltersBtn.setAttribute("aria-expanded", String(isOpen));
  el.toggleAdvancedFiltersBtn.textContent = isOpen ? "Hide advanced filters" : "Show advanced filters";
  el.advancedFilters.classList.toggle("is-collapsed", !isOpen);
  el.advancedFilters.hidden = !isOpen;
}

function setAdvancedFiltersOpen(nextOpen, options = {}) {
  state.ui.advancedFiltersOpen = Boolean(nextOpen);
  syncAdvancedFiltersDisclosure();

  if (options.focusToggle && el.toggleAdvancedFiltersBtn) {
    el.toggleAdvancedFiltersBtn.focus();
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function uniqueValues(values) {
  const seen = new Set();
  const items = [];
  for (const rawValue of values || []) {
    const value = String(rawValue || "").trim();
    if (!value) {
      continue;
    }
    const key = value.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    items.push(value);
  }
  return items;
}

function normalizeSemanticKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}

function getIssueTypeEntry(rawValue) {
  const normalizedValue = normalizeSemanticKey(rawValue);
  const canonicalValue = ISSUE_TYPE_ALIASES.get(normalizedValue) || normalizedValue;
  if (ISSUE_TYPE_BY_KEY.has(canonicalValue)) {
    return ISSUE_TYPE_BY_KEY.get(canonicalValue);
  }

  // Fallback matching handles verbose Jira issue type labels such as
  // "Technical Task" or "Epic Feature" without requiring exact aliases.
  if (canonicalValue.includes("epic")) {
    return ISSUE_TYPE_BY_KEY.get("epic");
  }
  if (canonicalValue.includes("task")) {
    return ISSUE_TYPE_BY_KEY.get("task");
  }
  if (canonicalValue.includes("story")) {
    return ISSUE_TYPE_BY_KEY.get("story");
  }
  if (canonicalValue.includes("bug")) {
    return ISSUE_TYPE_BY_KEY.get("bug");
  }

  return ISSUE_TYPE_BY_KEY.get("unknown");
}

function getDependencyTypeEntry(rawValue) {
  const normalizedValue = normalizeSemanticKey(rawValue);
  const canonicalValue = DEPENDENCY_TYPE_ALIASES.get(normalizedValue) || normalizedValue;
  return DEPENDENCY_TYPE_BY_KEY.get(canonicalValue) || DEPENDENCY_TYPE_BY_KEY.get("unknown");
}

function getClassificationEntry(rawValue) {
  const normalizedValue = normalizeSemanticKey(rawValue);
  return CLASSIFICATION_BY_KEY.get(normalizedValue) || CLASSIFICATION_BY_KEY.get("unknown");
}

function buildNetworkStyles() {
  const styles = [
    {
      selector: "node",
      style: {
        "background-color": ISSUE_TYPE_BY_KEY.get("unknown").color,
        color: "#eef7ff",
        "font-size": 9,
        "text-valign": "center",
        label: "data(ticket_key)",
      },
    },
    {
      selector: "edge",
      style: {
        width: 2,
        "line-color": DEPENDENCY_TYPE_BY_KEY.get("unknown").color,
        "target-arrow-color": DEPENDENCY_TYPE_BY_KEY.get("unknown").color,
        "source-arrow-color": DEPENDENCY_TYPE_BY_KEY.get("unknown").color,
        "source-arrow-shape": "none",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
      },
    },
  ];

  for (const entry of GRAPH_SEMANTICS.issueTypes) {
    styles.push({
      selector: `node[issue_type_key = '${entry.key}']`,
      style: {
        "background-color": entry.color,
      },
    });
  }

  for (const entry of GRAPH_SEMANTICS.dependencyTypes) {
    styles.push({
      selector: `edge[dependency_type_key = '${entry.key}']`,
      style: {
        "line-color": entry.color,
        "target-arrow-color": entry.color,
        "source-arrow-color": entry.color,
      },
    });
  }

  styles.push({
    selector: "edge[dependency_type_key = 'relates_to']",
    style: {
      "source-arrow-shape": "none",
      "target-arrow-shape": "none",
    },
  });

  for (const entry of GRAPH_SEMANTICS.classifications) {
    styles.push({
      selector: `edge[classification_key = '${entry.key}']`,
      style: {
        "line-style": entry.lineStyle,
      },
    });
  }

  return styles;
}

function renderLegendList(entries, variant) {
  return entries
    .map((entry) => {
      if (variant === "line") {
        return `
          <li class="legend-item">
            <span class="legend-line ${entry.lineStyle}" style="color: ${entry.color};"></span>
            <span>${escapeHtml(entry.label)}</span>
          </li>
        `;
      }

      return `
        <li class="legend-item">
          <span class="legend-swatch" style="background-color: ${entry.color};"></span>
          <span>${escapeHtml(entry.label)}</span>
        </li>
      `;
    })
    .join("");
}

function renderNetworkLegend() {
  if (!el.networkLegend) {
    return;
  }

  el.networkLegend.className = "network-legend is-visible";
  el.networkLegend.innerHTML = `
    <div class="legend-grid">
      <section class="legend-section">
        <h4>Ticket types</h4>
        <ul class="legend-list">
          ${renderLegendList(GRAPH_SEMANTICS.issueTypes, "swatch")}
        </ul>
      </section>
      <section class="legend-section">
        <h4>Dependency types</h4>
        <ul class="legend-list">
          ${renderLegendList(GRAPH_SEMANTICS.dependencyTypes, "swatch")}
        </ul>
      </section>
      <section class="legend-section">
        <h4>Classification</h4>
        <ul class="legend-list">
          ${renderLegendList(GRAPH_SEMANTICS.classifications, "line")}
        </ul>
      </section>
    </div>
  `;
}

function hideNetworkLegend() {
  if (!el.networkLegend) {
    return;
  }

  el.networkLegend.className = "network-legend";
  el.networkLegend.innerHTML = "";
}

function parseStatusQuery(params) {
  const rawValues = params.getAll("status");
  if (rawValues.length === 1 && rawValues[0].includes(",")) {
    return uniqueValues(rawValues[0].split(","));
  }
  return uniqueValues(rawValues);
}

function parseAssigneeQuery(params) {
  return uniqueValues(params.getAll("assignee"));
}

function parseStatusExcludeQuery(params) {
  const rawValues = params.getAll("status_exclude");
  if (rawValues.length === 1 && rawValues[0].includes(",")) {
    return uniqueValues(rawValues[0].split(","));
  }
  return uniqueValues(rawValues);
}

function parseAssigneeExcludeQuery(params) {
  return uniqueValues(params.getAll("assignee_exclude"));
}

function getSelectedValues(selectEl) {
  return Array.from(selectEl.selectedOptions)
    .map((option) => option.value.trim())
    .filter(Boolean);
}

function setSelectedValues(selectEl, values) {
  const previousScrollTop = selectEl.scrollTop;
  const selectedKeys = new Set((values || []).map((value) => value.toLowerCase()));
  for (const option of selectEl.options) {
    option.selected = selectedKeys.has(option.value.toLowerCase());
  }
  restoreSelectScroll(selectEl, previousScrollTop);
}

function restoreSelectScroll(selectEl, scrollTop) {
  requestAnimationFrame(() => {
    selectEl.scrollTop = scrollTop;
    requestAnimationFrame(() => {
      selectEl.scrollTop = scrollTop;
    });
  });
}

function applyExcludedOptionStyles(selectEl, excludedValues) {
  const excludedKeys = new Set((excludedValues || []).map((value) => String(value || "").toLowerCase()));
  for (const option of selectEl.options) {
    const baseLabel = option.dataset.label || option.value;
    const isExcluded = excludedKeys.has(String(option.value || "").toLowerCase());
    option.classList.toggle("is-excluded", isExcluded);
    const displayLabel = isExcluded ? `${baseLabel} (excluded)` : baseLabel;
    if (option.textContent !== displayLabel) {
      option.textContent = displayLabel;
    }
  }
}

function refreshExcludeStyles() {
  const statusScrollTop = el.statusSelect.scrollTop;
  const assigneeScrollTop = el.assigneeSelect.scrollTop;
  applyExcludedOptionStyles(el.statusSelect, state.filters.excludedStatuses);
  applyExcludedOptionStyles(el.assigneeSelect, state.filters.excludedAssignees);
  restoreSelectScroll(el.statusSelect, statusScrollTop);
  restoreSelectScroll(el.assigneeSelect, assigneeScrollTop);
}

function enableToggleMultiSelect(selectEl, includeKey, excludeKey) {
  // Native multi-select requires Ctrl/Cmd; this enables click-to-toggle behavior.
  selectEl.addEventListener("mousedown", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLOptionElement)) {
      return;
    }
    event.preventDefault();
    const previousScrollTop = selectEl.scrollTop;
    target.selected = !target.selected;

    if (target.selected && includeKey && excludeKey) {
      const valueKey = String(target.value || "").trim().toLowerCase();
      state.filters[excludeKey] = uniqueValues(state.filters[excludeKey] || []).filter(
        (value) => value.toLowerCase() !== valueKey,
      );
      updateFilterSummaries();
      refreshExcludeStyles();
    }

    const changeEvent = new Event("change", { bubbles: true });
    selectEl.dispatchEvent(changeEvent);
    restoreSelectScroll(selectEl, previousScrollTop);
  });
}

function bindExcludeOnDoubleClick(selectEl, includeKey, excludeKey) {
  selectEl.addEventListener("dblclick", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLOptionElement)) {
      return;
    }
    event.preventDefault();
    const previousScrollTop = selectEl.scrollTop;

    const value = String(target.value || "").trim();
    if (!value) {
      return;
    }

    const includeValues = uniqueValues(state.filters[includeKey] || []);
    const excludeValues = uniqueValues(state.filters[excludeKey] || []);
    const valueKey = value.toLowerCase();

    const currentlyExcluded = excludeValues.some((item) => item.toLowerCase() === valueKey);
    state.filters[excludeKey] = currentlyExcluded
      ? excludeValues.filter((item) => item.toLowerCase() !== valueKey)
      : [...excludeValues, value];

    state.filters[includeKey] = includeValues.filter((item) => item.toLowerCase() !== valueKey);
    target.selected = false;

    applyStateToQuery();
    updateFilterSummaries();
    refreshExcludeStyles();
    restoreSelectScroll(selectEl, previousScrollTop);
  });
}

function updateFilterSummaries() {
  const statuses = state.filters.statuses;
  const assignees = state.filters.assignees;
  const excludedStatuses = state.filters.excludedStatuses;
  const excludedAssignees = state.filters.excludedAssignees;

  const statusParts = [];
  if (statuses.length) {
    statusParts.push(
      `${statuses.length} selected: ${statuses.slice(0, 2).join(", ")}${statuses.length > 2 ? "..." : ""}`,
    );
  }
  if (excludedStatuses.length) {
    statusParts.push(
      `${excludedStatuses.length} excluded: ${excludedStatuses.slice(0, 2).join(", ")}${excludedStatuses.length > 2 ? "..." : ""}`,
    );
  }
  el.statusSummary.textContent = statusParts.length ? statusParts.join(" | ") : "All statuses";

  const assigneeParts = [];
  if (assignees.length) {
    assigneeParts.push(
      `${assignees.length} selected: ${assignees.slice(0, 2).join(", ")}${assignees.length > 2 ? "..." : ""}`,
    );
  }
  if (excludedAssignees.length) {
    assigneeParts.push(
      `${excludedAssignees.length} excluded: ${excludedAssignees.slice(0, 2).join(", ")}${excludedAssignees.length > 2 ? "..." : ""}`,
    );
  }
  el.assigneeSummary.textContent = assigneeParts.length ? assigneeParts.join(" | ") : "All assignees";
}

function buildGroupedTicketsFromRows(rows) {
  const grouped = new Map();
  for (const ticket of rows || []) {
    const assignee = String(ticket.assignee || "").trim() || "Unassigned";
    if (!grouped.has(assignee)) {
      grouped.set(assignee, []);
    }
    grouped.get(assignee).push(ticket);
  }

  return Array.from(grouped.entries())
    .map(([assignee, items]) => ({ assignee, count: items.length, items }))
    .sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.assignee.localeCompare(right.assignee);
    });
}

async function apiGet(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function apiPost(path) {
  const response = await fetch(path, { method: "POST", headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function applyStateToQuery() {
  const params = new URLSearchParams();
  if (state.filters.search) params.set("search", state.filters.search);
  for (const status of state.filters.statuses) {
    params.append("status", status);
  }
  for (const assignee of state.filters.assignees) {
    params.append("assignee", assignee);
  }
  for (const status of state.filters.excludedStatuses) {
    params.append("status_exclude", status);
  }
  for (const assignee of state.filters.excludedAssignees) {
    params.append("assignee_exclude", assignee);
  }
  if (state.filters.boardId) params.set("board", state.filters.boardId);
  if (state.filters.offset) params.set("offset", String(state.filters.offset));
  const query = params.toString();
  history.replaceState(null, "", query ? `?${query}` : location.pathname);
}

function readStateFromQuery() {
  const params = new URLSearchParams(location.search);
  state.filters.search = params.get("search") || "";
  state.filters.statuses = parseStatusQuery(params);
  state.filters.assignees = parseAssigneeQuery(params);
  state.filters.excludedStatuses = parseStatusExcludeQuery(params);
  state.filters.excludedAssignees = parseAssigneeExcludeQuery(params);
  state.filters.boardId = params.get("board") || "";
  state.filters.offset = Number(params.get("offset") || 0);
  if (!Number.isFinite(state.filters.offset) || state.filters.offset < 0) {
    state.filters.offset = 0;
  }
}

function syncInputsFromState() {
  el.searchInput.value = state.filters.search;
  el.boardInput.value = state.filters.boardId;
  setSelectedValues(el.statusSelect, state.filters.statuses);
  setSelectedValues(el.assigneeSelect, state.filters.assignees);
  updateFilterSummaries();
}

function buildTicketsQuery() {
  const params = new URLSearchParams();
  if (state.filters.search) params.set("search", state.filters.search);
  for (const status of state.filters.statuses) {
    params.append("status", status);
  }
  for (const assignee of state.filters.assignees) {
    params.append("assignee", assignee);
  }
  for (const status of state.filters.excludedStatuses) {
    params.append("status_exclude", status);
  }
  for (const assignee of state.filters.excludedAssignees) {
    params.append("assignee_exclude", assignee);
  }
  if (state.filters.boardId) params.set("board_id", state.filters.boardId);
  params.set("limit", String(maxTicketLimit));
  params.set("offset", String(state.filters.offset));
  return `/api/tickets?${params.toString()}`;
}

function buildSharedFilterQuery(basePath) {
  const params = new URLSearchParams();
  if (state.filters.search) params.set("search", state.filters.search);
  for (const status of state.filters.statuses) {
    params.append("status", status);
  }
  for (const assignee of state.filters.assignees) {
    params.append("assignee", assignee);
  }
  for (const status of state.filters.excludedStatuses) {
    params.append("status_exclude", status);
  }
  for (const assignee of state.filters.excludedAssignees) {
    params.append("assignee_exclude", assignee);
  }
  if (state.filters.boardId) params.set("board_id", state.filters.boardId);
  const query = params.toString();
  return query ? `${basePath}?${query}` : basePath;
}

function updateFilterStateFromInputs() {
  state.filters.search = el.searchInput.value.trim();
  const selectedStatuses = uniqueValues(getSelectedValues(el.statusSelect));
  const selectedAssignees = uniqueValues(getSelectedValues(el.assigneeSelect));

  state.filters.statuses = selectedStatuses.filter(
    (status) => !state.filters.excludedStatuses.some((excluded) => excluded.toLowerCase() === status.toLowerCase()),
  );
  state.filters.assignees = selectedAssignees.filter(
    (assignee) => !state.filters.excludedAssignees.some((excluded) => excluded.toLowerCase() === assignee.toLowerCase()),
  );

  const availableStatuses = new Set((state.filterOptions.statuses || []).map((value) => value.toLowerCase()));
  const availableAssignees = new Set((state.filterOptions.assignees || []).map((value) => value.toLowerCase()));
  state.filters.excludedStatuses = uniqueValues(state.filters.excludedStatuses).filter(
    (status) => availableStatuses.has(status.toLowerCase()),
  );
  state.filters.excludedAssignees = uniqueValues(state.filters.excludedAssignees).filter(
    (assignee) => availableAssignees.has(assignee.toLowerCase()),
  );

  state.filters.boardId = el.boardInput.value.trim();
  state.filters.offset = 0;
  applyStateToQuery();
  updateFilterSummaries();
}

function inferJiraDomainFromTicket(ticket) {
  if (!ticket || !Array.isArray(ticket.source_links) || !ticket.source_links.length) {
    return;
  }
  try {
    const host = new URL(ticket.source_links[0]).host;
    if (host) {
      state.jiraDomain = host;
    }
  } catch (_error) {
    // Keep default domain.
  }
}

function jiraIssueUrl(ticketKey) {
  return `https://${state.jiraDomain}/browse/${encodeURIComponent(ticketKey)}`;
}

function renderSyncChip() {
  if (!state.sync) {
    el.syncChip.textContent = "Sync status: unavailable";
    el.syncChip.className = "sync-chip error";
    return;
  }

  const runtime = state.sync.runtime || {};
  const persisted = state.sync.persisted || {};
  const run = persisted.last_run || null;

  el.syncChip.className = "sync-chip";

  if (runtime.last_error) {
    el.syncChip.textContent = `Sync status: error (${runtime.last_error})`;
    el.syncChip.classList.add("error");
    return;
  }

  if (runtime.is_running) {
    const trigger = runtime.trigger || "unknown";
    el.syncChip.textContent = `Sync status: running (${trigger})`;
    el.syncChip.classList.add("running");
    return;
  }

  if (run && run.started_at) {
    el.syncChip.textContent = `Sync status: last ${run.status || "unknown"} (${run.started_at})`;
    return;
  }

  el.syncChip.textContent = "Sync status: idle";
}

function renderKpis() {
  const kpis = (state.metrics && state.metrics.kpis) || {};
  el.kpiTotalActive.textContent = String(kpis.total_active_tickets ?? "-");
  el.kpiOpenBugs.textContent = String(kpis.open_bug_count ?? "-");
  el.kpiStale.textContent = String(kpis.stale_tickets_over_14_days ?? "-");
  el.kpiFilteredTotal.textContent = String(state.ticketTotal ?? "-");
}

function destroyChart(name) {
  if (state.charts[name]) {
    state.charts[name].destroy();
    delete state.charts[name];
  }
}

function makeChart(canvasId, config, stateKey) {
  destroyChart(stateKey);
  const chartCtor = window.Chart;
  const canvas = document.getElementById(canvasId);
  if (!chartCtor || !canvas) {
    return;
  }
  state.charts[stateKey] = new chartCtor(canvas, config);
}

function renderStatusChart() {
  const rows = (state.metrics && state.metrics.active_by_status) || [];
  makeChart("statusChart", {
    type: "bar",
    data: {
      labels: rows.map((row) => row.status),
      datasets: [{
        label: "Tickets",
        data: rows.map((row) => row.count),
        backgroundColor: "rgba(29, 211, 255, 0.62)",
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  }, "status");
}

function renderDependencyChart() {
  const dep = (state.metrics && state.metrics.dependency_summary) || {};
  makeChart("dependencyChart", {
    type: "doughnut",
    data: {
      labels: ["Blockers", "Inter-team", "Intra-team"],
      datasets: [{
        data: [dep.blockers || 0, dep.inter_team || 0, dep.intra_team || 0],
        backgroundColor: ["#ff6b6b", "#ff9f43", "#3ad29f"],
      }],
    },
    options: { responsive: true },
  }, "dependency");
}

function renderStoryPointsChart() {
  const byStatus = new Map();
  for (const ticket of state.tickets) {
    const key = ticket.status || "Unknown";
    const points = Number(ticket.story_points || 0);
    byStatus.set(key, (byStatus.get(key) || 0) + points);
  }

  makeChart("storyPointsChart", {
    type: "bar",
    data: {
      labels: Array.from(byStatus.keys()),
      datasets: [{
        label: "Story points",
        data: Array.from(byStatus.values()),
        backgroundColor: "rgba(58, 210, 159, 0.66)",
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  }, "storyPoints");
}

function renderAssigneeChart() {
  const byAssignee = new Map();
  for (const ticket of state.tickets) {
    const key = ticket.assignee || "Unassigned";
    byAssignee.set(key, (byAssignee.get(key) || 0) + 1);
  }
  const rows = Array.from(byAssignee.entries())
    .sort((left, right) => right[1] - left[1])
    .slice(0, 8);

  makeChart("assigneeChart", {
    type: "bar",
    data: {
      labels: rows.map((row) => row[0]),
      datasets: [{
        label: "Tickets",
        data: rows.map((row) => row[1]),
        backgroundColor: "rgba(255, 159, 67, 0.64)",
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  }, "assignee");
}

function renderTickets() {
  if (!state.ticketGroups.length) {
    el.ticketsGroups.innerHTML = "<p class='muted'>No tickets match the active filters.</p>";
    return;
  }

  const sections = state.ticketGroups.map((group) => {
    const rows = (group.items || []).map((ticket) => {
      const issueUrl = jiraIssueUrl(ticket.ticket_key || "");
      return `<tr>
        <td>${escapeHtml(ticket.ticket_key)}</td>
        <td>${escapeHtml(ticket.summary)}</td>
        <td>${escapeHtml(ticket.status)}</td>
        <td>${escapeHtml(ticket.priority)}</td>
        <td><a class="jira-link" href="${issueUrl}" target="_blank" rel="noopener noreferrer">Open</a></td>
      </tr>`;
    });

    return `<section class="ticket-group">
      <h4>${escapeHtml(group.assignee)} <span class="ticket-group-count">(${group.count})</span></h4>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Key</th>
              <th>Summary</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Jira</th>
            </tr>
          </thead>
          <tbody>${rows.join("")}</tbody>
        </table>
      </div>
    </section>`;
  });

  el.ticketsGroups.innerHTML = sections.join("");
}

function renderNetworkEmptyState(message, isError = false) {
  el.networkEmptyState.textContent = message;
  el.networkEmptyState.className = isError ? "network-empty error is-visible" : "network-empty muted is-visible";
}

function clearNetworkEmptyState() {
  el.networkEmptyState.textContent = "";
  el.networkEmptyState.className = "network-empty muted";
}

function renderMobileDependencySummary() {
  const dep = (state.metrics && state.metrics.dependency_summary) || {};
  const networkCounts = (state.network && state.network.counts) || { nodes: 0, edges: 0 };
  el.networkMobileSummary.className = "network-mobile-summary is-visible";
  el.networkMobileSummary.innerHTML = `
    <div class="summary-grid">
      <article class="summary-card"><h4>Blockers</h4><p>${dep.blockers || 0}</p></article>
      <article class="summary-card"><h4>Inter-team</h4><p>${dep.inter_team || 0}</p></article>
      <article class="summary-card"><h4>Intra-team</h4><p>${dep.intra_team || 0}</p></article>
      <article class="summary-card"><h4>Edges</h4><p>${networkCounts.edges || 0}</p></article>
    </div>
  `;
}

function renderNodeDependencyDetails(nodeId) {
  const network = state.network || { nodes: [], edges: [] };
  const nodeById = new Map((network.nodes || []).map((item) => [item.id, item]));
  const incoming = [];
  const outgoing = [];

  for (const edge of network.edges || []) {
    if (edge.target_ticket === nodeId) {
      incoming.push(edge);
    }
    if (edge.source_ticket === nodeId) {
      outgoing.push(edge);
    }
  }

  const formatEdge = (edge, isIncoming) => {
    const otherKey = isIncoming ? edge.source_ticket : edge.target_ticket;
    const otherNode = nodeById.get(otherKey) || {};
    const relation = edge.relation_description || edge.relation_name || edge.dependency_type || "dependency";
    const classification = edge.classification || "unknown";
    const status = otherNode.status || "Unknown";
    return `<li><strong>${escapeHtml(otherKey)}</strong> (${escapeHtml(status)}) - ${escapeHtml(relation)} [${escapeHtml(classification)}]</li>`;
  };

  const incomingHtml = incoming.length
    ? `<ul>${incoming.slice(0, 8).map((edge) => formatEdge(edge, true)).join("")}</ul>`
    : "<p class='muted'>No incoming dependencies.</p>";

  const outgoingHtml = outgoing.length
    ? `<ul>${outgoing.slice(0, 8).map((edge) => formatEdge(edge, false)).join("")}</ul>`
    : "<p class='muted'>No outgoing dependencies.</p>";

  const hiddenIncoming = incoming.length > 8 ? `<p class='muted'>+${incoming.length - 8} more incoming</p>` : "";
  const hiddenOutgoing = outgoing.length > 8 ? `<p class='muted'>+${outgoing.length - 8} more outgoing</p>` : "";

  return `
    <p><strong>Dependency details</strong></p>
    <p>Incoming: ${incoming.length} | Outgoing: ${outgoing.length}</p>
    <p><strong>Incoming (depends on this ticket)</strong></p>
    ${incomingHtml}
    ${hiddenIncoming}
    <p><strong>Outgoing (this ticket depends on)</strong></p>
    ${outgoingHtml}
    ${hiddenOutgoing}
  `;
}

function renderNetwork() {
  const cyCtor = window.cytoscape;
  const data = state.network || { nodes: [], edges: [], counts: { nodes: 0, edges: 0 } };

  if (state.cy) {
    state.cy.destroy();
    state.cy = null;
  }

  if (window.innerWidth <= mobileBreakpoint) {
    el.networkGraph.style.display = "none";
    hideNetworkLegend();
    renderMobileDependencySummary();
    renderNetworkEmptyState("Mobile summary mode: interactive graph is optimized for desktop.");
    return;
  }

  el.networkGraph.style.display = "block";
  el.networkMobileSummary.className = "network-mobile-summary";
  el.networkMobileSummary.innerHTML = "";
  renderNetworkLegend();

  if (state.networkLoadError) {
    renderNetworkEmptyState("Dependency graph unavailable. Check API/network logs and retry.", true);
    return;
  }

  if (!cyCtor) {
    renderNetworkEmptyState("Dependency graph library failed to load. Check CDN access.", true);
    return;
  }

  if (!Array.isArray(data.edges) || data.edges.length === 0) {
    renderNetworkEmptyState("No dependency edges found for the active filters.");
  } else {
    clearNetworkEmptyState();
  }

  const elements = [];
  for (const node of data.nodes || []) {
    const issueType = String(node.issue_type || "").trim();
    elements.push({
      data: {
        id: node.id,
        ticket_key: node.ticket_key,
        summary: node.summary || "",
        status: node.status || "",
        reporter: node.reporter || "",
        issue_type: issueType,
        issue_type_key: getIssueTypeEntry(issueType).key,
      },
    });
  }

  for (const edge of data.edges || []) {
    const dependencyType = String(edge.relation_description || edge.relation_name || edge.dependency_type || "").trim();
    const classification = String(edge.classification || "").trim();
    elements.push({
      data: {
        id: `${edge.source_ticket}->${edge.target_ticket}->${normalizeSemanticKey(dependencyType)}->${normalizeSemanticKey(classification)}`,
        source: edge.source_ticket,
        target: edge.target_ticket,
        relation_name: edge.relation_name || "",
        relation_description: edge.relation_description || "",
        dependency_type: dependencyType,
        dependency_type_key: getDependencyTypeEntry(dependencyType).key,
        classification,
        classification_key: getClassificationEntry(classification).key,
      },
    });
  }

  state.cy = cyCtor({
    container: el.networkGraph,
    elements,
    style: buildNetworkStyles(),
    layout: {
      name: "cose",
      animate: true,
      fit: true,
    },
  });

  state.cy.on("tap", "node", (event) => {
    const node = event.target.data();
    const issueUrl = jiraIssueUrl(node.id);
    const dependencyDetails = renderNodeDependencyDetails(node.id);
    el.nodeDetails.innerHTML = `<p><strong>${escapeHtml(node.ticket_key)}</strong></p>
      <p>${escapeHtml(node.summary || "No summary")}</p>
      <p>Status: ${escapeHtml(node.status || "Unknown")}</p>
      <p>Reporter: ${escapeHtml(node.reporter || "Unknown")}</p>
      <p>Ticket type: ${escapeHtml(node.issue_type || "Unknown")}</p>
      ${dependencyDetails}
      <p><a class="jira-link" href="${issueUrl}" target="_blank" rel="noopener noreferrer">Open in Jira</a></p>`;
  });
}

function setSelectOptions(selectEl, values) {
  const previousScrollTop = selectEl.scrollTop;
  const options = [];
  for (const value of values) {
    const safe = escapeHtml(value);
    options.push(`<option value='${safe}' data-label='${safe}'>${safe}</option>`);
  }
  if (!options.length) {
    options.push("<option value='' disabled data-label='(no options)'>(no options)</option>");
  }
  selectEl.innerHTML = options.join("");
  restoreSelectScroll(selectEl, previousScrollTop);
}

function refreshFilterOptions() {
  const statusScrollTop = el.statusSelect.scrollTop;
  const assigneeScrollTop = el.assigneeSelect.scrollTop;
  const statuses = Array.isArray(state.filterOptions.statuses) ? state.filterOptions.statuses : [];
  const assignees = Array.isArray(state.filterOptions.assignees) ? state.filterOptions.assignees : [];

  setSelectOptions(el.statusSelect, statuses);
  setSelectOptions(el.assigneeSelect, assignees);
  syncInputsFromState();
  refreshExcludeStyles();
  restoreSelectScroll(el.statusSelect, statusScrollTop);
  restoreSelectScroll(el.assigneeSelect, assigneeScrollTop);
}

async function loadSyncStatus() {
  try {
    state.sync = await apiGet("/api/sync/status");
  } catch (_error) {
    state.sync = null;
  }
  renderSyncChip();
}

async function loadDashboardData() {
  const [metricsResult, ticketsResult, networkResult] = await Promise.allSettled([
    apiGet(buildSharedFilterQuery("/api/metrics")),
    apiGet(buildTicketsQuery()),
    apiGet(buildSharedFilterQuery("/api/network")),
  ]);

  if (metricsResult.status !== "fulfilled") {
    throw metricsResult.reason;
  }
  if (ticketsResult.status !== "fulfilled") {
    throw ticketsResult.reason;
  }

  const ticketsPayload = ticketsResult.value || {};
  state.metrics = metricsResult.value;
  state.tickets = Array.isArray(ticketsPayload.items) ? ticketsPayload.items : [];
  state.ticketTotal = Number(ticketsPayload.total || 0);
  state.filterOptions = {
    statuses: Array.isArray(ticketsPayload.filter_options?.statuses) ? ticketsPayload.filter_options.statuses : [],
    assignees: Array.isArray(ticketsPayload.filter_options?.assignees) ? ticketsPayload.filter_options.assignees : [],
  };
  state.ticketGroups = Array.isArray(ticketsPayload.groups) && ticketsPayload.groups.length
    ? ticketsPayload.groups
    : buildGroupedTicketsFromRows(state.tickets);

  if (networkResult.status === "fulfilled") {
    state.network = networkResult.value;
    state.networkLoadError = "";
  } else {
    state.network = null;
    state.networkLoadError = String(networkResult.reason || "network load failed");
  }

  if (state.tickets.length) {
    inferJiraDomainFromTicket(state.tickets[0]);
  }

  renderKpis();
  renderStatusChart();
  renderDependencyChart();
  renderStoryPointsChart();
  renderAssigneeChart();
  refreshFilterOptions();
  renderTickets();
  renderNetwork();
}

function setActiveTab(tabName) {
  const tabs = document.querySelectorAll(".tab");
  const views = document.querySelectorAll(".view");
  for (const tab of tabs) {
    tab.classList.toggle("is-active", tab.dataset.tab === tabName);
  }
  for (const view of views) {
    view.classList.toggle("is-active", view.id === tabName);
  }
}

function bindTabNavigation() {
  const tabs = document.querySelectorAll(".tab");
  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      setActiveTab(tab.dataset.tab);
    });
  }
}

function bindFilterDisclosure() {
  if (!el.toggleAdvancedFiltersBtn || !el.advancedFilters) {
    return;
  }

  if (isNarrowViewport()) {
    state.ui.advancedFiltersOpen = false;
  }
  syncAdvancedFiltersDisclosure();

  el.toggleAdvancedFiltersBtn.addEventListener("click", () => {
    setAdvancedFiltersOpen(!state.ui.advancedFiltersOpen);
  });
}

function bindActions() {
  enableToggleMultiSelect(el.statusSelect, "statuses", "excludedStatuses");
  enableToggleMultiSelect(el.assigneeSelect, "assignees", "excludedAssignees");
  bindExcludeOnDoubleClick(el.statusSelect, "statuses", "excludedStatuses");
  bindExcludeOnDoubleClick(el.assigneeSelect, "assignees", "excludedAssignees");

  el.applyFiltersBtn.addEventListener("click", async () => {
    updateFilterStateFromInputs();
    await loadDashboardData();
  });

  el.resetFiltersBtn.addEventListener("click", async () => {
    state.filters = {
      search: "",
      statuses: [],
      assignees: [],
      excludedStatuses: [],
      excludedAssignees: [],
      boardId: "",
      offset: 0,
    };
    applyStateToQuery();
    syncInputsFromState();
    await loadDashboardData();
  });

  el.manualSyncBtn.addEventListener("click", async () => {
    try {
      await apiPost("/api/sync/manual");
    } catch (_error) {
      // Status polling will surface failures.
    }
    await loadSyncStatus();
  });

  window.addEventListener("resize", () => {
    renderNetwork();
  });
}

async function bootstrap() {
  readStateFromQuery();
  bindTabNavigation();
  bindFilterDisclosure();
  bindActions();
  await loadSyncStatus();
  await loadDashboardData();
  syncInputsFromState();
  setInterval(loadSyncStatus, pollIntervalMs);
}

bootstrap();
