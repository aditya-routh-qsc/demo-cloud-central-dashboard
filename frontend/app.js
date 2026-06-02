const state = {
  filters: {
    search: "",
    statuses: [],
    assignees: [],
    excludedStatuses: [],
    excludedAssignees: [],
    boardId: "",
    limit: 200,
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
};

const pollIntervalMs = 15000;
const mobileBreakpoint = 900;

const el = {
  syncChip: document.getElementById("syncChip"),
  manualSyncBtn: document.getElementById("manualSyncBtn"),
  searchInput: document.getElementById("searchInput"),
  statusSelect: document.getElementById("statusSelect"),
  assigneeSelect: document.getElementById("assigneeSelect"),
  statusSummary: document.getElementById("statusSummary"),
  assigneeSummary: document.getElementById("assigneeSummary"),
  boardInput: document.getElementById("boardInput"),
  limitInput: document.getElementById("limitInput"),
  applyFiltersBtn: document.getElementById("applyFiltersBtn"),
  resetFiltersBtn: document.getElementById("resetFiltersBtn"),
  ticketsGroups: document.getElementById("ticketsGroups"),
  nodeDetails: document.getElementById("nodeDetails"),
  networkEmptyState: document.getElementById("networkEmptyState"),
  networkMobileSummary: document.getElementById("networkMobileSummary"),
  networkGraph: document.getElementById("networkGraph"),
  kpiTotalActive: document.getElementById("kpiTotalActive"),
  kpiOpenBugs: document.getElementById("kpiOpenBugs"),
  kpiStale: document.getElementById("kpiStale"),
  kpiFilteredTotal: document.getElementById("kpiFilteredTotal"),
};

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
  params.set("limit", String(state.filters.limit));
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
  state.filters.limit = Number(params.get("limit") || 200);
  state.filters.offset = Number(params.get("offset") || 0);
  if (!Number.isFinite(state.filters.limit) || state.filters.limit < 1 || state.filters.limit > 1000) {
    state.filters.limit = 200;
  }
  if (!Number.isFinite(state.filters.offset) || state.filters.offset < 0) {
    state.filters.offset = 0;
  }
}

function syncInputsFromState() {
  el.searchInput.value = state.filters.search;
  el.boardInput.value = state.filters.boardId;
  el.limitInput.value = String(state.filters.limit);
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
  params.set("limit", String(state.filters.limit));
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
  state.filters.limit = Number(el.limitInput.value || 200);
  if (!Number.isFinite(state.filters.limit) || state.filters.limit < 1) {
    state.filters.limit = 200;
  }
  if (state.filters.limit > 1000) {
    state.filters.limit = 1000;
  }
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

function buildDependencyDetailsForNode(nodeId, networkData) {
  const nodes = Array.isArray(networkData?.nodes) ? networkData.nodes : [];
  const edges = Array.isArray(networkData?.edges) ? networkData.edges : [];
  const nodeById = new Map(nodes.map((node) => [String(node.id || node.ticket_key || ""), node]));

  const outgoing = [];
  const incoming = [];

  for (const edge of edges) {
    const source = String(edge.source_ticket || "");
    const target = String(edge.target_ticket || "");
    if (source === nodeId) {
      outgoing.push(edge);
    }
    if (target === nodeId) {
      incoming.push(edge);
    }
  }

  outgoing.sort((a, b) => String(a.target_ticket || "").localeCompare(String(b.target_ticket || "")));
  incoming.sort((a, b) => String(a.source_ticket || "").localeCompare(String(b.source_ticket || "")));

  const toListHtml = (rows, counterpartKey) => {
    if (!rows.length) {
      return "<li class='muted'>None</li>";
    }

    return rows.map((edge) => {
      const counterpartTicket = String(edge[counterpartKey] || "");
      const counterpartNode = nodeById.get(counterpartTicket) || {};
      const counterpartStatus = counterpartNode.status || "Unknown";
      const relation = edge.relation_name || edge.relation_description || edge.dependency_type || "dependency";
      const classification = edge.classification || "unclassified";
      return `<li>
        <strong>${escapeHtml(counterpartTicket)}</strong>
        <span class="muted">(${escapeHtml(counterpartStatus)})</span>
        <br/>
        <span>${escapeHtml(relation)}</span>
        <span class="muted"> | ${escapeHtml(classification)}</span>
      </li>`;
    }).join("");
  };

  return {
    outgoingHtml: toListHtml(outgoing, "target_ticket"),
    incomingHtml: toListHtml(incoming, "source_ticket"),
    outgoingCount: outgoing.length,
    incomingCount: incoming.length,
  };
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
    renderMobileDependencySummary();
    renderNetworkEmptyState("Mobile summary mode: interactive graph is optimized for desktop.");
    return;
  }

  el.networkGraph.style.display = "block";
  el.networkMobileSummary.className = "network-mobile-summary";
  el.networkMobileSummary.innerHTML = "";

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
    elements.push({
      data: {
        id: node.id,
        ticket_key: node.ticket_key,
        summary: node.summary || "",
        status: node.status || "",
        assignee: node.assignee || "",
        reporter: node.reporter || "",
        issue_type: node.issue_type || "",
        priority: node.priority || "",
        story_points: node.story_points,
      },
    });
  }

  for (const edge of data.edges || []) {
    elements.push({
      data: {
        id: `${edge.source_ticket}->${edge.target_ticket}`,
        source: edge.source_ticket,
        target: edge.target_ticket,
        classification: edge.classification || "",
      },
    });
  }

  state.cy = cyCtor({
    container: el.networkGraph,
    elements,
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#1dd3ff",
          "color": "#eef7ff",
          "font-size": 9,
          "text-valign": "center",
          label: "data(ticket_key)",
        },
      },
      {
        selector: "edge",
        style: {
          width: 2,
          "line-color": "#3ad29f",
          "target-arrow-color": "#3ad29f",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
        },
      },
      {
        selector: "edge[classification = 'inter_team']",
        style: {
          "line-style": "dashed",
          "line-color": "#ff9f43",
          "target-arrow-color": "#ff9f43",
        },
      },
    ],
    layout: {
      name: "cose",
      animate: true,
      fit: true,
    },
  });

  state.cy.on("tap", "node", (event) => {
    const node = event.target.data();
    const issueUrl = jiraIssueUrl(node.id);
    const deps = buildDependencyDetailsForNode(String(node.id || ""), data);
    el.nodeDetails.innerHTML = `<p><strong>${escapeHtml(node.ticket_key)}</strong></p>
      <p>${escapeHtml(node.summary || "No summary")}</p>
      <p>Status: ${escapeHtml(node.status || "Unknown")}</p>
      <p>Assignee: ${escapeHtml(node.assignee || "Unassigned")}</p>
      <p>Reporter: ${escapeHtml(node.reporter || "Unknown")}</p>
      <p>Type: ${escapeHtml(node.issue_type || "Unknown")}</p>
      <p>Priority: ${escapeHtml(node.priority || "Unknown")}</p>
      <p>Story points: ${node.story_points ?? "-"}</p>
      <p><strong>Dependencies Out (${deps.outgoingCount})</strong></p>
      <ul>${deps.outgoingHtml}</ul>
      <p><strong>Dependencies In (${deps.incomingCount})</strong></p>
      <ul>${deps.incomingHtml}</ul>
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
      limit: 200,
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
  bindActions();
  await loadSyncStatus();
  await loadDashboardData();
  syncInputsFromState();
  setInterval(loadSyncStatus, pollIntervalMs);
}

bootstrap();
