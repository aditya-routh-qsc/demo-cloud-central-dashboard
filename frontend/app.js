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
  themeToggleBtn: document.getElementById("themeToggleBtn"),
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
  return tabName === "teams" || tabName === "infocomm";
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

  const totalPoints = Array.from(byStatus.values()).reduce((sum, v) => sum + v, 0);
  const hasPointsData = totalPoints > 0;

  // Fall back to ticket count per status when no story points are recorded
  let labels, data, chartLabel;
  if (hasPointsData) {
    labels = Array.from(byStatus.keys());
    data = Array.from(byStatus.values());
    chartLabel = "Story points";
  } else {
    const byCount = new Map();
    for (const ticket of state.tickets) {
      const key = ticket.status || "Unknown";
      byCount.set(key, (byCount.get(key) || 0) + 1);
    }
    labels = Array.from(byCount.keys());
    data = Array.from(byCount.values());
    chartLabel = "Tickets (no story points)";
  }

  // Update the chart title to reflect what is being shown
  const chartHeading = document.querySelector("#metrics .panel:first-child h3");
  if (chartHeading) {
    chartHeading.textContent = hasPointsData ? "Story points by status" : "Tickets count by status";
  }

  makeChart("storyPointsChart", {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: chartLabel,
        data,
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
    state.sync = await apiGet("/api/sync/status");
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
  renderDependencyChart();
  renderStoryPointsChart();
  renderAssigneeChart();
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
