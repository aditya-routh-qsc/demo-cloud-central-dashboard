#!/usr/bin/env python3
"""Test bidirectional dependency filtering."""

from main import get_network

# Get full graph
data = get_network(search=None, status=None, assignee=None, status_exclude=[], assignee_exclude=[], board_id=None)
nodes = data.get('nodes', [])
edges = data.get('edges', [])

print(f'Total graph: {len(nodes)} nodes, {len(edges)} edges')

if not edges:
    print('No edges in graph; skipping test.')
    exit(1)

# Pick a sample ticket that appears in edges
sample_src = edges[0]['source_ticket']
print(f'\nTesting with ticket: {sample_src}')

# Query filtered by that ticket's summary
result = get_network(search=sample_src, status=None, assignee=None, status_exclude=[], assignee_exclude=[], board_id=None)
filtered_nodes = result['nodes']
filtered_edges = result['edges']

print(f'Filtered by search="{sample_src}": {len(filtered_nodes)} nodes, {len(filtered_edges)} edges')

# Count incoming vs outgoing
incoming = [e for e in filtered_edges if e['target_ticket'] == sample_src]
outgoing = [e for e in filtered_edges if e['source_ticket'] == sample_src]

print(f'  Edges targeting {sample_src} (incoming): {len(incoming)}')
print(f'  Edges sourcing from {sample_src} (outgoing): {len(outgoing)}')
print(f'  Total: {len(incoming) + len(outgoing)}')

if len(incoming) > 0 and len(outgoing) > 0:
    print('\n✓ SUCCESS: Both incoming and outgoing dependencies are visible!')
elif len(incoming) == 0 and len(outgoing) > 0:
    print('\n✗ ISSUE: Only outgoing dependencies are showing (no incoming).')
elif len(incoming) > 0 and len(outgoing) == 0:
    print('\n✗ ISSUE: Only incoming dependencies are showing (no outgoing).')
else:
    print('\n✗ ISSUE: Neither incoming nor outgoing dependencies found.')
