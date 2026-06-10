const state = {
  activeTab: "overview",
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
  teamsWorkspace: null,
  teamWorkspaceSearch: "",
  selectedTeamId: "",
  teamDetail: null,
  jiraDomain: "qsc.atlassian.net",
  charts: {},
  infocomm: {
    selectedShow: "india",
    selectedDate: "",
    schedule: [],
    loading: false,
  },
  release: {
    rows: [],
    loading: false,
    error: "",
    loadedOnce: false,
    editMode: false,
    selectedRowIds: [],
    relationshipData: {},
    relationshipForm: {
      dependsSearch: "",
      coReleasesSearch: "",
      dependsOnSelected: [],
      coReleasesSelected: [],
    },
    filters: {
      nameQuery: "",
      status: "",
    },
    sort: {
      columnKey: "",
      direction: "none",
    },
    graph: {
      visible: false,
      statusFilter: ["Released", "Planned", "Archived", "Overdue"],
      instance: null,
    },
  },
  ui: {
    advancedFiltersOpen: true,
    sidebarCollapsed: false,
  },
};

const pollIntervalMs = 15000;
const mobileBreakpoint = 768;

const el = {
  dashboardShell: document.querySelector(".dashboard-shell"),
  controlToolbar: document.querySelector(".control-toolbar"),
  toolbarLeft: document.querySelector(".control-toolbar .toolbar-left"),
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
  kpiTotalActive: document.getElementById("kpiTotalActive"),
  kpiOpenBugs: document.getElementById("kpiOpenBugs"),
  kpiStale: document.getElementById("kpiStale"),
  kpiFilteredTotal: document.getElementById("kpiFilteredTotal"),
  teamsGrid: document.getElementById("teamsGrid"),
  teamWorkspaceSearchInput: document.getElementById("teamWorkspaceSearchInput"),
  teamDetailTitle: document.getElementById("teamDetailTitle"),
  teamDetailSkeleton: document.getElementById("teamDetailSkeleton"),
  teamDetailContent: document.getElementById("teamDetailContent"),
  infocommWebsiteUrl: document.getElementById("infocommWebsiteUrl"),
  infocommScheduleTitle: document.getElementById("infocommScheduleTitle"),
  infocommSkeleton: document.getElementById("infocommSkeleton"),
  infocommDateTabs: document.getElementById("infocommDateTabs"),
  infocommScheduleList: document.getElementById("infocommScheduleList"),
  releasePanelState: document.getElementById("releasePanelState"),
  releaseRelationshipControls: document.getElementById("releaseRelationshipControls"),
  releaseRelationshipFeedback: document.getElementById("releaseRelationshipFeedback"),
  releaseDependsSelectedList: document.getElementById("releaseDependsSelectedList"),
  releaseDependsSearchInput: document.getElementById("releaseDependsSearchInput"),
  releaseDependsSuggestions: document.getElementById("releaseDependsSuggestions"),
  releaseCoreleasesSelectedList: document.getElementById("releaseCoreleasesSelectedList"),
  releaseCoreleasesSearchInput: document.getElementById("releaseCoreleasesSearchInput"),
  releaseCoreleasesSuggestions: document.getElementById("releaseCoreleasesSuggestions"),
  releaseEditToggleBtn: document.getElementById("releaseEditToggleBtn"),
  releaseApplyRelationshipsBtn: document.getElementById("releaseApplyRelationshipsBtn"),
  releaseGraphToggleBtn: document.getElementById("releaseGraphToggleBtn"),
  releaseTableFiltersWrap: document.getElementById("releaseTableFiltersWrap"),
  releaseNameFilterInput: document.getElementById("releaseNameFilterInput"),
  releaseStatusFilterSelect: document.getElementById("releaseStatusFilterSelect"),
  releaseClearFiltersBtn: document.getElementById("releaseClearFiltersBtn"),
  releaseSelectAllCheckbox: document.getElementById("releaseSelectAllCheckbox"),
  releaseTableWrap: document.getElementById("releaseTableWrap"),
  releaseTableBody: document.getElementById("releaseTableBody"),
  releaseGraphPanel: document.getElementById("releaseGraphPanel"),
  releaseGraphStatusFilter: document.getElementById("releaseGraphStatusFilter"),
  releaseGraphCanvas: document.getElementById("releaseGraphCanvas"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  globalLoadingIndicator: document.getElementById("globalLoadingIndicator"),
};

const loadingUiState = {
  activeRequests: 0,
  revealTimer: null,
  hideTimer: null,
  visibleSince: 0,
};

const loadingRevealDelayMs = 120;
const loadingMinVisibleMs = 220;

function setGlobalLoadingVisible(visible) {
  if (!el.globalLoadingIndicator) {
    return;
  }
  el.globalLoadingIndicator.classList.toggle("is-visible", visible);
  el.globalLoadingIndicator.setAttribute("aria-hidden", String(!visible));
}

function beginGlobalLoading() {
  loadingUiState.activeRequests += 1;
  if (loadingUiState.activeRequests !== 1) {
    return;
  }

  if (loadingUiState.hideTimer) {
    clearTimeout(loadingUiState.hideTimer);
    loadingUiState.hideTimer = null;
  }

  loadingUiState.revealTimer = setTimeout(() => {
    loadingUiState.revealTimer = null;
    if (loadingUiState.activeRequests > 0) {
      loadingUiState.visibleSince = Date.now();
      setGlobalLoadingVisible(true);
    }
  }, loadingRevealDelayMs);
}

function endGlobalLoading() {
  loadingUiState.activeRequests = Math.max(0, loadingUiState.activeRequests - 1);
  if (loadingUiState.activeRequests > 0) {
    return;
  }

  if (loadingUiState.revealTimer) {
    clearTimeout(loadingUiState.revealTimer);
    loadingUiState.revealTimer = null;
  }

  const elapsed = Date.now() - loadingUiState.visibleSince;
  const remainingVisibleMs = Math.max(0, loadingMinVisibleMs - elapsed);
  if (loadingUiState.hideTimer) {
    clearTimeout(loadingUiState.hideTimer);
  }
  loadingUiState.hideTimer = setTimeout(() => {
    loadingUiState.hideTimer = null;
    setGlobalLoadingVisible(false);
  }, remainingVisibleMs);
}

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
  const label = isOpen ? "Hide filters" : "Advanced filters";
  el.toggleAdvancedFiltersBtn.setAttribute("aria-expanded", String(isOpen));
  // Rebuild button contents preserving the icon
  el.toggleAdvancedFiltersBtn.innerHTML = `<i data-lucide="sliders-horizontal" class="btn-icon-left" aria-hidden="true"></i><span>${label}</span>`;
  if (window.lucide) window.lucide.createIcons();
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

function shouldHideFilterControlsForTab(tabName) {
  return tabName === "teams" || tabName === "infocomm" || tabName === "release";
}

function syncFilterControlsVisibility(tabName) {
  const hideFilters = shouldHideFilterControlsForTab(tabName);
  if (el.controlToolbar) {
    if (hideFilters) {
      el.controlToolbar.classList.remove("control-toolbar", "panel");
    } else {
      el.controlToolbar.classList.add("control-toolbar", "panel");
    }
    el.controlToolbar.hidden = hideFilters;
  }

  if (el.toolbarLeft) {
    el.toolbarLeft.hidden = hideFilters;
  }

  if (!el.advancedFilters) {
    return;
  }

  if (hideFilters) {
    el.advancedFilters.classList.add("is-collapsed");
    el.advancedFilters.hidden = true;
    return;
  }

  syncAdvancedFiltersDisclosure();
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

  const members = Array.from(grouped.entries())
    .map(([assignee, items]) => ({ member_name: assignee, assignee, count: items.length, items }))
    .sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return left.assignee.localeCompare(right.assignee);
    });

  const total = members.reduce((sum, member) => sum + Number(member.count || 0), 0);
  return [{
    team_id: "unmapped-team",
    team_name: "Unmapped Team",
    metrics: { total, in_progress: 0, blocked: 0 },
    members,
  }];
}

