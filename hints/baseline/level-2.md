# Baseline — Hint 2 of 3: the relationships to inspect

Three things have to line up for a Service to work:

1. **The name and port clients use** (what the brief asks for).
2. **Which Pods the Service sends traffic to** — and how it decides.
3. **The port the application actually listens on** — which is not necessarily the
   port clients use.

Ask yourself which of these you are given and which you have to *discover* from the
cluster. Also compare the labels on the `web` Pods with the labels on the `report`
Pods: what would happen if you matched on a label they both carry?

Finally, the Deployment is not at the size the brief asks for yet.
