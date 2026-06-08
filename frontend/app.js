const state = {
  filters: {
    search: "",
    teams: [],
    statuses: [],
    assignees: [],
    excludedStatuses: [],
    excludedAssignees: [],
    boardId: "",
    offset: 0,
  },
  filterOptions: {
    teams: [],
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
  teamsWorkspace: null,
  selectedTeamId: "",
  selectedTeamTab: "assigned",
  teamDetail: null,
  teamDetailLoading: false,
  jiraDomain: "qsc.atlassian.net",
  charts: {},
  cy: null,
  infocomm: {
    selectedShow: "india",
    selectedDate: "",
    schedule: [],
    loading: false,
  },
  ui: {
    advancedFiltersOpen: true,
    sidebarCollapsed: false,
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
  dashboardShell: document.querySelector(".dashboard-shell"),
  syncChip: document.getElementById("syncChip"),
  lastUpdatedText: document.getElementById("lastUpdatedText"),
  manualSyncBtn: document.getElementById("manualSyncBtn"),
  toggleSidebarBtn: document.getElementById("toggleSidebarBtn"),
  toggleAdvancedFiltersBtn: document.getElementById("toggleAdvancedFiltersBtn"),
  advancedFilters: document.getElementById("advancedFilters"),
  searchInput: document.getElementById("searchInput"),
  teamSelect: document.getElementById("teamSelect"),
  statusSelect: document.getElementById("statusSelect"),
  assigneeSelect: document.getElementById("assigneeSelect"),
  teamSummary: document.getElementById("teamSummary"),
  statusSummary: document.getElementById("statusSummary"),
  assigneeSummary: document.getElementById("assigneeSummary"),
  assigneeSelectAllBtn: document.getElementById("assigneeSelectAllBtn"),
  assigneeClearAllBtn: document.getElementById("assigneeClearAllBtn"),
  boardInput: document.getElementById("boardInput"),
  applyFiltersBtn: document.getElementById("applyFiltersBtn"),
  resetFiltersBtn: document.getElementById("resetFiltersBtn"),
  ticketsGroups: document.getElementById("ticketsGroups"),
  nodeDetails: document.getElementById("nodeDetails"),
  networkLegend: document.getElementById("networkLegend"),
  networkSkeleton: document.getElementById("networkSkeleton"),
  networkEmptyState: document.getElementById("networkEmptyState"),
  networkMobileSummary: document.getElementById("networkMobileSummary"),
  networkGraph: document.getElementById("networkGraph"),
  kpiTotalActive: document.getElementById("kpiTotalActive"),
  kpiOpenBugs: document.getElementById("kpiOpenBugs"),
  kpiStale: document.getElementById("kpiStale"),
  kpiFilteredTotal: document.getElementById("kpiFilteredTotal"),
  teamsGrid: document.getElementById("teamsGrid"),
  teamDetailTitle: document.getElementById("teamDetailTitle"),
  teamDetailTabs: document.getElementById("teamDetailTabs"),
  teamDetailSkeleton: document.getElementById("teamDetailSkeleton"),
  teamAssignedPanel: document.getElementById("teamAssignedPanel"),
  teamWorkDonePanel: document.getElementById("teamWorkDonePanel"),
  teamReportedPanel: document.getElementById("teamReportedPanel"),
  teamTimelinePanel: document.getElementById("teamTimelinePanel"),
  infocommWebsiteUrl: document.getElementById("infocommWebsiteUrl"),
  infocommScheduleTitle: document.getElementById("infocommScheduleTitle"),
  infocommSkeleton: document.getElementById("infocommSkeleton"),
  infocommDateTabs: document.getElementById("infocommDateTabs"),
  infocommScheduleList: document.getElementById("infocommScheduleList"),
};

function syncSidebarDisclosure() {
  if (!el.dashboardShell || !el.toggleSidebarBtn) {
    return;
  }

  const isCollapsed = Boolean(state.ui.sidebarCollapsed);
  el.dashboardShell.classList.toggle("sidebar-collapsed", isCollapsed);
  el.toggleSidebarBtn.setAttribute("aria-expanded", String(!isCollapsed));
  el.toggleSidebarBtn.setAttribute("aria-label", isCollapsed ? "Expand sidebar" : "Collapse sidebar");

  const label = el.toggleSidebarBtn.querySelector(".sidebar-toggle-label");
  if (label) {
    label.textContent = isCollapsed ? "Expand sidebar" : "Collapse sidebar";
  }
}

function formatSyncTimestamp(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZoneName: "short",
  }).format(date);
}

