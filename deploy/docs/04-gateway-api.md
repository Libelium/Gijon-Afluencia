# 4. Exponer servicios con la Gateway API

Este chart expone los servicios con la **Gateway API de Kubernetes** estándar
(`gateway.networking.k8s.io`). Es portable entre todos los controladores conformes: Traefik, Istio,
NGINX Gateway Fabric, Envoy Gateway, Cilium y otros.

## Reparto de responsabilidades

| Lo gestiona el equipo del clúster o de plataforma | Lo gestiona este chart |
|---------------------------------------------------|------------------------|
| `GatewayClass` | `HTTPRoute` (uno por componente) |
| Los recursos `Gateway`, sus listeners y el TLS | `TCPRoute`, si algún componente lo declara |
| El balanceador de carga y el punto de entrada | — |

El chart **nunca** crea Gateways ni balanceadores. La ruta de cada componente activado
simplemente se engancha a un Gateway que ya existe, por `name` y `namespace`.

## Qué debe aportar la infraestructura

> ¿Partes de un clúster vacío? Salta a
> [Montar un controlador desde cero: Traefik](#montar-un-controlador-desde-cero-traefik-ejemplo-completo)
> para una configuración completa de copiar y pegar, y vuelve aquí para los conceptos.

1. Los CRDs de la Gateway API instalados (v1 para `HTTPRoute`, v1alpha2 para `TCPRoute`).
2. Uno o varios recursos `Gateway` en el namespace de gateways (esta guía usa `gateway`). Un
   reparto habitual:
   - `public-gateway` — de cara a internet (API de web-back, Keycloak).
   - `internal-gateway` — interno del clúster o de la VPN (orion-ld, carrot).
3. En los Gateways con HTTPS, una **sección de listener** HTTPS cuyo nombre coincida con
   `gateway.httpsSectionName` (por defecto `https`), con TLS configurado (referencia a un
   certificado o cert-manager). El TLS termina en el Gateway; las rutas del chart solo referencian
   la sección.
4. **Enrutado entre namespaces permitido.** Las rutas se crean en el namespace de la release
   (`pid-gijon`), mientras que los Gateways viven en `gateway`. Por eso cada listener del Gateway
   debe permitir rutas desde el namespace de la release, por ejemplo:

   ```yaml
   listeners:
     - name: https
       protocol: HTTPS
       port: 443
       tls: { ... }
       allowedRoutes:
         namespaces:
           from: Selector
           selector:
             matchLabels:
               kubernetes.io/metadata.name: pid-gijon
   ```

   (Algunos controladores exigen además un `ReferenceGrant` para las referencias a backends de otro
   namespace; aquí las rutas referencian backends de su propio namespace, así que normalmente no
   hace falta.)

## Montar un controlador desde cero: Traefik (ejemplo completo)

Si tu clúster **no tiene nada** para la Gateway API, esta sección te lleva de cero a Gateways
funcionando con [Traefik](https://traefik.io) v3. Produce exactamente el Gateway que esperan las
rutas por defecto del generador: `public-gateway`, con una sección de listener `https`.

> Regla clave con Traefik: **el `port` de un listener del Gateway debe coincidir con el puerto del
> entryPoint de Traefik**. Abajo ejecutamos los entryPoints en los puertos reales `80` y `443` (con
> los puertos privilegiados vinculados mediante la capacidad `NET_BIND_SERVICE`, que el Pod Security
> Standard restringido permite), de modo que los puertos de los listeners se quedan en los
> convencionales `80/443`.

### Paso 1 — Instalar los CRDs de la Gateway API

**Solo el canal experimental, en la v1.5.1 o posterior.** Las dos mitades de esa frase importan, y
equivocarse en cualquiera de ellas falla en silencio:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/experimental-install.yaml
```

- **Solo el experimental.** Es un superconjunto del canal estándar y, desde la v1.5, la release
  incluye una `ValidatingAdmissionPolicy` llamada `safe-upgrades` que *rechaza* instalar CRDs
  experimentales encima de los estándar. Aplicar primero el canal estándar —como indican las
  instrucciones antiguas— hace que el segundo `apply` falle.
- **v1.5.1, no v1.1.** Traefik 3.7 (lo que instala hoy `helm install traefik`) vigila `TLSRoute` y
  `BackendTLSPolicy` en `v1`, y la v1.5.0 es la primera release que sirve `TLSRoute` ahí. Con
  cualquier versión anterior, los informers del proveedor de gateway nunca sincronizan: Traefik
  arranca sin ningún error visible y **nunca programa un Gateway**, la GatewayClass se queda en
  «Waiting for controller», y el único síntoma es una línea repetida
  `Failed to watch *v1.TLSRoute` en `kubectl logs -n gateway deploy/traefik`.

`TCPRoute`, que necesitarías si algún componente se expusiera por TCP, también existe solo en el
canal experimental: una razón más para instalar ese canal.

### Paso 2 — Instalar Traefik con el proveedor de Gateway API

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
kubectl create namespace gateway --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install traefik traefik/traefik -n gateway -f traefik-values.yaml --wait
```

`traefik-values.yaml`:

```yaml
# Activa el proveedor de Gateway API; la GatewayClass y los Gateways los creamos nosotros.
providers:
  kubernetesGateway:
    enabled: true
    # El canal experimental es el que sirve TLSRoute en v1, que es donde Traefik 3.7
    # lo vigila; sin él sus informers nunca sincronizan.
    experimentalChannel: true
  kubernetesIngress:
    enabled: false
gateway:
  enabled: false
gatewayClass:
  enabled: false

# Ejecuta los entryPoints en los puertos reales para que los listeners sean 80/443.
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
  type: LoadBalancer   # ¿bare metal? usa MetalLB, o pon type: NodePort
```

### Paso 3 — Crear la GatewayClass

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: traefik
spec:
  controllerName: traefik.io/gateway-controller
```

### Paso 4 — Certificado TLS para el listener HTTPS

Para una configuración rápida que funcione, crea un certificado comodín autofirmado (cambia el
dominio):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt \
  -subj "/CN=*.demo.example.com" \
  -addext "subjectAltName=DNS:*.demo.example.com,DNS:demo.example.com"
kubectl -n gateway create secret tls pid-gijon-wildcard-tls --cert=tls.crt --key=tls.key
```

> **En producción:** usa [cert-manager](https://cert-manager.io) — crea un `ClusterIssuer` (por
> ejemplo, Let's Encrypt) y un `Certificate` que escriba el secreto `pid-gijon-wildcard-tls` en el
> namespace `gateway`. No cambia nada más.

### Paso 5 — Crear los Gateways

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: public-gateway
  namespace: gateway
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
    - name: https                       # coincide con gateway.httpsSectionName
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - name: pid-gijon-wildcard-tls
            namespace: gateway
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              kubernetes.io/metadata.name: pid-gijon
```

> ¿Necesitas rutas solo internas (orion-ld, carrot)? Crea un `internal-gateway` igual que
> `public-gateway`. Para una separación pública/privada de verdad, levanta una segunda release de
> Traefik enganchada a un LoadBalancer interno (con las anotaciones de Service propias de tu nube)
> en vez de reutilizar esta.

### Paso 6 — Comprobar

```bash
kubectl get gateways -n gateway          # PROGRAMMED debe ser True
kubectl get svc -n gateway traefik       # anota la EXTERNAL-IP
```

Apunta tu DNS (o el `/etc/hosts`, para una prueba con certificado autofirmado) a esa IP externa
para los nombres de host de `config.env` (por ejemplo, `api.pid.gijon.example`,
`kc.pid.gijon.example`). Las rutas de pid-gijon-core se enganchan entonces a estos Gateways.

> Los demás controladores (Istio, NGINX Gateway Fabric, Envoy Gateway, Cilium) funcionan igual:
> instala el controlador, crea una `GatewayClass` con su `controllerName` y crea el mismo
> `public-gateway`. Solo cambian la instalación del controlador y la regla del puerto del listener.

## Configurar las rutas en tus valores

Las rutas se declaran por componente, en `components.<nombre>.gatewayAPI`:

```yaml
gateway:
  enabled: true
  namespace: gateway        # namespace padre por defecto de todas las rutas
  httpsSectionName: https   # nombre de la sección del listener HTTPS

components:
  webBack:
    gatewayAPI:
      enabled: true
      routes:
        - httpsOnly: true                 # engancharse a la sección `https`
          route:
            gateway: public-gateway       # nombre del Gateway padre
            # gatewayNamespace: gateway   # sobrescribe el namespace padre si hace falta
            hostnames: ["api.example.com"]
            backendPort: 80               # puerto del Service (por defecto, el primero)
```

### Campos de una ruta

| Campo | Se aplica a | Significado |
|-------|-------------|-------------|
| `gatewayKind` | ambas | `HTTP` (por defecto) o `TCP`. |
| `route.gateway` | ambas | Nombre del Gateway padre (**obligatorio**). |
| `route.gatewayNamespace` | ambas | Namespace padre; por defecto, `gateway.namespace`. |
| `route.hostnames` | HTTP | Lista de nombres de host que casa el `HTTPRoute`. |
| `route.backendPort` | ambas | Puerto del Service de destino; por defecto, el primero del componente. |
| `httpsOnly` | HTTP | Engancharse a la sección de listener `httpsSectionName`. |
| `path` / `pathType` | HTTP | Ruta que casar (por defecto, `/` con `PathPrefix`). |
| `route.sectionName` | TCP | Sección del listener TCP en el Gateway padre. |

### Ejemplo TCP

Ningún componente del chart usa hoy `TCPRoute`, y `k3s-bootstrap.sh` no crea un Gateway TCP. Si
añades uno que lo necesite, crea tú el Gateway con su listener TCP (igual que `public-gateway`, pero
con `protocol: TCP` y `kinds: [TCPRoute]`) y declara la ruta así:

```yaml
components:
  <tu-componente>:
    gatewayAPI:
      enabled: true
      routes:
        - gatewayKind: TCP
          route:
            gateway: tcp-gateway
            sectionName: <nombre-del-listener>   # debe existir en ese Gateway
            backendPort: 4000
```

## Comprobación

```bash
kubectl get httproute,tcproute -n pid-gijon
kubectl describe httproute web-back-http-route-0 -n pid-gijon
```

Mira las `status.parents[].conditions` de la ruta: `Accepted=True` y `ResolvedRefs=True` significan
que el controlador la ha enganchado correctamente al Gateway. Si `Accepted` es falso, las causas
habituales son: el nombre o el namespace del Gateway están mal, el `sectionName` del listener no
existe, o el `allowedRoutes` del listener no permite el namespace `pid-gijon`.
