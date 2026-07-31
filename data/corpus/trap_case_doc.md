# Data Retention Policy

## Overview

This policy describes how user data is retained, backed up, and
ultimately deleted across our systems, in accordance with applicable
data protection regulations. It applies to all account data collected
through our products, including profile information, usage logs, and
billing records.

## Production Systems

Deleted account data is removed from active production systems
immediately upon processing a deletion request. Once a deletion request
has been confirmed, the associated account record, profile information,
and usage history are purged from all production databases and are no
longer accessible through any customer-facing or internal tool.

## Backup and Disaster Recovery

Backup systems, which are separate from production systems, retain a
rolling snapshot of all account data, including deleted accounts, for 90
days as part of standard disaster-recovery procedure. This snapshot
exists solely to support recovery from infrastructure failure and is not
accessible for day-to-day account management. After the 90-day window,
backups are purged on a routine schedule along with the rest of that
snapshot generation.

## Legal Holds

If an account is subject to a legal hold, litigation, or an active
regulatory inquiry, standard deletion and backup-purge timelines
described above do not apply. Data subject to a hold is retained until
the hold is formally released by the legal team, regardless of any
deletion request made in the interim.

## Exceptions and Contact

For questions about specific handling exceptions, retention timelines
for a particular data category, or the status of a legal hold, contact
the privacy team directly.