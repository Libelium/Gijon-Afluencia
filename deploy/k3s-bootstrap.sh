#!/usr/bin/env bash
#
# Prepare a single-node k3s host for the platform.
#
# This automates step 2 of deploy/README.md — k3s itself, the Gateway API CRDs,
# a Traefik gateway controller, the Gateways, and the operators the bundled data
# charts need. It stops before the platform itself: the generator and the helm
# installs are run by deploy/k3s-deploy.sh.
#
#   deploy/k3s-bootstrap.sh --domain pid.gijon.example
#   deploy/k3s-bootstrap.sh --domain pid.gijon.example --skip-k3s
#   deploy/k3s-bootstrap.sh --domain pid.gijon.example --dry-run
#
# Idempotent: re-running it converges rather than failing.
#
# NOT VERIFIED AGAINST A REAL CLUSTER. Written from the deployment docs and
# validated statically; the first real run is expected to need fixes.

set -euo pipefail

DOMAIN=""; SKIP_K3S=0; DRY=0
GATEWAY_NS="gateway"
GATEWAY_API_VERSION="v1.5.1"
CERT_MANAGER_VERSION="v1.14.5"
RMQ_TOPOLOGY_VERSION="v1.14.0"

log()  { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }
run()  { if [[ $DRY -eq 1 ]]; then printf '  + %s\n' "$*"; else "$@"; fi; }
apply(){ if [[ $DRY -eq 1 ]]; then printf '  + kubectl apply -f - <<manifest\n'; cat; else kubectl apply -f -; fi; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)   DOMAIN="$2"; shift ;;
    --skip-k3s) SKIP_K3S=1 ;;
    --dry-run)  DRY=1 ;;
    -h|--help)  sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

[[ -n "$DOMAIN" ]] || die "--domain is required (e.g. --domain pid.gijon.example)"

# --------------------------------------------------------------- 1. k3s ---
if [[ $SKIP_K3S -eq 0 ]]; then
  if command -v kubectl >/dev/null 2>&1 && kubectl get nodes >/dev/null 2>&1; then
    log "A reachable cluster already exists — skipping the k3s install"
  else
    log "Installing k3s"
    # Traefik is disabled on purpose. k3s bundles Traefik as an *ingress*
    # controller; the platform uses the Gateway API, so we install our own Traefik
    # release below with the kubernetesGateway provider enabled. Leaving the
    # bundled one in place gives you two Traefiks fighting over ports 80/443.
    run bash -c "curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC='--disable traefik' sh -"
    run bash -c 'mkdir -p "$HOME/.kube" && sudo cat /etc/rancher/k3s/k3s.yaml > "$HOME/.kube/config" && chmod 600 "$HOME/.kube/config"'
    export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
  fi
fi

[[ $DRY -eq 1 ]] || kubectl get nodes >/dev/null 2>&1 || die "no reachable cluster; check KUBECONFIG"

if ! command -v helm >/dev/null 2>&1; then
  log "Installing helm"
  run bash -c "curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
fi

# ------------------------------------------------- 2. Gateway API CRDs ---
# The experimental channel only, deliberately, and pinned to >= v1.5.
#
# Only experimental: it is a superset of standard, and from v1.5 the release
# ships a ValidatingAdmissionPolicy ("safe-upgrades") that *rejects* installing
# experimental CRDs over standard ones. Applying both, as the upstream docs
# describe, now fails on the second apply.
#
# >= v1.5: Traefik 3.7 watches TLSRoute and BackendTLSPolicy at v1, and v1.5.0
# is the first release that serves TLSRoute there (v1.4 has BackendTLSPolicy v1
# but not TLSRoute). On anything older the gateway provider's informers never
# sync, so it starts, logs nothing useful, and silently never programs a
# Gateway — GatewayClass sits at "Waiting for controller" forever.
log "Installing the Gateway API CRDs ($GATEWAY_API_VERSION, experimental channel)"
# --server-side is required, not a preference: client-side apply stores the whole
# manifest in the last-applied-configuration annotation, and the experimental
# HTTPRoute CRD alone is over the 256 KiB annotation limit. A plain apply dies
# with `metadata.annotations: Too long` *after* creating some of the CRDs, so the
# failure looks partial and re-running does not fix it.
run kubectl apply --server-side --force-conflicts -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/$GATEWAY_API_VERSION/experimental-install.yaml"

