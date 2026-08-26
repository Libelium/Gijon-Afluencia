# 2. Requisitos previos

## Herramientas (en tu equipo)

- `kubectl`, configurado y apuntando al clúster de destino (`kubectl config current-context`).
- `helm` 3.x.
- `bash`, `openssl` y `envsubst` (GNU gettext) — los necesita `scripts/generate-env.sh`.

## Requisitos del clúster

| Requisito | Para qué | Notas |
|-----------|----------|-------|
| Kubernetes ≥ 1.26 | Versiones de API del chart. | Cualquier distribución (k3s, EKS, AKS, GKE, OpenShift…). |
| CRDs de Gateway API ≥ v1.5.1, **solo el canal experimental** | El chart genera `HTTPRoute` y `TCPRoute`. | `TCPRoute` solo existe en el canal experimental, y Traefik 3.7 necesita `TLSRoute` en `v1` (disponible desde v1.5.0) o no programa nada, en silencio. No superpongas el canal estándar por debajo — véase [04-gateway-api.md](04-gateway-api.md). |
| Un controlador de Gateway y sus Gateways | Las rutas se enganchan a Gateways existentes. | Traefik, Istio, NGINX Gateway Fabric, Envoy Gateway, Cilium… |
| `metrics-server` | Solo si activas el HPA. | Opcional. |
| Operador KEDA | Solo si activas el autoescalado por cola. | Opcional. |
| CRDs del Prometheus Operator | Solo si activas `ServiceMonitor`. | Opcional. |

## Operadores para los charts de infraestructura incluidos

Instala solo los de los charts que vayas a usar de verdad (si apuntas a un servicio externo o
gestionado, sáltate su operador — véase [03-infrastructure.md](03-infrastructure.md)).

| Chart | Operador | Instalación |
|-------|----------|-------------|
| `charts/stackgres` | StackGres Operator | <https://stackgres.io/doc/latest/install/> |
| `charts/rabbitmq` | RabbitMQ **Cluster** Operator + **Messaging Topology** Operator | ver más abajo |
| `charts/mongodb` | ninguno (StatefulSet simple) | — |
| `charts/minio` | ninguno (dependencia de Helm) | `helm dependency update charts/minio` |

### Operadores de RabbitMQ

`charts/rabbitmq` necesita **dos** operadores:

- el **Cluster Operator** aporta el CRD `RabbitmqCluster`;
- el **Messaging Topology Operator** aporta los CRDs `User`, `Vhost` y `Permission` que el chart
  usa para declarar el usuario y el vhost de la aplicación. Sin él, la instalación falla con
  `no matches for kind "Vhost"/"User"/"Permission" ... ensure CRDs are installed first`.

El Topology Operator depende de **cert-manager** para su webhook de admisión.

```bash
# Cluster Operator
kubectl apply -f https://github.com/rabbitmq/cluster-operator/releases/latest/download/cluster-operator.yml

# cert-manager (requisito del Topology Operator)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.5/cert-manager.yaml
kubectl wait --for=condition=Available -n cert-manager --all deployment --timeout=180s

# Messaging Topology Operator
kubectl apply -f https://github.com/rabbitmq/messaging-topology-operator/releases/download/v1.14.0/messaging-topology-operator-with-certmanager.yaml
```

Comprueba que los CRDs están registrados antes de instalar el chart:

```bash
kubectl get crds | grep rabbitmq   # deben salir rabbitmqclusters, users, vhosts, permissions, …
```

## Acceso a las imágenes de contenedor

Las imágenes propias de la plataforma salen del registro que indiques en `IMAGE_REGISTRY` dentro
del `config.env` de tu entorno (se traslada a `global.imageRegistry`). Si requiere autenticación,
crea un Secret de tipo `docker-registry` en el namespace `pid-gijon` y decláralo en
`global.imagePullSecrets`. Las imágenes públicas (`quay.io/fiware/*`) no necesitan autenticación.

## Namespaces

Esta guía usa:
- `pid-gijon` — el namespace de la release de la plataforma,
- `gateway` — donde viven los Gateways,
- `postgres`, `mongodb`, `rabbitmq`, `minio` — los charts de infraestructura incluidos.

`helm install --create-namespace` los crea según haga falta.
