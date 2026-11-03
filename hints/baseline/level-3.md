# Baseline — Hint 3 of 3: a more explicit diagnostic approach

Work through this loop. It tells you *how to find out*, not what to type for the fix.

1. **Read state.** Print the `web` Deployment as YAML and find: the replica count, the
   labels that select its Pods, and the container's declared port.
2. **Make the smallest change** for each gap you found (size, then connectivity).
3. **Check what the Service actually selected.** List the Service's EndpointSlices (or
   Endpoints) and compare the addresses to `kubectl get pods -o wide`. Empty or
   unexpected addresses mean the selection is wrong. Addresses that look right but
   still refuse connections point at the port.
4. **Test like a client.** Run a short-lived Pod in the namespace and request the
   Service by name. Any image that has a small HTTP client works; the `web` image
   (`busybox`, with its `wget` applet) is already on the node. Use `--rm` so the Pod
   cleans up after itself.
5. **Run `scripts/verify.sh baseline`.** Read each criterion, not just the summary.