# ---------------------------------------------- 3. Traefik + Gateways ---
log "Installing Traefik with the Gateway API provider"
run kubectl create namespace "$GATEWAY_NS" --dry-run=client -o yaml >/dev/null 2>&1 || true
if [[ $DRY -eq 0 ]]; then
  kubectl create namespace "$GATEWAY_NS" 2>/dev/null || true
fi

TRAEFIK_VALUES="$(mktemp)"
cat > "$TRAEFIK_VALUES" <<'YAML'
providers:
  kubernetesGateway:
    enabled: true
    # The experimental channel is what serves TLSRoute at v1; Traefik 3.7 watches
    # it there and its informers never sync without it (see docs/04-gateway-api.md).
    experimentalChannel: true
  kubernetesIngress:
    enabled: false
gateway:
  enabled: false
gatewayClass:
  enabled: false
securityContext:
  capabilities:
    add: ["NET_BIND_SERVICE"]
    drop: ["ALL"]
  readOnlyRootFilesystem: true
ports:
  web:
    port: 80
    exposedPort: 80
  websecure:
    port: 443
    exposedPort: 443
service:
  # k3s ships ServiceLB (klipper), so a LoadBalancer Service is fulfilled with
  # the node's own IP on a single-node host. No MetalLB needed.
  type: LoadBalancer
YAML
run helm repo add traefik https://traefik.github.io/charts
run helm repo update
run helm upgrade --install traefik traefik/traefik -n "$GATEWAY_NS" --create-namespace -f "$TRAEFIK_VALUES" --wait
rm -f "$TRAEFIK_VALUES"

log "Creating the GatewayClass"
apply <<'YAML'
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: traefik
spec:
  controllerName: traefik.io/gateway-controller
YAML

log "Creating a self-signed wildcard certificate for *.$DOMAIN"
if [[ $DRY -eq 1 ]]; then
  echo "  + openssl req -x509 ... -subj '/CN=*.$DOMAIN'"
  echo "  + kubectl -n $GATEWAY_NS create secret tls pid-gijon-wildcard-tls ..."
elif kubectl -n "$GATEWAY_NS" get secret pid-gijon-wildcard-tls >/dev/null 2>&1; then
  echo "  pid-gijon-wildcard-tls already exists — leaving it alone"
else
  TLSDIR="$(mktemp -d)"
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$TLSDIR/tls.key" -out "$TLSDIR/tls.crt" \
    -subj "/CN=*.$DOMAIN" \
    -addext "subjectAltName=DNS:*.$DOMAIN,DNS:$DOMAIN" 2>/dev/null
  kubectl -n "$GATEWAY_NS" create secret tls pid-gijon-wildcard-tls \
    --cert="$TLSDIR/tls.crt" --key="$TLSDIR/tls.key"
  rm -rf "$TLSDIR"
  warn "Self-signed certificate. Clients must skip verification, or replace this"
  warn "secret with a real one (cert-manager is installed below)."
fi

log "Creating the Gateways"
apply <<YAML
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: public-gateway
  namespace: $GATEWAY_NS
spec:
  gatewayClassName: traefik
  listeners:
    - name: web
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              kubernetes.io/metadata.name: pid-gijon
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - name: pid-gijon-wildcard-tls
            namespace: $GATEWAY_NS
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              kubernetes.io/metadata.name: pid-gijon
YAML

# The Gateways select routes from a namespace labelled with its own name, and
# k8s only sets kubernetes.io/metadata.name automatically on namespace creation.
log "Creating the pid-gijon namespace"
if [[ $DRY -eq 0 ]]; then
  kubectl create namespace pid-gijon 2>/dev/null || true
  kubectl label namespace pid-gijon kubernetes.io/metadata.name=pid-gijon --overwrite >/dev/null
else
  echo "  + kubectl create namespace pid-gijon"
