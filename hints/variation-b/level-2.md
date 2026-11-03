# Variation B — Hint 2 of 3: the relationship to inspect

A Service only sends traffic to Pods that report **Ready**. Something decides whether
each Pod is Ready, and that decision is made by the kubelet running a check you can
read in the Pod spec.

Careful with "does the Service have backends?": an endpoint address can be *listed* and
still be marked not ready. Look at the per-endpoint conditions, not just the addresses.

Compare what that check asks the application for with what the application actually
serves. Where could you observe what the application serves? (Its logs, or a request
from another Pod.)

Remember the team's rule: whatever you do, an unhealthy Pod must still be kept out of
rotation. Removing the check would make the symptom disappear and break the rule.
