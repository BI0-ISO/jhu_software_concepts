Operational Notes
=================

Busy-State Policy
-----------------

- When a pull is running, the UI disables Update Analysis and the JSON
  endpoint returns ``409`` with ``{"busy": true}``.
- Pull attempts while busy also return ``409``.

Idempotency Strategy
--------------------

- Database inserts use the ``url`` field as a uniqueness constraint.
- Duplicate pulls do not create duplicate rows.
