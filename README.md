This repository is a **security-first Kubernetes GitOps** reference implementation designed to demonstrate practical DevSecOps architecture and day-2 operations.

It deploys a minimal **nginx hello-world** workload and layers security controls across:

- **GitOps** delivery with **Argo CD**
- **Configuration composition** with **Kustomize**
- **Admission control** (policy-as-code) with **Kyverno** (and an optional native `ValidatingAdmissionPolicy` example)
- **Service mesh** security with **Istio** (mTLS + L7 authorization)
- **CNI-level** security with **Cilium** (L3/L4/L7 network policy)
- **Operator pattern** with a small **CRD + operator** that enforces namespace security intent (example)

## What this does

- Deploys `apps/hello-nginx`: a small nginx deployment serving a fixed “hello” page.
- Enforces **secure-by-default workload posture** (non-root, no privilege escalation, read-only root FS, dropped capabilities).
- Applies **admission policies** to prevent unsafe specs from being admitted.
- Enables **Istio strict mTLS** in the app namespace and restricts L7 access via mesh `AuthorizationPolicy`.
- Applies a **CiliumNetworkPolicy** so the app has constrained network reachability.
- Uses **Argo CD** to continuously reconcile cluster state from Git.

## Why this is necessary

Kubernetes “works” without these layers, but insecure defaults create predictable failure modes:

- Pods run as root, request dangerous Linux capabilities, or mount host paths.
- Apps can laterally move across namespaces because networking is flat.
- Traffic is unencrypted inside the cluster; identity is weak at the network layer.
- Drift accumulates because humans apply YAML manually.

This repo demonstrates how to build **defense-in-depth** using native Kubernetes primitives plus widely adopted CNCF tools.

## Tooling and skills demonstrated

- **Kustomize**: base/overlay model; environment-specific composition.
- **Argo CD**: GitOps app-of-apps; multi-source apps (Kustomize/Helm).
- **Kyverno**: policy-as-code; validation + mutation (where appropriate).
- **Kubernetes admission**: native policy example (`ValidatingAdmissionPolicy`).
- **Istio**: sidecar injection; strict mTLS; L7 access control.
- **Cilium**: network policy with identity-aware enforcement.
- **Operator/CRD**: custom security intent modeled as a CRD with a controller applying derived resources.

---

## Repository layout

```
.
├── apps/
│   └── hello-nginx/
│       ├── base/
│       └── overlays/
│           ├── dev/
│           └── prod/
├── argocd/
│   ├── apps/
│   └── bootstrap/
├── operators/
│   └── security-profile-operator/
├── platform/
│   ├── istio/
│   ├── cilium/
│   ├── kyverno/
│   └── namespaces/
├── policies/
│   ├── kyverno/
│   └── validating-admission-policy/
└── kustomize/
    └── envs/
        ├── dev/
        └── prod/
```

---

## Architecture and where security controls apply

### Control plane gates (Admission)

- **Kyverno admission controller**: blocks insecure pod specs before they enter etcd.
  - Example controls: require non-root, disallow privilege escalation, drop capabilities, forbid host namespaces, enforce read-only root filesystem.
- **Native `ValidatingAdmissionPolicy` example**: demonstrates Kubernetes-built-in admission (CEL).

### Workload runtime posture (Pod Security)

The nginx deployment ships with:

- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true`
- `capabilities.drop: ["ALL"]`
- `seccompProfile: RuntimeDefault`

### Network segmentation (CNI: Cilium)

- **CiliumNetworkPolicy** restricts ingress/egress at the dataplane.
- This blocks lateral movement even if a pod is compromised.

### Service-to-service identity + L7 authorization (Istio)

- **Strict mTLS**: encrypts pod-to-pod traffic and binds it to workload identity.
- **AuthorizationPolicy**: L7 allow rules (who can call what).

### Continuous enforcement (GitOps: Argo CD)

- Cluster state is reconciled from Git; drift is reverted.
- Changes are reviewed in PRs, creating an audit trail.

### Custom security intent (Operator/CRD)

- A small CRD models “desired security posture” for a namespace.
- The operator translates intent into concrete policies/resources (example pattern).

---

## Prerequisites

- Kubernetes cluster (recommended: **kind** or a managed cluster)
- `kubectl`
- `kustomize`
- `argocd` CLI (optional but useful)

Platform components can be installed by Argo CD (recommended) or manually.

---

## Quick start (GitOps path)

### 1) Install Argo CD (bootstrap)

Apply Argo CD into `argocd` namespace (one-time). Example:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 2) Point Argo CD at this repo (root app)

Edit `argocd/bootstrap/root-app-dev.yaml` to set your repo URL and revision, then:

```bash
kubectl apply -n argocd -f argocd/bootstrap/root-app-dev.yaml
```

Argo CD will then deploy:

- Kyverno policies
- Istio mesh policies
- Cilium network policy examples
- nginx hello-world app

## Platform prerequisites (what you install once)

This repo assumes these components already exist in the cluster:

- **Cilium** as the cluster CNI (because it’s installed at cluster bring-up time).
- **Istio** control plane and an ingress gateway (so mTLS + `AuthorizationPolicy` resources can reconcile).
- **Kyverno** (so `ClusterPolicy` resources can reconcile).

This repo intentionally keeps the “platform install” step separate from “platform policy” so the security controls are clear and reviewable.

## Repo placeholders you must replace

- `REPLACE_ME_REPO_URL` in `argocd/**` with your Git repo URL.
- `ghcr.io/REPLACE_ME/...` in `operators/security-profile-operator/manifests/deployment.yaml` with your built operator image.

---

## Environment overlays

- **dev**: more permissive (faster iteration), still secure defaults.
- **prod**: stricter policies and traffic restrictions.

Entry points:

- `kustomize/envs/dev`
- `kustomize/envs/prod`

Manual apply (non-GitOps):

```bash
kubectl apply -k kustomize/envs/dev
```

---

## Verification

- Nginx:

```bash
kubectl -n hello-nginx get deploy,po,svc
```

- Kyverno policies:

```bash
kubectl -n kyverno get po
kubectl get cpol
```

- Istio mTLS/authorization:

```bash
kubectl -n hello-nginx get peerauthentication,authorizationpolicy
```

- Cilium policy:

```bash
kubectl -n hello-nginx get ciliumnetworkpolicy
```

---

## Notes on production hardening (extensions)

- Add image signing enforcement (cosign + policy admission).
- Add runtime detection (Falco/Tetragon).
- Add secret management (External Secrets / Vault) and restrict secret access (RBAC).
- Add SLSA build provenance and promotion gates in CI/CD.


