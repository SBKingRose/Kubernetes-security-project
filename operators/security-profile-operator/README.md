# SecurityProfile Operator (demo)

This is a minimal example of the **operator pattern** for security intent.

## What it does

Watches cluster-scoped `SecurityProfile` resources and (for the referenced namespace):

- Ensures the namespace is labeled `istio-injection=enabled`
- Applies an Istio `PeerAuthentication` (STRICT mTLS) and `AuthorizationPolicy` (allow only from ingress)
- Applies a `CiliumNetworkPolicy` (restrict ingress + allow DNS egress)

This is intentionally small and readable: it demonstrates **CRD modeling + reconciliation + RBAC**.

## Build/push

Update the image reference in `manifests/deployment.yaml`, then build and push:

```bash
docker build -t ghcr.io/<you>/security-profile-operator:0.1.0 operators/security-profile-operator
docker push ghcr.io/<you>/security-profile-operator:0.1.0
```

## Install (manual)

```bash
kubectl apply -k operators/security-profile-operator/manifests
kubectl apply -f operators/security-profile-operator/crd/examples/hello-nginx-securityprofile.yaml
```


