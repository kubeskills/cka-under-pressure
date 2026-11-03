# Variation B — Hint 3 of 3: a more explicit diagnostic approach

1. `kubectl describe pod` on one `web` Pod. Find the readiness check configuration and
   the most recent events about it. Note the exact request it makes (path and port).
2. Look at the container's logs. The app logs the requests it receives, including ones
   it could not satisfy.
3. From a short-lived Pod, request the application directly on its port, on the path
   the check uses and on a couple of other likely paths. Which ones succeed?
4. Decide which side is wrong: the check, or the application. The brief tells you the
   image and the rule about health checking.
5. Make the smallest change that makes the check ask for something the application
   serves. A change to the Pod template triggers a rolling update; watch it finish
   (`kubectl rollout status`) before you verify.
6. Run `scripts/verify.sh variation-b`.
