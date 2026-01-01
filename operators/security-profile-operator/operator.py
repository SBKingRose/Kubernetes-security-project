import kopf
from kubernetes import client, config


GROUP = "security.demo.cypher"
VERSION = "v1alpha1"
PLURAL = "securityprofiles"


def _load_kube():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()


def _apply_istio_policies(namespace: str, enable: bool):
    api = client.CustomObjectsApi()

    if not enable:
        return

    peerauth = {
        "apiVersion": "security.istio.io/v1beta1",
        "kind": "PeerAuthentication",
        "metadata": {"name": "default", "namespace": namespace},
        "spec": {"mtls": {"mode": "STRICT"}},
    }

    authz = {
        "apiVersion": "security.istio.io/v1beta1",
        "kind": "AuthorizationPolicy",
        "metadata": {"name": "allow-from-ingress", "namespace": namespace},
        "spec": {
            "selector": {"matchLabels": {"app.kubernetes.io/name": "hello-nginx"}},
            "action": "ALLOW",
            "rules": [
                {
                    "from": [
                        {
                            "source": {
                                "principals": [
                                    "cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account"
                                ]
                            }
                        }
                    ],
                    "to": [{"operation": {"methods": ["GET"], "paths": ["/"]}}],
                }
            ],
        },
    }

    # Create-or-patch semantics
    for obj in (peerauth, authz):
        g, v = obj["apiVersion"].split("/", 1)
        kind = obj["kind"]
        name = obj["metadata"]["name"]
        ns = obj["metadata"]["namespace"]
        plural = {
            "PeerAuthentication": "peerauthentications",
            "AuthorizationPolicy": "authorizationpolicies",
        }[kind]
        try:
            api.get_namespaced_custom_object(g, v, ns, plural, name)
            api.patch_namespaced_custom_object(g, v, ns, plural, name, obj)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                api.create_namespaced_custom_object(g, v, ns, plural, obj)
            else:
                raise


def _apply_cilium_policy(namespace: str, enable: bool):
    api = client.CustomObjectsApi()
    if not enable:
        return

    cnp = {
        "apiVersion": "cilium.io/v2",
        "kind": "CiliumNetworkPolicy",
        "metadata": {"name": "hello-nginx-restrict", "namespace": namespace},
        "spec": {
            "endpointSelector": {"matchLabels": {"app.kubernetes.io/name": "hello-nginx"}},
            "ingress": [
                {
                    "fromEndpoints": [
                        {
                            "matchLabels": {
                                "k8s:io.kubernetes.pod.namespace": "istio-system",
                                "app": "istio-ingressgateway",
                            }
                        }
                    ],
                    "toPorts": [{"ports": [{"port": "8080", "protocol": "TCP"}]}],
                }
            ],
            "egress": [
                {
                    "toEndpoints": [
                        {
                            "matchLabels": {
                                "k8s:io.kubernetes.pod.namespace": "kube-system",
                                "k8s-app": "kube-dns",
                            }
                        }
                    ],
                    "toPorts": [
                        {
                            "ports": [
                                {"port": "53", "protocol": "UDP"},
                                {"port": "53", "protocol": "TCP"},
                            ],
                            "rules": {"dns": [{"matchPattern": "*"}]},
                        }
                    ],
                }
            ],
        },
    }

    try:
        api.get_namespaced_custom_object("cilium.io", "v2", namespace, "ciliumnetworkpolicies", "hello-nginx-restrict")
        api.patch_namespaced_custom_object("cilium.io", "v2", namespace, "ciliumnetworkpolicies", "hello-nginx-restrict", cnp)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            api.create_namespaced_custom_object("cilium.io", "v2", namespace, "ciliumnetworkpolicies", cnp)
        else:
            raise


def _ensure_namespace_label(namespace: str, key: str, value: str):
    v1 = client.CoreV1Api()
    ns_obj = v1.read_namespace(namespace)
    labels = ns_obj.metadata.labels or {}
    if labels.get(key) == value:
        return
    labels[key] = value
    patch = {"metadata": {"labels": labels}}
    v1.patch_namespace(namespace, patch)


@kopf.on.startup()
def startup(**_):
    _load_kube()


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
def reconcile(spec, **_):
    namespace = spec.get("namespace", "hello-nginx")
    _ensure_namespace_label(namespace, "istio-injection", "enabled")

    _apply_istio_policies(namespace, bool(spec.get("istioStrictMtls", True)))
    _apply_cilium_policy(namespace, bool(spec.get("ciliumRestrictIngress", True)))

    return {"namespace": namespace, "status": "reconciled"}