async function apiGet(path, options = {}) {
  const trackLoading = options.trackLoading !== false;
  if (trackLoading) {
    beginGlobalLoading();
  }
  try {
    const response = await fetch(path, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  } finally {
    if (trackLoading) {
      endGlobalLoading();
    }
  }
}

async function apiPost(path, options = {}) {
  const trackLoading = options.trackLoading !== false;
  if (trackLoading) {
    beginGlobalLoading();
  }
  try {
    const response = await fetch(path, { method: "POST", headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  } finally {
    if (trackLoading) {
      endGlobalLoading();
    }
  }
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

function renderPriorityChart() {
  const byPriority = new Map();
  for (const ticket of state.tickets) {
    const key = String(ticket.priority || "Unspecified").trim() || "Unspecified";
    byPriority.set(key, (byPriority.get(key) || 0) + 1);
  }

  const rows = Array.from(byPriority.entries()).sort((left, right) => right[1] - left[1]);
  if (!rows.length) {
    rows.push(["No tickets", 1]);
  }

  const hasRealData = rows.length > 0 && rows[0][0] !== "No tickets";
  makeChart("priorityChart", {
    type: "doughnut",
    data: {
      labels: rows.map((row) => row[0]),
      datasets: [{
        data: rows.map((row) => row[1]),
        backgroundColor: hasRealData
          ? ["#ef4444", "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6", "#14b8a6"]
          : ["rgba(156, 163, 175, 0.5)"],
      }],
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: { enabled: hasRealData },
      },
    },
  }, "priority");
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
      </summary>
      <div class="ticket-member-list">${memberSections.join("")}</div>
    </details>`;
  });

  el.ticketsGroups.innerHTML = sections.join("");
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function renderTeamsWorkspace() {
  const payload = state.teamsWorkspace || { teams: [] };
  const teams = Array.isArray(payload.teams) ? payload.teams : [];
  const searchTerm = String(state.teamWorkspaceSearch || "").trim().toLowerCase();
  const filteredTeams = teams.filter((team) => {
    if (!searchTerm) {
      return true;
    }
    const teamName = String(team.display_name || team.team_name || "").toLowerCase();
    const description = String(team.description || "").toLowerCase();
    return teamName.includes(searchTerm) || description.includes(searchTerm);
  });

  if (!teams.length) {
    el.teamsGrid.innerHTML = "<p class='muted'>No team data available in cache.</p>";
    return;
  }

  if (!filteredTeams.length) {
    el.teamsGrid.innerHTML = "<p class='muted'>No teams match your search.</p>";
    return;
  }

  const cards = filteredTeams.map((team) => {
    const teamDisplayName = team.display_name || team.team_name || "Unnamed Team";

    return `<article class="team-card ${state.selectedTeamId === team.team_id ? "is-selected" : ""}" data-team-id="${escapeHtml(team.team_id)}">
      <header>
        <h4>${escapeHtml(teamDisplayName)}</h4>
      </header>
    </article>`;
  });

  el.teamsGrid.innerHTML = cards.join("");

  const selectableCards = el.teamsGrid.querySelectorAll(".team-card");
  for (const card of selectableCards) {
    card.addEventListener("click", () => {
      state.selectedTeamId = String(card.getAttribute("data-team-id") || "").trim();
      state.teamDetail = null;
      renderTeamsWorkspace();
      renderTeamDetailPanels();
    });
  }

  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function renderTeamDetailPanels() {
  const teams = Array.isArray(state.teamsWorkspace?.teams) ? state.teamsWorkspace.teams : [];
  const selectedTeam = teams.find((team) => String(team.team_id || "").trim() === state.selectedTeamId) || null;

  if (!selectedTeam) {
    el.teamDetailTitle.textContent = "Team Details";
    if (el.teamDetailContent) {
      el.teamDetailContent.innerHTML = "<p class='muted'>Select a team to view details and members.</p>";
    }
    return;
  }

  const teamName = `${selectedTeam.display_name || selectedTeam.team_name || "Team"}`;
  const members = Array.isArray(selectedTeam.members) ? selectedTeam.members : [];

  el.teamDetailTitle.textContent = `${teamName} Details`;

  const memberRows = members.map((member) => {
    const label = escapeHtml(member.display_name || "Unknown Member");
    const role = escapeHtml(member.role || "-");
    const skillset = escapeHtml(member.skillset || "-");
    const location = escapeHtml(member.location || "-");
    const contractor = escapeHtml(member.contractor || "-");
    const notes = escapeHtml(member.notes || "-");

    return `<tr>
      <td>${label}</td>
      <td>${role}</td>
      <td>${skillset}</td>
      <td>${location}</td>
      <td>${contractor}</td>
      <td>${notes}</td>
    </tr>`;
  });

  const uniqueLocations = Array.from(
    new Set(
      members
        .map((member) => String(member.location || "").trim())
        .filter(Boolean)
    )
  );
  const uniqueContractors = Array.from(
    new Set(
      members
        .map((member) => String(member.contractor || "").trim())
        .filter(Boolean)
    )
  );

  if (el.teamDetailContent) {
    el.teamDetailContent.innerHTML = `
      <div class="team-meta-row muted">
        <span><strong>Members:</strong> ${members.length}</span>
        <span><strong>Locations:</strong> ${escapeHtml(uniqueLocations.join(", ") || "-")}</span>
        <span><strong>Contractors:</strong> ${escapeHtml(uniqueContractors.join(", ") || "-")}</span>
      </div>
      <h4>Team Members</h4>
      ${memberRows.length
        ? `<div class="table-wrap team-member-table-wrap">
            <table class="team-member-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Skillset</th>
                  <th>Location</th>
                  <th>Contractor</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>${memberRows.join("")}</tbody>
            </table>
          </div>`
        : "<p class='muted'>No team members available.</p>"}
    `;
  }
}

const RELEASE_RELATIONSHIPS_STORAGE_KEY = "release.relationships.v1";

function formatReleaseDate(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

function parseReleaseDateMillis(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return null;
  }

  const directParse = Date.parse(value);
  if (Number.isFinite(directParse)) {
    return directParse;
  }

  const simpleMatch = value.match(/^(\d{1,2})\/([A-Za-z]{3})\/(\d{2,4})$/);
  if (!simpleMatch) {
    return null;
  }

  const day = Number(simpleMatch[1]);
  const monthToken = simpleMatch[2].toLowerCase();
  let year = Number(simpleMatch[3]);
  const monthLookup = {
    jan: 0,
    feb: 1,
    mar: 2,
    apr: 3,
    may: 4,
    jun: 5,
    jul: 6,
    aug: 7,
    sep: 8,
    oct: 9,
    nov: 10,
    dec: 11,
  };
  if (!(monthToken in monthLookup)) {
    return null;
  }
  if (year < 100) {
    year += 2000;
  }

  const utcMillis = Date.UTC(year, monthLookup[monthToken], day);
  if (!Number.isFinite(utcMillis)) {
    return null;
  }

  return utcMillis;
}

function cycleSortDirection(currentDirection, isSameColumn) {
  if (!isSameColumn) {
    return "asc";
  }
  if (currentDirection === "asc") {
    return "desc";
  }
  if (currentDirection === "desc") {
    return "none";
  }
  return "asc";
}

function compareReleaseTextValues(leftValue, rightValue) {
  return String(leftValue || "").localeCompare(String(rightValue || ""), undefined, {
    sensitivity: "base",
    numeric: true,
  });
}

function compareReleaseRows(leftRow, rightRow, columnKey) {
  if (columnKey === "releaseDate") {
    const leftMillis = parseReleaseDateMillis(leftRow.releaseDate);
    const rightMillis = parseReleaseDateMillis(rightRow.releaseDate);
    if (leftMillis !== null && rightMillis !== null && leftMillis !== rightMillis) {
      return leftMillis - rightMillis;
    }
    if (leftMillis === null && rightMillis !== null) {
      return 1;
    }
    if (leftMillis !== null && rightMillis === null) {
      return -1;
    }
  }
  return compareReleaseTextValues(leftRow[columnKey], rightRow[columnKey]);
}

function getSortedReleaseRows(rowsInput) {
  const rows = Array.isArray(rowsInput) ? rowsInput : [];
  const sortState = state.release.sort || { columnKey: "", direction: "none" };
  const columnKey = String(sortState.columnKey || "");
  const direction = String(sortState.direction || "none");

  if (!columnKey || direction === "none") {
    return rows;
  }

  const multiplier = direction === "desc" ? -1 : 1;
  return rows
    .map((row, index) => ({ row, index }))
    .sort((left, right) => {
      const valueCompare = compareReleaseRows(left.row, right.row, columnKey) * multiplier;
      if (valueCompare !== 0) {
        return valueCompare;
      }
      return left.index - right.index;
    })
    .map((entry) => entry.row);
}

function computeReleaseStatus(release) {
  if (release.released === true) {
    return "Released";
  }
  if (release.archived === true) {
    return "Archived";
  }
  if (release.overdue === true) {
    return "Overdue";
  }
  return "Planned";
}

function normalizeReleaseRows(payload) {
  const records = Array.isArray(payload?.releases) ? payload.releases : [];
  return records
    .map((release) => {
      const id = String(release?.id || release?.releaseId || release?.name || "").trim();
      if (!id) {
        return null;
      }
      const name = String(release?.name || release?.releaseName || id).trim() || "Untitled release";
      const releaseDate = String(release?.releaseDate || release?.userReleaseDate || "").trim();
      return {
        id,
        name,
        releaseDate,
        status: computeReleaseStatus(release),
      };
    })
    .filter(Boolean);
}

function getReleaseRowByIdMap() {
  const map = new Map();
  for (const row of state.release.rows || []) {
    map.set(String(row.id), row);
  }
  return map;
}

function getValidReleaseIdsSet() {
  return new Set((state.release.rows || []).map((row) => String(row.id || "")).filter(Boolean));
}

function createEmptyReleaseRelationshipEntry() {
  return {
    depends_on: [],
    co_releases: [],
  };
}

function normalizeReleaseRelationshipMap(rawMap, validIdsSet) {
  const map = rawMap && typeof rawMap === "object" ? rawMap : {};
  const validIds = Array.from(validIdsSet || []);
  const normalized = {};

  for (const id of validIds) {
    const entry = map[id] && typeof map[id] === "object" ? map[id] : createEmptyReleaseRelationshipEntry();
    const depends = uniqueValues(Array.isArray(entry.depends_on) ? entry.depends_on : [])
      .filter((targetId) => targetId !== id && validIdsSet.has(targetId));
    const coReleases = uniqueValues(Array.isArray(entry.co_releases) ? entry.co_releases : [])
      .filter((targetId) => targetId !== id && validIdsSet.has(targetId));

    normalized[id] = {
      depends_on: depends,
      co_releases: coReleases,
    };
  }

  // Enforce bidirectional co-release relationships.
  for (const id of validIds) {
    for (const peerId of normalized[id].co_releases) {
      if (!normalized[peerId]) {
        normalized[peerId] = createEmptyReleaseRelationshipEntry();
      }
      if (!normalized[peerId].co_releases.includes(id)) {
        normalized[peerId].co_releases.push(id);
      }
    }
  }

  for (const id of Object.keys(normalized)) {
    normalized[id].depends_on = uniqueValues(normalized[id].depends_on)
      .filter((targetId) => targetId !== id && validIdsSet.has(targetId))
      .sort(compareReleaseTextValues);
    normalized[id].co_releases = uniqueValues(normalized[id].co_releases)
      .filter((targetId) => targetId !== id && validIdsSet.has(targetId))
      .sort(compareReleaseTextValues);
  }

  return normalized;
}

function saveReleaseRelationshipsToLocalJson(relationshipMap) {
  try {
    localStorage.setItem(RELEASE_RELATIONSHIPS_STORAGE_KEY, JSON.stringify(relationshipMap || {}, null, 2));
  } catch (_error) {
    // Ignore storage write failures and continue with in-memory state.
  }
}

function loadReleaseRelationshipsFromLocalJson(validIdsSet) {
  try {
    const raw = localStorage.getItem(RELEASE_RELATIONSHIPS_STORAGE_KEY);
    if (!raw) {
      return normalizeReleaseRelationshipMap({}, validIdsSet);
    }
    const parsed = JSON.parse(raw);
    return normalizeReleaseRelationshipMap(parsed, validIdsSet);
  } catch (_error) {
    return normalizeReleaseRelationshipMap({}, validIdsSet);
  }
}

function scrubReleaseRelationshipsAgainstRows() {
  const validIdsSet = getValidReleaseIdsSet();
  state.release.relationshipData = normalizeReleaseRelationshipMap(state.release.relationshipData, validIdsSet);
  saveReleaseRelationshipsToLocalJson(state.release.relationshipData);
}

function setReleasePanelState(message, options = {}) {
  const tone = options.tone || "muted";

  if (el.releasePanelState) {
    el.releasePanelState.className = `release-panel-state ${tone}`;
    el.releasePanelState.textContent = message;
  }
}

function setReleaseRelationshipFeedback(message, tone = "muted") {
  if (!el.releaseRelationshipFeedback) {
    return;
  }
  el.releaseRelationshipFeedback.className = `release-relationship-feedback ${tone}`;
  el.releaseRelationshipFeedback.textContent = message;
}

function getReleaseStatusClass(statusValue) {
  const normalized = String(statusValue || "").trim().toLowerCase();
  if (normalized === "released") {
    return "release-status release-status-released";
  }
  if (normalized === "planned") {
    return "release-status release-status-planned";
  }
  if (normalized === "archived") {
    return "release-status release-status-archived";
  }
  if (normalized === "overdue") {
    return "release-status release-status-overdue";
  }
  return "release-status";
}

function getReleaseRelationshipLabel(row) {
  const status = String(row?.status || "").trim();
  const name = String(row?.name || row?.id || "Untitled release").trim();
  return status ? `${name} (${status})` : name;
}

function getReleaseFilteredRows(rowsInput) {
  const rows = Array.isArray(rowsInput) ? rowsInput : [];
  const nameQuery = String(state.release.filters?.nameQuery || "").trim().toLowerCase();
  const status = String(state.release.filters?.status || "").trim();

  return rows.filter((row) => {
    const nameMatches = !nameQuery || String(row.name || "").toLowerCase().includes(nameQuery);
    const statusMatches = !status || String(row.status || "") === status;
    return nameMatches && statusMatches;
  });
}

function getFilteredReleaseRows(rowsInput) {
  return getReleaseFilteredRows(rowsInput);
}

function getReleaseSelectedRowIdsSet() {
  return new Set((state.release.selectedRowIds || []).map((id) => String(id || "")).filter(Boolean));
}

function setReleaseSelectedRowsFromSet(selectedSet) {
  state.release.selectedRowIds = Array.from(selectedSet || []).sort(compareReleaseTextValues);
}

function toggleReleaseRowSelection(rowId, selected) {
  const selectedSet = getReleaseSelectedRowIdsSet();
  if (selected) {
    selectedSet.add(rowId);
  } else {
    selectedSet.delete(rowId);
  }
  setReleaseSelectedRowsFromSet(selectedSet);
}

function updateReleaseSelectAllCheckbox(displayRows) {
  if (!el.releaseSelectAllCheckbox) {
    return;
  }
  const selectedSet = getReleaseSelectedRowIdsSet();
  const rows = Array.isArray(displayRows) ? displayRows : [];
  if (!rows.length) {
    el.releaseSelectAllCheckbox.checked = false;
    el.releaseSelectAllCheckbox.indeterminate = false;
    return;
  }
  const selectedCount = rows.filter((row) => selectedSet.has(String(row.id))).length;
  el.releaseSelectAllCheckbox.checked = selectedCount > 0 && selectedCount === rows.length;
  el.releaseSelectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < rows.length;
}

function syncReleasePanelVisibility(hasRows) {
  const graphVisible = Boolean(state.release.graph.visible);
  const rowsAvailable = Boolean(hasRows);

  if (el.releaseGraphPanel) {
    el.releaseGraphPanel.hidden = !graphVisible;
  }
  if (el.releaseTableWrap) {
    el.releaseTableWrap.hidden = graphVisible || !rowsAvailable;
  }
  if (el.releaseTableFiltersWrap) {
    el.releaseTableFiltersWrap.hidden = graphVisible;
  }
  if (el.releaseRelationshipControls) {
    el.releaseRelationshipControls.hidden = graphVisible || !state.release.editMode;
  }
  if (el.releaseApplyRelationshipsBtn) {
    el.releaseApplyRelationshipsBtn.hidden = graphVisible || !state.release.editMode;
  }
  if (el.releaseEditToggleBtn) {
    el.releaseEditToggleBtn.textContent = state.release.editMode ? "Exit Edit" : "Edit: Off";
    el.releaseEditToggleBtn.classList.toggle("is-active", state.release.editMode);
  }
  if (el.releaseGraphToggleBtn) {
    el.releaseGraphToggleBtn.textContent = graphVisible ? "Hide Graph" : "Show Graph";
  }
  const selectHeader = document.querySelector("#release .release-select-col");
  if (selectHeader) {
    selectHeader.hidden = !state.release.editMode;
  }
}

function toggleSuggestionSelection(collectionKey, releaseId) {
  const values = uniqueValues(state.release.relationshipForm?.[collectionKey] || []);
  const valueSet = new Set(values);
  if (valueSet.has(releaseId)) {
    valueSet.delete(releaseId);
  } else {
    valueSet.add(releaseId);
  }
  state.release.relationshipForm[collectionKey] = Array.from(valueSet).sort(compareReleaseTextValues);
}

function buildReleaseSuggestionItems(rows, searchText, selectedIds) {
  const query = String(searchText || "").trim().toLowerCase();
  const selectedSet = new Set(uniqueValues(selectedIds || []));
  return rows
    .filter((row) => !selectedSet.has(String(row.id)))
    .filter((row) => !query || getReleaseRelationshipLabel(row).toLowerCase().includes(query))
    .map((row) => ({
      id: String(row.id),
      label: getReleaseRelationshipLabel(row),
      selected: false,
    }));
}

function buildReleaseSelectedItems(selectedIds) {
  const rowById = getReleaseRowByIdMap();
  return uniqueValues(selectedIds || [])
    .map((id) => rowById.get(String(id)))
    .filter(Boolean)
    .map((row) => ({
      id: String(row.id),
      label: getReleaseRelationshipLabel(row),
      selected: true,
    }));
}

function renderReleaseSelectedList(containerEl, items, onToggle) {
  if (!containerEl) {
    return;
  }
  if (!items.length) {
    containerEl.innerHTML = "<div class='release-suggestion-empty muted'>No releases selected.</div>";
    return;
  }
  containerEl.innerHTML = items
    .map((item) => `<button type="button" class="release-suggestion-item is-selected" data-release-id="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`)
    .join("");
  for (const button of containerEl.querySelectorAll(".release-suggestion-item")) {
    button.addEventListener("click", () => {
      const releaseId = String(button.getAttribute("data-release-id") || "").trim();
      if (!releaseId) {
        return;
      }
      onToggle(releaseId);
    });
  }
}

function renderReleaseSuggestionList(containerEl, items, onToggle) {
  if (!containerEl) {
    return;
  }
  if (!items.length) {
    containerEl.innerHTML = "<div class='release-suggestion-empty muted'>No matching releases.</div>";
    return;
  }
  containerEl.innerHTML = items
    .map((item) => `<button type="button" class="release-suggestion-item ${item.selected ? "is-selected" : ""}" data-release-id="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`)
    .join("");
  for (const button of containerEl.querySelectorAll(".release-suggestion-item")) {
    button.addEventListener("click", () => {
      const releaseId = String(button.getAttribute("data-release-id") || "").trim();
      if (!releaseId) {
        return;
      }
      onToggle(releaseId);
    });
  }
}

function refreshReleaseRelationshipControls() {
  const rows = Array.isArray(state.release.rows) ? state.release.rows : [];
  const dependsSearch = String(state.release.relationshipForm.dependsSearch || "").trim().toLowerCase();
  const coSearch = String(state.release.relationshipForm.coReleasesSearch || "").trim().toLowerCase();

  if (el.releaseDependsSearchInput) {
    el.releaseDependsSearchInput.value = state.release.relationshipForm.dependsSearch;
  }
  if (el.releaseCoreleasesSearchInput) {
    el.releaseCoreleasesSearchInput.value = state.release.relationshipForm.coReleasesSearch;
  }

  const dependsSelectedItems = buildReleaseSelectedItems(state.release.relationshipForm.dependsOnSelected || []);
  renderReleaseSelectedList(el.releaseDependsSelectedList, dependsSelectedItems, (releaseId) => {
    toggleSuggestionSelection("dependsOnSelected", releaseId);
    refreshReleaseRelationshipControls();
  });

  const dependsItems = buildReleaseSuggestionItems(rows, dependsSearch, state.release.relationshipForm.dependsOnSelected || []);
  renderReleaseSuggestionList(el.releaseDependsSuggestions, dependsItems, (releaseId) => {
    toggleSuggestionSelection("dependsOnSelected", releaseId);
    refreshReleaseRelationshipControls();
  });

  const coSelectedItems = buildReleaseSelectedItems(state.release.relationshipForm.coReleasesSelected || []);
  renderReleaseSelectedList(el.releaseCoreleasesSelectedList, coSelectedItems, (releaseId) => {
    toggleSuggestionSelection("coReleasesSelected", releaseId);
    refreshReleaseRelationshipControls();
  });

  const coItems = buildReleaseSuggestionItems(rows, coSearch, state.release.relationshipForm.coReleasesSelected || []);
  renderReleaseSuggestionList(el.releaseCoreleasesSuggestions, coItems, (releaseId) => {
    toggleSuggestionSelection("coReleasesSelected", releaseId);
    refreshReleaseRelationshipControls();
  });
}

function syncReleaseGraphStatusFilterInput() {
  if (!el.releaseGraphStatusFilter) {
    return;
  }
  const values = uniqueValues(state.release.graph.statusFilter || []);
  state.release.graph.statusFilter = values.length ? values : ["Released", "Planned", "Archived", "Overdue"];
  setSelectedValues(el.releaseGraphStatusFilter, state.release.graph.statusFilter);
}

function renderReleaseStatusFilterOptions() {
  if (!el.releaseStatusFilterSelect) {
    return;
  }

  const rows = Array.isArray(state.release.rows) ? state.release.rows : [];
  const statuses = Array.from(new Set(rows.map((row) => String(row.status || "").trim()).filter(Boolean)))
    .sort((left, right) => compareReleaseTextValues(left, right));

  const options = ['<option value="">All statuses</option>'];
  for (const status of statuses) {
    options.push(`<option value="${escapeHtml(status)}">${escapeHtml(status)}</option>`);
  }
  el.releaseStatusFilterSelect.innerHTML = options.join("");

  const currentStatus = String(state.release.filters?.status || "").trim();
  const hasCurrentStatus = currentStatus && statuses.includes(currentStatus);
  state.release.filters.status = hasCurrentStatus ? currentStatus : "";
  el.releaseStatusFilterSelect.value = state.release.filters.status;
}

function syncReleaseFilterInputs() {
  if (el.releaseNameFilterInput) {
    el.releaseNameFilterInput.value = String(state.release.filters?.nameQuery || "");
  }
  if (el.releaseStatusFilterSelect) {
    el.releaseStatusFilterSelect.value = String(state.release.filters?.status || "");
  }
}

function resetReleaseFilters() {
  state.release.filters = {
    nameQuery: "",
    status: "",
  };
}

function renderReleaseSortIndicators() {
  const sortButtons = document.querySelectorAll("[data-release-sort-key]");
  const activeKey = String(state.release.sort?.columnKey || "");
  const direction = String(state.release.sort?.direction || "none");

  for (const button of sortButtons) {
    const key = String(button.dataset.releaseSortKey || "");
    const isActive = key && key === activeKey && direction !== "none";
    const iconEl = button.querySelector(".release-sort-indicator");

    button.classList.toggle("is-active", isActive);
    let ariaSort = "none";
    let icon = "↕";
    if (isActive && direction === "asc") {
      ariaSort = "ascending";
      icon = "↑";
    } else if (isActive && direction === "desc") {
      ariaSort = "descending";
      icon = "↓";
    }
    button.setAttribute("aria-sort", ariaSort);
    const headerCell = button.closest("th");
    if (headerCell) {
      headerCell.setAttribute("aria-sort", ariaSort);
    }
    const label = (button.textContent || "").replace(/[↑↓↕]/g, "").trim();
    button.setAttribute("aria-label", `${label} sort ${ariaSort}`);
    if (iconEl) {
      iconEl.textContent = icon;
    }
  }
}

function handleReleaseSortHeaderClick(columnKey) {
  const currentKey = String(state.release.sort?.columnKey || "");
  const currentDirection = String(state.release.sort?.direction || "none");
  const isSameColumn = currentKey === columnKey;
  const nextDirection = cycleSortDirection(currentDirection, isSameColumn);

  if (nextDirection === "none") {
    state.release.sort = {
      columnKey: "",
      direction: "none",
    };
  } else {
    state.release.sort = {
      columnKey,
      direction: nextDirection,
    };
  }
  renderReleaseTable();
}

function applyReleaseRelationshipsToSelectedRows() {
  const selectedRowSet = getReleaseSelectedRowIdsSet();
  if (!selectedRowSet.size) {
    setReleaseRelationshipFeedback("Select at least one release row before applying relationships.", "muted");
    return;
  }

  const dependsOnIds = uniqueValues(state.release.relationshipForm.dependsOnSelected || []);
  const coReleaseIds = uniqueValues(state.release.relationshipForm.coReleasesSelected || []);

  const validIds = getValidReleaseIdsSet();
  const nextMap = normalizeReleaseRelationshipMap(state.release.relationshipData, validIds);

  for (const rowId of selectedRowSet) {
    if (!nextMap[rowId]) {
      nextMap[rowId] = createEmptyReleaseRelationshipEntry();
    }
    nextMap[rowId].depends_on = dependsOnIds.filter((id) => id !== rowId && validIds.has(id));
    nextMap[rowId].co_releases = coReleaseIds.filter((id) => id !== rowId && validIds.has(id));
  }

  state.release.relationshipData = normalizeReleaseRelationshipMap(nextMap, validIds);
  saveReleaseRelationshipsToLocalJson(state.release.relationshipData);
  setReleaseRelationshipFeedback(`Applied relationships to ${selectedRowSet.size} selected release${selectedRowSet.size === 1 ? "" : "s"}.`, "muted");
  renderReleaseGraph();
  renderReleaseTable();
}

function getReleaseGraphRenderableIds() {
  const rowById = getReleaseRowByIdMap();
  const selectedStatuses = new Set(uniqueValues(state.release.graph.statusFilter || []));
  const ids = [];
  for (const [id, entry] of Object.entries(state.release.relationshipData || {})) {
    const row = rowById.get(id);
    if (!row) {
      continue;
    }
    const hasRelation = (entry.depends_on || []).length > 0 || (entry.co_releases || []).length > 0;
    if (!hasRelation) {
      continue;
    }
    if (!selectedStatuses.has(String(row.status || ""))) {
      continue;
    }
    ids.push(id);
  }
  return ids;
}

function buildReleaseCoReleaseGroups(ids) {
  const parent = {};
  for (const id of ids) {
    parent[id] = id;
  }

  function find(id) {
    if (parent[id] === id) {
      return id;
    }
    parent[id] = find(parent[id]);
    return parent[id];
  }

  function union(leftId, rightId) {
    const rootLeft = find(leftId);
    const rootRight = find(rightId);
    if (rootLeft !== rootRight) {
      parent[rootRight] = rootLeft;
    }
  }

  const idSet = new Set(ids);
  for (const id of ids) {
    const entry = state.release.relationshipData[id] || createEmptyReleaseRelationshipEntry();
    for (const peerId of entry.co_releases || []) {
      if (idSet.has(peerId)) {
        union(id, peerId);
      }
    }
  }

  const groups = new Map();
  for (const id of ids) {
    const root = find(id);
    if (!groups.has(root)) {
      groups.set(root, []);
    }
    groups.get(root).push(id);
  }

  const idToGroup = new Map();
  for (const [root, members] of groups.entries()) {
    if (members.length < 2) {
      continue;
    }
    const groupId = `co-group:${root}`;
    for (const memberId of members) {
      idToGroup.set(memberId, groupId);
    }
  }
  return idToGroup;
}

function releaseStatusNodeClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "released") return "status-released";
  if (normalized === "planned") return "status-planned";
  if (normalized === "archived") return "status-archived";
  if (normalized === "overdue") return "status-overdue";
  return "";
}

function renderReleaseGraph() {
  if (!el.releaseGraphPanel || !el.releaseGraphCanvas) {
    return;
  }

  syncReleasePanelVisibility((state.release.rows || []).length > 0);
  if (!state.release.graph.visible) {
    return;
  }

  const cytoscapeCtor = window.cytoscape;
  if (!cytoscapeCtor) {
    el.releaseGraphCanvas.innerHTML = "<p class='muted'>Graph library unavailable.</p>";
    return;
  }

  const renderableIds = getReleaseGraphRenderableIds();
  if (!renderableIds.length) {
    el.releaseGraphCanvas.innerHTML = "<p class='muted'>No dependency nodes match current graph filters.</p>";
    if (state.release.graph.instance) {
      state.release.graph.instance.destroy();
      state.release.graph.instance = null;
    }
    return;
  }

  const rowById = getReleaseRowByIdMap();
  const idSet = new Set(renderableIds);
  const idToGroup = buildReleaseCoReleaseGroups(renderableIds);
  const elements = [];

  const groupIds = new Set(idToGroup.values());
  for (const groupId of groupIds) {
    elements.push({
      data: { id: groupId, label: "Released Together" },
      classes: "release-co-group",
    });
  }

  for (const id of renderableIds) {
    const row = rowById.get(id);
    if (!row) continue;
    const classes = ["release-node", releaseStatusNodeClass(row.status)].filter(Boolean).join(" ");
    const data = {
      id,
      label: row.name,
      status: row.status,
    };
    if (idToGroup.has(id)) {
      data.parent = idToGroup.get(id);
    }
    elements.push({ data, classes });
  }

  for (const id of renderableIds) {
    const entry = state.release.relationshipData[id] || createEmptyReleaseRelationshipEntry();
    for (const dependsId of entry.depends_on || []) {
      if (!idSet.has(dependsId)) {
        continue;
      }
      elements.push({
        data: { id: `dep:${dependsId}->${id}`, source: dependsId, target: id },
        classes: "edge-depends",
      });
    }
    for (const peerId of entry.co_releases || []) {
      if (!idSet.has(peerId) || id >= peerId) {
        continue;
      }
      elements.push({
        data: { id: `co:${id}<->${peerId}`, source: id, target: peerId },
        classes: "edge-corelease",
      });
    }
  }

  if (state.release.graph.instance) {
    state.release.graph.instance.destroy();
    state.release.graph.instance = null;
  }

  state.release.graph.instance = cytoscapeCtor({
    container: el.releaseGraphCanvas,
    elements,
    style: [
      {
        selector: ".release-node",
        style: {
          "label": "data(label)",
          "text-wrap": "wrap",
          "text-max-width": 160,
          "text-valign": "center",
          "text-halign": "center",
          "font-size": 11,
          "border-width": 1.5,
          "shape": "round-rectangle",
          "padding": 8,
          "background-color": "#e2e8f0",
          "border-color": "#94a3b8",
          "color": "#0f172a",
          "width": 190,
          "height": 58,
        },
      },
      {
        selector: ".status-released",
        style: {
          "background-color": "#ecfdf5",
          "border-color": "#10b981",
          "color": "#065f46",
        },
      },
      {
        selector: ".status-planned",
        style: {
          "background-color": "#e8f3ff",
          "border-color": "#60a5fa",
          "color": "#1e40af",
        },
      },
      {
        selector: ".status-archived",
        style: {
          "background-color": "#fff5e6",
          "border-color": "#d97706",
          "color": "#7c2d12",
        },
      },
      {
        selector: ".status-overdue",
        style: {
          "background-color": "#fef2f2",
          "border-color": "#ef4444",
          "color": "#991b1b",
        },
      },
      {
        selector: ".release-co-group",
        style: {
          "label": "data(label)",
          "font-size": 10,
          "text-valign": "top",
          "text-halign": "center",
          "background-opacity": 0.08,
          "background-color": "#60a5fa",
          "border-color": "#60a5fa",
          "border-width": 1,
          "shape": "round-rectangle",
          "padding": 16,
        },
      },
      {
        selector: ".edge-depends",
        style: {
          "width": 2,
          "line-color": "#64748b",
          "curve-style": "bezier",
          "target-arrow-color": "#64748b",
          "target-arrow-shape": "triangle",
        },
      },
      {
        selector: ".edge-corelease",
        style: {
          "width": 2,
          "line-style": "dashed",
          "line-color": "#38bdf8",
          "curve-style": "bezier",
          "target-arrow-shape": "none",
        },
      },
    ],
    layout: {
      name: "breadthfirst",
      directed: true,
      spacingFactor: 1.25,
      padding: 16,
    },
  });

  state.release.graph.instance.fit(undefined, 24);
}

function renderReleaseTable() {
  if (!el.releaseTableBody) {
    return;
  }

  const allRows = Array.isArray(state.release.rows) ? state.release.rows : [];
  syncReleasePanelVisibility(allRows.length > 0);
  renderReleaseSortIndicators();
  if (!allRows.length) {
    el.releaseTableBody.innerHTML = "";
    updateReleaseSelectAllCheckbox([]);
    setReleasePanelState("No releases available.", { tone: "muted", showTable: false });
    return;
  }

  const filteredRows = getReleaseFilteredRows(allRows);
  const rows = getSortedReleaseRows(filteredRows);

  if (!rows.length) {
    el.releaseTableBody.innerHTML = "";
    updateReleaseSelectAllCheckbox([]);
    setReleasePanelState("No releases match current filters.", { tone: "muted", showTable: true });
    return;
  }

  const selectedSet = getReleaseSelectedRowIdsSet();
  const htmlRows = rows.map((row) => `<tr>
      ${state.release.editMode ? `<td class="release-select-col">
        <input class="release-row-checkbox" type="checkbox" data-release-id="${escapeHtml(row.id)}" ${selectedSet.has(String(row.id)) ? "checked" : ""} aria-label="Select ${escapeHtml(row.name)}" />
      </td>` : ""}
      <td>${escapeHtml(row.name)}</td>
      <td>${escapeHtml(formatReleaseDate(row.releaseDate))}</td>
      <td><span class="${getReleaseStatusClass(row.status)}">${escapeHtml(row.status || "-")}</span></td>
    </tr>`);

  el.releaseTableBody.innerHTML = htmlRows.join("");
  if (state.release.editMode) {
    for (const checkbox of el.releaseTableBody.querySelectorAll(".release-row-checkbox")) {
      checkbox.addEventListener("change", () => {
        const releaseId = String(checkbox.getAttribute("data-release-id") || "").trim();
        if (!releaseId) {
          return;
        }
        toggleReleaseRowSelection(releaseId, checkbox.checked);
        updateReleaseSelectAllCheckbox(rows);
      });
    }
    updateReleaseSelectAllCheckbox(rows);
  } else {
    updateReleaseSelectAllCheckbox([]);
  }
  const isFiltered = rows.length !== allRows.length;
  const message = isFiltered
    ? `Showing ${rows.length} of ${allRows.length} releases.`
    : `Loaded ${rows.length} release${rows.length === 1 ? "" : "s"}.`;

  setReleasePanelState(message, {
    tone: "muted",
    showTable: true,
  });
}

function resetReleaseSelectionAndForms() {
  state.release.selectedRowIds = [];
  state.release.editMode = false;
  state.release.graph.visible = false;
  state.release.relationshipForm = {
    dependsSearch: "",
    coReleasesSearch: "",
    dependsOnSelected: [],
    coReleasesSelected: [],
  };
}

async function loadReleaseData() {
  state.release.loading = true;
  state.release.error = "";
  resetReleaseSelectionAndForms();
  resetReleaseFilters();
  state.release.sort = { columnKey: "", direction: "none" };
  setReleasePanelState("Loading release data...", { tone: "muted", showTable: false });

  try {
    const payload = await apiGet("/api/releases");
    if (payload && payload.error) {
      throw new Error(String(payload.error));
    }

    state.release.rows = normalizeReleaseRows(payload);
    const validIdsSet = getValidReleaseIdsSet();
    state.release.relationshipData = loadReleaseRelationshipsFromLocalJson(validIdsSet);
    scrubReleaseRelationshipsAgainstRows();
    renderReleaseStatusFilterOptions();
    syncReleaseFilterInputs();
    refreshReleaseRelationshipControls();
    syncReleaseGraphStatusFilterInput();
    state.release.loadedOnce = true;
    setReleaseRelationshipFeedback("Use Edit mode to manage Depends On and Released Together relationships.", "muted");
    renderReleaseTable();
    renderReleaseGraph();
  } catch (error) {
    state.release.rows = [];
    state.release.relationshipData = {};
    state.release.error = String(error?.message || error || "Unknown error");
    renderReleaseStatusFilterOptions();
    syncReleaseFilterInputs();
    refreshReleaseRelationshipControls();
    syncReleaseGraphStatusFilterInput();
    state.release.loadedOnce = true;
    if (el.releaseTableBody) {
      el.releaseTableBody.innerHTML = "";
    }
    setReleasePanelState(`Failed to load release data: ${state.release.error}`, {
      tone: "error-msg text-danger",
      showTable: false,
    });
  } finally {
    state.release.loading = false;
  }
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
  const previousSync = state.sync;
  try {
    state.sync = await apiGet("/api/sync/status", { trackLoading: false });
  } catch (_error) {
    state.sync = null;
  }
  renderSyncChip();

  if (previousSync && state.sync) {
    const prevRunning = previousSync.runtime?.is_running;
    const currRunning = state.sync.runtime?.is_running;
    const prevRunId = previousSync.persisted?.last_run?.run_id;
    const currRunId = state.sync.persisted?.last_run?.run_id;

    if ((prevRunning && !currRunning) || (prevRunId !== currRunId)) {
      await loadDashboardData();
    }
  }
}

async function loadDashboardData() {
  const [metricsResult, ticketsResult, teamsWorkspaceResult] = await Promise.allSettled([
    apiGet(buildSharedFilterQuery("/api/metrics")),
    apiGet(buildTicketsQuery()),
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

  if (teamsWorkspaceResult.status === "fulfilled") {
    state.teamsWorkspace = teamsWorkspaceResult.value;
    const teams = Array.isArray(state.teamsWorkspace?.teams) ? state.teamsWorkspace.teams : [];
    const teamIds = new Set(teams.map(t => String(t.team_id || "").trim()));
    if (state.selectedTeamId && !teamIds.has(state.selectedTeamId)) {
      state.selectedTeamId = "";
    }
  } else {
    state.teamsWorkspace = { teams: [] };
    state.selectedTeamId = "";
  }

  if (state.tickets.length) {
    inferJiraDomainFromTicket(state.tickets[0]);
  }

  renderKpis();
  renderStatusChart();
  renderPriorityChart();
  refreshFilterOptions();
  renderTickets();
  renderTeamsWorkspace();
  renderTeamDetailPanels();
}

function setActiveTab(tabName) {
  state.activeTab = tabName;
  const tabs = document.querySelectorAll(".tab");
  const views = document.querySelectorAll(".view");
  for (const tab of tabs) {
    tab.classList.toggle("is-active", tab.dataset.tab === tabName);
  }
  for (const view of views) {
    view.classList.toggle("is-active", view.id === tabName);
  }
  syncFilterControlsVisibility(tabName);
  if (tabName === "release" && !state.release.loading && !state.release.loadedOnce) {
    loadReleaseData();
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
      if (tab.dataset.tab === "release" && state.release.loadedOnce && !state.release.loading) {
        scrubReleaseRelationshipsAgainstRows();
        refreshReleaseRelationshipControls();
        renderReleaseTable();
        renderReleaseGraph();
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

  if (el.teamWorkspaceSearchInput) {
    el.teamWorkspaceSearchInput.addEventListener("input", () => {
      state.teamWorkspaceSearch = String(el.teamWorkspaceSearchInput.value || "").trim();
      renderTeamsWorkspace();
    });
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

  const releaseSortButtons = document.querySelectorAll("[data-release-sort-key]");
  for (const button of releaseSortButtons) {
    button.addEventListener("click", () => {
      const columnKey = String(button.dataset.releaseSortKey || "").trim();
      if (!columnKey) {
        return;
      }
      handleReleaseSortHeaderClick(columnKey);
    });
  }

  if (el.releaseSelectAllCheckbox) {
    el.releaseSelectAllCheckbox.addEventListener("change", () => {
      const visibleRows = getSortedReleaseRows(getReleaseFilteredRows(state.release.rows || []));
      const selectedSet = getReleaseSelectedRowIdsSet();
      if (el.releaseSelectAllCheckbox.checked) {
        for (const row of visibleRows) {
          selectedSet.add(String(row.id));
        }
      } else {
        for (const row of visibleRows) {
          selectedSet.delete(String(row.id));
        }
      }
      setReleaseSelectedRowsFromSet(selectedSet);
      renderReleaseTable();
    });
  }

  if (el.releaseDependsSearchInput) {
    el.releaseDependsSearchInput.addEventListener("input", () => {
      state.release.relationshipForm.dependsSearch = String(el.releaseDependsSearchInput.value || "");
      refreshReleaseRelationshipControls();
    });
  }

  if (el.releaseCoreleasesSearchInput) {
    el.releaseCoreleasesSearchInput.addEventListener("input", () => {
      state.release.relationshipForm.coReleasesSearch = String(el.releaseCoreleasesSearchInput.value || "");
      refreshReleaseRelationshipControls();
    });
  }

  if (el.releaseEditToggleBtn) {
    el.releaseEditToggleBtn.addEventListener("click", () => {
      state.release.editMode = !state.release.editMode;
      if (!state.release.editMode) {
        state.release.selectedRowIds = [];
      }
      renderReleaseTable();
      refreshReleaseRelationshipControls();
    });
  }

  if (el.releaseApplyRelationshipsBtn) {
    el.releaseApplyRelationshipsBtn.addEventListener("click", () => {
      applyReleaseRelationshipsToSelectedRows();
    });
  }

  if (el.releaseGraphToggleBtn) {
    el.releaseGraphToggleBtn.addEventListener("click", () => {
      state.release.graph.visible = !state.release.graph.visible;
      if (state.release.graph.visible) {
        renderReleaseGraph();
      } else {
        renderReleaseTable();
      }
    });
  }

  if (el.releaseGraphStatusFilter) {
    enableToggleMultiSelect(el.releaseGraphStatusFilter);
    el.releaseGraphStatusFilter.addEventListener("change", () => {
      state.release.graph.statusFilter = uniqueValues(getSelectedValues(el.releaseGraphStatusFilter));
      renderReleaseGraph();
    });
  }

  if (el.releaseNameFilterInput) {
    el.releaseNameFilterInput.addEventListener("input", () => {
      state.release.filters.nameQuery = String(el.releaseNameFilterInput.value || "");
      renderReleaseTable();
    });
  }

  if (el.releaseStatusFilterSelect) {
    el.releaseStatusFilterSelect.addEventListener("change", () => {
      state.release.filters.status = String(el.releaseStatusFilterSelect.value || "").trim();
      renderReleaseTable();
    });
  }

  if (el.releaseClearFiltersBtn) {
    el.releaseClearFiltersBtn.addEventListener("click", () => {
      resetReleaseFilters();
      syncReleaseFilterInputs();
      renderReleaseTable();
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
    global: "InfoComm Global",
  };
  const websiteMap = {
    india: "https://www.infocomm-india.com/",
    global: "https://www.infocommshow.org/",
  };
  
  // Update website link
  if (el.infocommWebsiteUrl) {
    el.infocommWebsiteUrl.href = websiteMap[state.infocomm.selectedShow];
    el.infocommWebsiteUrl.textContent = `Visit Official ${showNameMap[state.infocomm.selectedShow]} Website`;
  }
  
  const dates = uniqueValues((state.infocomm.schedule || []).map((item) => item.date));
  el.infocommDateTabs.innerHTML = "";

  if (!dates.length) {
    el.infocommScheduleList.innerHTML = '<p class="muted">No schedule dates available.</p>';
    return;
  }

  el.infocommScheduleList.innerHTML = `
    <div class="infocomm-sessions-feed">
      ${dates.map((date) => `
        <article class="infocomm-session-card">
          <h4 class="infocomm-session-title">${escapeHtml(date)}</h4>
        </article>
      `).join("")}
    </div>
  `;

  if (window.lucide) {
    window.lucide.createIcons();
  }
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

function bindThemeToggle() {
  if (!el.themeToggleBtn) {
    return;
  }

  const savedTheme = localStorage.getItem("theme") || "light";
  document.body.setAttribute("data-theme", savedTheme);

  el.themeToggleBtn.addEventListener("click", () => {
    const currentTheme = document.body.getAttribute("data-theme") || "light";
    const nextTheme = currentTheme === "light" ? "dark" : "light";
    document.body.setAttribute("data-theme", nextTheme);
    localStorage.setItem("theme", nextTheme);
  });
}

async function bootstrap() {
  readStateFromQuery();
  bindTabNavigation();
  bindSidebarToggle();
  bindFilterDisclosure();
  bindThemeToggle();
  bindActions();
  setActiveTab(state.activeTab);
  await loadSyncStatus();
  await loadDashboardData();
  syncInputsFromState();
  setInterval(loadSyncStatus, pollIntervalMs);
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

bootstrap();
