# Native ValidatingAdmissionPolicy example

This directory contains an example using Kubernetes **native admission** (`ValidatingAdmissionPolicy` + CEL).

Notes:

- Requires a Kubernetes version where `admissionregistration.k8s.io/v1` `ValidatingAdmissionPolicy` is available/enabled.
- This repo primarily uses **Kyverno** for policy-as-code because it’s widely used and easier to author at scale.

Apply (optional):

```bash
kubectl apply -f policies/validating-admission-policy/disallow-privileged-pods.yaml
```


