#!/usr/bin/env python3
"""Check incoming edges in database."""

from database import get_connection

with get_connection() as conn:
    # Check edges targeting QSYSCLOUD-1000
    edges_to_1000 = conn.execute(
        'SELECT source_ticket_key, target_ticket_key, dependency_type FROM ticket_dependencies_current WHERE target_ticket_key = ? LIMIT 10',
        ['QSYSCLOUD-1000']
    ).fetchall()

    # Check edges from QSYSCLOUD-1000
    edges_from_1000 = conn.execute(
        'SELECT source_ticket_key, target_ticket_key, dependency_type FROM ticket_dependencies_current WHERE source_ticket_key = ? LIMIT 10',
        ['QSYSCLOUD-1000']
    ).fetchall()

    print(f'Database edges targeting QSYSCLOUD-1000: {len(edges_to_1000)}')
    if edges_to_1000:
        print('Sample edges TO QSYSCLOUD-1000:')
        for e in edges_to_1000:
            print(f'  {e[0]} -> {e[1]} ({e[2]})')

    print(f'\nDatabase edges from QSYSCLOUD-1000: {len(edges_from_1000)}')
    if edges_from_1000:
        print('Sample edges FROM QSYSCLOUD-1000:')
        for e in edges_from_1000:
            print(f'  {e[0]} -> {e[1]} ({e[2]})')
