# Variation A — Hint 1 of 3: where to look

Start from the symptom and work toward the cause, in the order a request travels:

- Does the name `web` resolve from inside the namespace?
- Does a Service by that name exist, and what does it say about *which Pods* it serves?
- Are the Pods themselves healthy? (The brief says they look healthy. Check, don't assume.)

`kubectl describe` on the Service and `kubectl get` on its EndpointSlices are good
first stops. The Kubernetes **Service** concept page explains how a Service finds Pods.

Remember the constraint: the running `web` Pods must not be restarted or replaced.
