# Variation A — Hint 3 of 3: a more explicit diagnostic approach

1. Print the Service as YAML and write down its selector.
2. Run `kubectl get pods --show-labels` and write down the labels on the `web` Pods
   and on the `report` Pod.
3. Check: does every key=value in the selector appear on the `web` Pods? Does any
   `report` label also satisfy it?
4. Choose the change that leaves the Deployment's spec untouched. (Changing Pod
   template labels rolls the Pods, which the brief forbids.)
5. After the change, confirm the Service now lists three backend addresses, then
   request it by name from a short-lived Pod, then run `scripts/verify.sh variation-a`.
