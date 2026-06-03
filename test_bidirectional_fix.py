#!/usr/bin/env python3
"""Test bidirectional dependency filtering with a ticket that has both."""

from main import get_network

# Full graph
data = get_network(search=None, status=None, assignee=None, status_exclude=[], assignee_exclude=[], board_id=None)
edges_full = data.get('edges', [])

print(f'Full graph has {len(edges_full)} edges\n')

# Test ticket with both incoming and outgoing in the database
test_ticket = 'QSYSCLOUD-2848'

# Query filtered by that ticket's key
result = get_network(search=test_ticket, status=None, assignee=None, status_exclude=[], assignee_exclude=[], board_id=None)
filtered_nodes = result['nodes']
filtered_edges = result['edges']

print(f'Filtered by search="{test_ticket}":')
print(f'  Nodes returned: {len(filtered_nodes)}')
print(f'  Edges returned: {len(filtered_edges)}')

# Count incoming vs outgoing
incoming = [e for e in filtered_edges if e['target_ticket'] == test_ticket]
outgoing = [e for e in filtered_edges if e['source_ticket'] == test_ticket]

print(f'\n  Edges WITH {test_ticket} as TARGET (incoming): {len(incoming)}')
print(f'  Edges WITH {test_ticket} as SOURCE (outgoing): {len(outgoing)}')
print(f'  Total edges connected to {test_ticket}: {len(incoming) + len(outgoing)}')

if len(incoming) > 0 and len(outgoing) > 0:
    print('\n✓ SUCCESS: Both incoming and outgoing dependencies are visible!')
    print('  The fix is working correctly!')
elif len(incoming) == 0 and len(outgoing) > 0:
    print('\n✗ ISSUE: Only outgoing dependencies are showing (no incoming).')
    print('  The fix may not have been applied correctly.')
elif len(incoming) > 0 and len(outgoing) == 0:
    print('\n✗ ISSUE: Only incoming dependencies are showing (no outgoing).')
else:
    print('\n✗ ISSUE: Neither incoming nor outgoing dependencies found.')
    
# Show sample edges
if incoming:
    print(f'\n  Sample incoming edges to {test_ticket}:')
    for e in incoming[:3]:
        print(f'    {e["source_ticket"]} -> {e["target_ticket"]}')
if outgoing:
    print(f'\n  Sample outgoing edges from {test_ticket}:')
    for e in outgoing[:3]:
        print(f'    {e["source_ticket"]} -> {e["target_ticket"]}')