fi

# ------------------------------------------------------- 4. Operators ---
log "Installing the StackGres operator (PostgreSQL)"
run helm repo add stackgres https://stackgres.io/downloads/stackgres-k8s/stackgres/helm/
run helm repo update
run helm upgrade --install stackgres-operator stackgres/stackgres-operator \
  -n stackgres-system --create-namespace --wait

log "Installing cert-manager ($CERT_MANAGER_VERSION)"
run kubectl apply --server-side --force-conflicts -f "https://github.com/cert-manager/cert-manager/releases/download/$CERT_MANAGER_VERSION/cert-manager.yaml"
run kubectl wait --for=condition=Available -n cert-manager --all deployment --timeout=300s

log "Installing the RabbitMQ operators"
run kubectl apply --server-side --force-conflicts -f https://github.com/rabbitmq/cluster-operator/releases/latest/download/cluster-operator.yml
run kubectl apply --server-side --force-conflicts -f "https://github.com/rabbitmq/messaging-topology-operator/releases/download/$RMQ_TOPOLOGY_VERSION/messaging-topology-operator-with-certmanager.yaml"

# ----------------------------------------------------------- 5. Report ---
# Finishing green with a dead gateway is the worst outcome here: every route the
# platform creates would be accepted by the API server and served by nobody. So
# this blocks until the controller has actually adopted the GatewayClass and
# programmed the public Gateway, and fails loudly if it never does.
log "Waiting for the GatewayClass to be Accepted and public-gateway Programmed"
if [[ $DRY -eq 0 ]]; then
  ok=0
  for _ in $(seq 1 60); do
    if [[ "$(kubectl get gatewayclass traefik -o jsonpath='{.status.conditions[?(@.type=="Accepted")].status}' 2>/dev/null)" == "True" ]] \
    && [[ "$(kubectl get gateway public-gateway -n "$GATEWAY_NS" -o jsonpath='{.status.conditions[?(@.type=="Programmed")].status}' 2>/dev/null)" == "True" ]]; then
      ok=1; break
    fi
    sleep 5
  done
  if [[ $ok -eq 0 ]]; then
    kubectl get gatewayclass traefik -o wide 2>/dev/null || true
    kubectl get gateways -n "$GATEWAY_NS" -o wide 2>/dev/null || true
    warn "The gateway was never programmed (waited 5 minutes). Look here first:"
    warn "  kubectl logs -n $GATEWAY_NS deploy/traefik | grep -i 'failed to watch'"
    warn "A repeating \"Failed to watch *v1.TLSRoute\" line means the Gateway API"
    warn "CRDs are older than the controller expects: Traefik 3.7 watches TLSRoute"
    warn "and BackendTLSPolicy at v1, and only Gateway API >= v1.5.0 serves them"
    warn "there. The provider then starts cleanly and silently programs nothing."
    warn "Re-apply the CRDs (experimental channel only) and restart Traefik:"
    warn "  kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/$GATEWAY_API_VERSION/experimental-install.yaml"
    warn "  kubectl rollout restart -n $GATEWAY_NS deploy/traefik"
    die "gateway not Programmed"
  fi
  log "GatewayClass Accepted, public-gateway Programmed"
fi

log "Done"
if [[ $DRY -eq 0 ]]; then
  echo
  kubectl get gatewayclass
  kubectl get gateways -n "$GATEWAY_NS"
  EXTIP="$(kubectl get svc -n "$GATEWAY_NS" traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  echo
  echo "Gateway external IP: ${EXTIP:-<pending>}"
  echo
  echo "Point DNS (or /etc/hosts) for these at that IP:"
  # One label deep, so the *.$DOMAIN wildcard certificate created above covers
  # them. k3s-deploy.sh pins the same names into the generated config.env.
  for h in api kc app fiware; do echo "  $h.$DOMAIN"; done
fi
cat <<EOF

Next: deploy the platform.

  deploy/k3s-deploy.sh --env demo --domain $DOMAIN --registry <your-registry>

or follow deploy/README.md and run the generator and the helm installs by hand.
EOF