function updateLastUpdatedText(rawValue) {
  if (!el.lastUpdatedText) {
    return;
  }
  el.lastUpdatedText.textContent = `Last update: ${formatSyncTimestamp(rawValue)}`;
}

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

function parseTeamQuery(params) {
  return uniqueValues(params.getAll("team"));
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
  const teams = state.filters.teams;
  const statuses = state.filters.statuses;
  const assignees = state.filters.assignees;
  const excludedStatuses = state.filters.excludedStatuses;
  const excludedAssignees = state.filters.excludedAssignees;

  const teamParts = [];
  if (teams.length) {
    teamParts.push(`${teams.length} selected: ${teams.slice(0, 2).join(", ")}${teams.length > 2 ? "..." : ""}`);
  }
  el.teamSummary.textContent = teamParts.length ? teamParts.join(" | ") : "All teams";

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
  for (const team of state.filters.teams) {
    params.append("team", team);
  }
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
  state.filters.teams = parseTeamQuery(params);
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
  setSelectedValues(el.teamSelect, state.filters.teams);
  setSelectedValues(el.statusSelect, state.filters.statuses);
  setSelectedValues(el.assigneeSelect, state.filters.assignees);
  updateFilterSummaries();
}

function buildTicketsQuery() {
  const params = new URLSearchParams();
  if (state.filters.search) params.set("search", state.filters.search);
  for (const team of state.filters.teams) {
    params.append("team", team);
  }
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
  for (const team of state.filters.teams) {
    params.append("team", team);
  }
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
  state.filters.teams = uniqueValues(getSelectedValues(el.teamSelect));
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
    updateLastUpdatedText(null);
    return;
  }

  const runtime = state.sync.runtime || {};
  const persisted = state.sync.persisted || {};
  const run = persisted.last_run || null;

  el.syncChip.className = "sync-chip";

  if (runtime.last_error) {
    el.syncChip.textContent = `Sync status: error (${runtime.last_error})`;
    el.syncChip.classList.add("error");
    updateLastUpdatedText(runtime.started_at || run?.completed_at || run?.started_at || null);
    return;
  }

  if (runtime.is_running) {
    const trigger = runtime.trigger || "unknown";
    el.syncChip.textContent = `Sync status: running (${trigger})`;
    el.syncChip.classList.add("running");
    updateLastUpdatedText(runtime.started_at || run?.completed_at || run?.started_at || null);
    return;
  }

  if (run && run.started_at) {
    const completedAt = run.completed_at || run.started_at;
    el.syncChip.textContent = `Sync status: last ${run.status || "unknown"} (${formatSyncTimestamp(completedAt)})`;
    updateLastUpdatedText(completedAt);
    return;
  }

  el.syncChip.textContent = "Sync status: idle";
  updateLastUpdatedText(null);
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
    const memberSections = (group.members || []).map((memberGroup) => {
      const rows = (memberGroup.items || []).map((ticket) => {
        const issueUrl = jiraIssueUrl(ticket.ticket_key || "");
        return `<tr>
          <td>${escapeHtml(ticket.ticket_key)}</td>
          <td>${escapeHtml(ticket.summary)}</td>
          <td>${escapeHtml(ticket.status)}</td>
          <td>${escapeHtml(ticket.priority)}</td>
          <td><a class="jira-link" href="${issueUrl}" target="_blank" rel="noopener noreferrer">Open</a></td>
        </tr>`;
      });

      return `<section class="ticket-member-group">
        <h5>${escapeHtml(memberGroup.member_name || memberGroup.assignee || "Unassigned")} <span class="ticket-group-count">(${memberGroup.count || 0})</span></h5>
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

    const metrics = group.metrics || {
      total: group.total_tickets || 0,
      in_progress: group.in_progress_tickets || 0,
      blocked: group.blocked_tickets || 0,
    };

    return `<details class="ticket-group" open>
      <summary>
        <strong>${escapeHtml(group.team_name || "Unmapped Team")}</strong>
        <span class="ticket-group-badge">Total: ${metrics.total || 0} Tickets | ${metrics.in_progress || 0} In Progress | ${metrics.blocked || 0} Blocked</span>
      </summary>
      <div class="ticket-member-list">${memberSections.join("")}</div>
    </details>`;
  });

  el.ticketsGroups.innerHTML = sections.join("");
}

function renderTeamsWorkspace() {
  const payload = state.teamsWorkspace || { teams: [] };
  const teams = Array.isArray(payload.teams) ? payload.teams : [];
  if (!teams.length) {
    el.teamsGrid.innerHTML = "<p class='muted'>No team data available in cache.</p>";
    return;
  }

  const cards = teams.map((team) => {
    const members = Array.isArray(team.members) ? team.members : [];
    const memberLinks = members.map((member) => {
      const profileUrl = String(member.profile_url || "").trim();
      const label = escapeHtml(member.display_name || "Unknown Member");
      if (!profileUrl) {
        return `<li>${label}</li>`;
      }
      return `<li><a class="jira-link" href="${profileUrl}" target="_blank" rel="noopener noreferrer">${label} <span class="external-icon" aria-hidden="true">&#8599;</span></a></li>`;
    });

    return `<article class="team-card ${state.selectedTeamId === team.team_id ? "is-selected" : ""}" data-team-id="${escapeHtml(team.team_id)}">
      <header>
        <h4>${escapeHtml(team.display_name || team.team_name || "Unnamed Team")}</h4>
        <p class="muted">${escapeHtml(team.description || "")}</p>
      </header>
      <ul>${memberLinks.join("")}</ul>
    </article>`;
  });

  el.teamsGrid.innerHTML = cards.join("");

  const selectableCards = el.teamsGrid.querySelectorAll(".team-card");
  for (const card of selectableCards) {
    card.addEventListener("click", async () => {
      state.selectedTeamId = String(card.getAttribute("data-team-id") || "").trim();
      renderTeamsWorkspace();
      await loadSelectedTeamDetail();
    });
  }
}

