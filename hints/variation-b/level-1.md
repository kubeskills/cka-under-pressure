# Variation B — Hint 1 of 3: where to look

"Running" and "Ready" are different states. Start with the Pods:

- What does the READY column say for each `web` Pod?
- What do the Pod's events say? (`kubectl describe pod`, or `kubectl get events`.)
- What does the Service currently have to send traffic to?

The Kubernetes concept page on **liveness, readiness and startup probes** is the one
to have open.
