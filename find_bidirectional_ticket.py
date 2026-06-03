#!/usr/bin/env python3
"""Find a ticket with both incoming and outgoing dependencies."""

from database import get_connection

with get_connection() as conn:
    # Find tickets with both incoming and outgoing
    result = conn.execute('''
        WITH sources AS (
            SELECT source_ticket_key as key, COUNT(*) as out_count FROM ticket_dependencies_current GROUP BY source_ticket_key
        ),
        targets AS (
            SELECT target_ticket_key as key, COUNT(*) as in_count FROM ticket_dependencies_current GROUP BY target_ticket_key
        )
        SELECT s.key, s.out_count, COALESCE(t.in_count, 0) as in_count
        FROM sources s
        LEFT JOIN targets t ON s.key = t.key
        WHERE t.key IS NOT NULL
        ORDER BY (s.out_count + COALESCE(t.in_count, 0)) DESC
        LIMIT 5
    ''').fetchall()
    
    print("Tickets with both incoming and outgoing dependencies:")
    for row in result:
        ticket_key, out_count, in_count = row
        print(f"  {ticket_key}: {in_count} incoming, {out_count} outgoing")
        
    if result:
        test_ticket = result[0][0]
        print(f"\nUsing {test_ticket} for testing")
