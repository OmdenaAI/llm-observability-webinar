# Backup & Disaster Recovery Policy

Last updated: January 2026

This policy governs how backup infrastructure is operated across all
production systems.

All production databases are snapshotted on a rolling schedule and
replicated to a geographically separate region. Every backup snapshot
that is captured, including snapshots taken before an account or
record was removed from production, is retained for 90 days from the
date it was captured, after which it is purged automatically as part
of routine backup rotation. This 90-day window exists to support
disaster recovery and point-in-time restoration in the event of a
system failure, data corruption incident, or accidental deletion of
infrastructure.

Access to restore from a backup snapshot is limited to the
infrastructure on-call team and requires a documented incident ticket.
Backup snapshots are encrypted at rest using the same key management
system as production data.