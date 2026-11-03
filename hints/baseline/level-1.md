# Baseline — Hint 1 of 3: where to look

Before you change anything, **orient**: confirm your context and namespace, then list
what exists in `drill-baseline`.

- How does one Pod normally find another in Kubernetes? Which API object gives a
  workload a stable name and address inside the cluster?
- Look at the `web` Deployment itself. What does the container say about how it
  listens for traffic? That information lives in the cluster, not in the task brief.
- Docs worth having open: the Kubernetes **Service** concept page and the output of
  `kubectl <command> --help` for whatever command you reach for.

Record in your worksheet that you consulted hint 1, then try again.
