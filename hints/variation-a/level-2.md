# Variation A — Hint 2 of 3: the relationship to inspect

A Service and the Pods behind it are connected by **labels**, not by name.

Compare two lists side by side:

- what the Service says it is looking for, and
- what labels the `web` Pods actually carry (`--show-labels`).

Then look at what the Service ended up with: does it list any backend addresses at all?

When you decide how to correct the mismatch, consider which side is cheaper and safer
to change given the brief's constraint, and check the `report` Pods' labels so your
fix doesn't select them too.