function setActiveTeamTab(tabKey) {
  state.selectedTeamTab = tabKey;
  const tabs = document.querySelectorAll(".team-tab");
  for (const tab of tabs) {
    tab.classList.toggle("is-active", tab.dataset.teamTab === tabKey);
  }

  const panelMap = {
    assigned: el.teamAssignedPanel,
    work_done: el.teamWorkDonePanel,
    reported: el.teamReportedPanel,
    timeline: el.teamTimelinePanel,
  };
  for (const [key, panel] of Object.entries(panelMap)) {
    panel.classList.toggle("is-active", key === tabKey);
  }
}

function renderTeamDetailPanels() {
  const detail = state.teamDetail;
  if (!detail) {
    el.teamDetailTitle.textContent = "Team Details";
    el.teamAssignedPanel.innerHTML = "<p class='muted'>Select a team to view assigned tickets.</p>";
    el.teamWorkDonePanel.innerHTML = "<p class='muted'>Select a team to view completed work.</p>";
    el.teamReportedPanel.innerHTML = "<p class='muted'>Select a team to view reported tickets.</p>";
    el.teamTimelinePanel.innerHTML = "<p class='muted'>Select a team to view timeline.</p>";
    return;
  }

  const team = detail.team || {};
  el.teamDetailTitle.textContent = `${team.display_name || team.team_name || "Team"} Details`;

  const assigned = detail.tickets_assigned || {};
  const assignedItems = Array.isArray(assigned.items) ? assigned.items : [];
  const assignedRows = assignedItems.map((item) => `<li>${escapeHtml(item.ticket_key)} - ${escapeHtml(item.summary || "No summary")} (${escapeHtml(item.status || "Unknown")})</li>`);
  const assignedMetrics = assigned.metrics || {};
  el.teamAssignedPanel.innerHTML = `
    <div class="team-metrics-row">
      <span class="metric-pill">Total: ${assignedMetrics.total || 0}</span>
      <span class="metric-pill">In Progress: ${assignedMetrics.in_progress || 0}</span>
      <span class="metric-pill">Blocked: ${assignedMetrics.blocked || 0}</span>
    </div>
    <ul>${assignedRows.join("") || "<li class='muted'>No assigned tickets.</li>"}</ul>
  `;

  const workDoneItems = Array.isArray(detail.work_done?.items) ? detail.work_done.items : [];
  el.teamWorkDonePanel.innerHTML = `<ul>${workDoneItems.map((item) => `<li>${escapeHtml(item.ticket_key)} - ${escapeHtml(item.summary || "No summary")}</li>`).join("") || "<li class='muted'>No completed/resolved tickets.</li>"}</ul>`;

  const reportedItems = Array.isArray(detail.tickets_reported?.items) ? detail.tickets_reported.items : [];
  el.teamReportedPanel.innerHTML = `<ul class="reported-list">${reportedItems.map((item) => `<li>${escapeHtml(item.ticket_key)} - ${escapeHtml(item.summary || "No summary")} <span class="reported-pill">Reported By Team</span></li>`).join("") || "<li class='muted'>No reported tickets.</li>"}</ul>`;

  const timeline = detail.timeline || { todo: 0, in_progress: 0, done: 0, total: 0 };
  const total = Number(timeline.total || (timeline.todo || 0) + (timeline.in_progress || 0) + (timeline.done || 0));
  const toPct = (value) => (total > 0 ? Math.round((Number(value || 0) / total) * 100) : 0);
  el.teamTimelinePanel.innerHTML = `
    <div class="timeline-lane"><span>To Do (${timeline.todo || 0})</span><div class="timeline-bar todo" style="width:${toPct(timeline.todo)}%"></div></div>
    <div class="timeline-lane"><span>In Progress (${timeline.in_progress || 0})</span><div class="timeline-bar in-progress" style="width:${toPct(timeline.in_progress)}%"></div></div>
    <div class="timeline-lane"><span>Done (${timeline.done || 0})</span><div class="timeline-bar done" style="width:${toPct(timeline.done)}%"></div></div>
  `;
}

async function loadSelectedTeamDetail() {
  if (!state.selectedTeamId) {
    state.teamDetail = null;
    renderTeamDetailPanels();
    return;
  }

  state.teamDetailLoading = true;
  el.teamDetailSkeleton.classList.add("is-visible");
  try {
    state.teamDetail = await apiGet(buildSharedFilterQuery(`/api/teams/${encodeURIComponent(state.selectedTeamId)}`));
  } catch (_error) {
    state.teamDetail = null;
  } finally {
    state.teamDetailLoading = false;
    el.teamDetailSkeleton.classList.remove("is-visible");
    renderTeamDetailPanels();
    setActiveTeamTab(state.selectedTeamTab);
  }
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
  const teamScrollTop = el.teamSelect.scrollTop;
  const statusScrollTop = el.statusSelect.scrollTop;
  const assigneeScrollTop = el.assigneeSelect.scrollTop;
  const teams = Array.isArray(state.filterOptions.teams) ? state.filterOptions.teams : [];
  const statuses = Array.isArray(state.filterOptions.statuses) ? state.filterOptions.statuses : [];
  const assignees = Array.isArray(state.filterOptions.assignees) ? state.filterOptions.assignees : [];

  setSelectOptions(el.teamSelect, teams);
  setSelectOptions(el.statusSelect, statuses);
  setSelectOptions(el.assigneeSelect, assignees);
  syncInputsFromState();
  refreshExcludeStyles();
  restoreSelectScroll(el.teamSelect, teamScrollTop);
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
  if (el.networkSkeleton) {
    el.networkSkeleton.classList.add("is-visible");
  }
  const [metricsResult, ticketsResult, networkResult, teamsWorkspaceResult] = await Promise.allSettled([
    apiGet(buildSharedFilterQuery("/api/metrics")),
    apiGet(buildTicketsQuery()),
    apiGet(buildSharedFilterQuery("/api/network")),
    apiGet("/api/teams"),
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
    teams: Array.isArray(ticketsPayload.filter_options?.teams) ? ticketsPayload.filter_options.teams : [],
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

  if (teamsWorkspaceResult.status === "fulfilled") {
    state.teamsWorkspace = teamsWorkspaceResult.value;
    if (!state.selectedTeamId) {
      const teams = Array.isArray(state.teamsWorkspace?.teams) ? state.teamsWorkspace.teams : [];
      state.selectedTeamId = String(teams[0]?.team_id || "").trim();
    }
  } else {
    state.teamsWorkspace = { teams: [] };
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
  renderTeamsWorkspace();
  await loadSelectedTeamDetail();
  if (el.networkSkeleton) {
    el.networkSkeleton.classList.remove("is-visible");
  }
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
      if (tab.dataset.tab === "infocomm" && state.infocomm.schedule.length === 0) {
        loadInfoCommSchedule();
      }
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
  enableToggleMultiSelect(el.teamSelect);
  enableToggleMultiSelect(el.statusSelect, "statuses", "excludedStatuses");
  enableToggleMultiSelect(el.assigneeSelect, "assignees", "excludedAssignees");
  bindExcludeOnDoubleClick(el.statusSelect, "statuses", "excludedStatuses");
  bindExcludeOnDoubleClick(el.assigneeSelect, "assignees", "excludedAssignees");

  if (el.teamDetailTabs) {
    const teamTabs = el.teamDetailTabs.querySelectorAll(".team-tab");
    for (const tab of teamTabs) {
      tab.addEventListener("click", () => {
        setActiveTeamTab(String(tab.dataset.teamTab || "assigned"));
      });
    }
  }

  if (el.assigneeSelectAllBtn) {
    el.assigneeSelectAllBtn.addEventListener("click", () => {
      setSelectedValues(el.assigneeSelect, state.filterOptions.assignees || []);
      state.filters.assignees = uniqueValues(state.filterOptions.assignees || []);
      applyStateToQuery();
      updateFilterSummaries();
      refreshExcludeStyles();
    });
  }

  if (el.assigneeClearAllBtn) {
    el.assigneeClearAllBtn.addEventListener("click", () => {
      setSelectedValues(el.assigneeSelect, []);
      state.filters.assignees = [];
      applyStateToQuery();
      updateFilterSummaries();
      refreshExcludeStyles();
    });
  }

  el.applyFiltersBtn.addEventListener("click", async () => {
    updateFilterStateFromInputs();
    await loadDashboardData();
  });

  el.resetFiltersBtn.addEventListener("click", async () => {
    state.filters = {
      search: "",
      teams: [],
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
    if (window.innerWidth <= mobileBreakpoint && state.ui.sidebarCollapsed) {
      state.ui.sidebarCollapsed = false;
      syncSidebarDisclosure();
    }
    renderNetwork();
  });

  // InfoComm Show Selector buttons
  const showBtns = document.querySelectorAll(".infocomm-btn");
  for (const btn of showBtns) {
    btn.addEventListener("click", async () => {
      for (const b of showBtns) {
        b.classList.toggle("is-active", b.dataset.show === btn.dataset.show);
      }
      state.infocomm.selectedShow = btn.dataset.show;
      await loadInfoCommSchedule();
    });
  }
}

async function loadInfoCommSchedule() {
  state.infocomm.loading = true;
  if (el.infocommSkeleton) el.infocommSkeleton.classList.add("is-visible");
  if (el.infocommScheduleList) el.infocommScheduleList.innerHTML = "";
  if (el.infocommDateTabs) el.infocommDateTabs.innerHTML = "";
  
  try {
    const data = await apiGet(`/api/infocomm/schedule/${state.infocomm.selectedShow}`);
    state.infocomm.schedule = data;
    
    // Auto-select the first date from the schedule
    const dates = uniqueValues(data.map(item => item.date));
    if (dates.length > 0) {
      if (!dates.includes(state.infocomm.selectedDate)) {
        state.infocomm.selectedDate = dates[0];
      }
    } else {
      state.infocomm.selectedDate = "";
    }
    
    renderInfoCommUI();
  } catch (error) {
    console.error("Error loading InfoComm schedule:", error);
    if (el.infocommScheduleList) {
      el.infocommScheduleList.innerHTML = `<p class="error-msg text-danger">Failed to load schedule: ${escapeHtml(error.message || error)}</p>`;
    }
  } finally {
    state.infocomm.loading = false;
    if (el.infocommSkeleton) el.infocommSkeleton.classList.remove("is-visible");
  }
}

function renderInfoCommUI() {
  if (!el.infocommDateTabs || !el.infocommScheduleList) return;
  
  const showNameMap = {
    india: "InfoComm India",
    asia: "InfoComm Asia",
    global: "InfoComm Global",
  };
  const websiteMap = {
    india: "https://www.infocomm-india.com/",
    asia: "https://www.infocomm-asia.com/",
    global: "https://www.infocommshow.org/",
  };
  
  // Update website link
  if (el.infocommWebsiteUrl) {
    el.infocommWebsiteUrl.href = websiteMap[state.infocomm.selectedShow];
    el.infocommWebsiteUrl.textContent = `Visit Official ${showNameMap[state.infocomm.selectedShow]} Website`;
  }
  
  // Render Date Tabs
  const dates = uniqueValues(state.infocomm.schedule.map(item => item.date));
  el.infocommDateTabs.innerHTML = dates.map(date => {
    const isActive = date === state.infocomm.selectedDate ? "is-active" : "";
    return `<button class="infocomm-date-tab ${isActive}" data-date="${escapeHtml(date)}" type="button">${escapeHtml(date)}</button>`;
  }).join("");
  
  // Add listeners to date tabs
  const dateButtons = el.infocommDateTabs.querySelectorAll(".infocomm-date-tab");
  for (const btn of dateButtons) {
    btn.addEventListener("click", () => {
      state.infocomm.selectedDate = btn.dataset.date;
      renderInfoCommUI();
    });
  }
  
  // Render Session Cards for selected date
  const filteredSessions = state.infocomm.schedule.filter(item => item.date === state.infocomm.selectedDate);
  if (filteredSessions.length === 0) {
    el.infocommScheduleList.innerHTML = '<p class="muted">No sessions scheduled for this date.</p>';
    return;
  }
  
  el.infocommScheduleList.innerHTML = `
    <div class="infocomm-sessions-feed">
      ${filteredSessions.map(session => {
        const titleHtml = session.link 
          ? `<a href="${escapeHtml(session.link)}" target="_blank">${escapeHtml(session.title)} <span class="external-icon">&#10138;</span></a>`
          : escapeHtml(session.title);
          
        const locationHtml = session.location
          ? `<span class="session-badge location">&#128205; ${escapeHtml(session.location)}</span>`
          : "";
          
        const durationHtml = session.duration
          ? `<span class="session-badge duration">&#9201; ${escapeHtml(session.duration)}</span>`
          : "";
          
        const descHtml = session.description
          ? `<p class="infocomm-session-desc">${escapeHtml(session.description)}</p>`
          : "";
          
        return `
          <article class="infocomm-session-card">
            <div class="infocomm-session-header">
              <h4 class="infocomm-session-title">${titleHtml}</h4>
            </div>
            <div class="infocomm-session-meta">
              ${durationHtml}
              ${locationHtml}
            </div>
            ${descHtml}
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function bindSidebarToggle() {
  if (!el.toggleSidebarBtn) {
    return;
  }

  syncSidebarDisclosure();
  el.toggleSidebarBtn.addEventListener("click", () => {
    state.ui.sidebarCollapsed = !state.ui.sidebarCollapsed;
    syncSidebarDisclosure();
  });
}

async function bootstrap() {
  readStateFromQuery();
  bindTabNavigation();
  bindSidebarToggle();
  bindFilterDisclosure();
  bindActions();
  await loadSyncStatus();
  await loadDashboardData();
  syncInputsFromState();
  setInterval(loadSyncStatus, pollIntervalMs);
}

bootstrap();
