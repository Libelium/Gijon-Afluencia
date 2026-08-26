# Plataforma PID Gijón — documentación

Documentación de referencia para desplegar la **plataforma PID Gijón** sobre cualquier
distribución de Kubernetes. El despliegue tiene tres capas, que se aplican en este orden:

1. **Configuración del clúster** — operadores, CRDs de Gateway API, un controlador de gateway.
2. **Bases de datos y broker** — PostgreSQL, MongoDB, RabbitMQ, almacenamiento de objetos.
3. **pid-gijon-core** — los componentes de aplicación de la plataforma (se despliegan al final).

> El recorrido paso a paso está en [../README.md](../README.md). Las páginas de aquí son la
> **referencia** de cada tema y de sus alternativas (por ejemplo, usar una base de datos
> gestionada en vez del chart incluido).

## Páginas

| # | Documento | Qué cubre |
|---|-----------|-----------|
| 1 | [01-overview.md](01-overview.md) | Componentes y cómo se comunican entre sí. |
| 2 | [02-prerequisites.md](02-prerequisites.md) | Herramientas, requisitos del clúster, operadores y controladores. |
| 3 | [03-infrastructure.md](03-infrastructure.md) | Despliegue de los charts de bases de datos, broker y almacenamiento, y cómo sustituirlos por servicios externos o gestionados. |
| 4 | [04-gateway-api.md](04-gateway-api.md) | Exposición de servicios mediante la Gateway API de Kubernetes. |
| 5 | [05-secrets.md](05-secrets.md) | Cómo se suministran los secretos y cuáles necesita cada componente. |
| 6 | [06-post-install.md](06-post-install.md) | Configuración manual de una sola vez: realm y clientes de Keycloak. |
| 7 | [07-apisix.md](07-apisix.md) | Pasarela APISIX opcional delante de los endpoints FIWARE (hay que activarla expresamente). |

Véase también [../SECURITY.md](../SECURITY.md) para la estrategia de gestión de secretos.

## Estructura del repositorio

```
charts/                 Charts de Helm: pid-gijon-core + stackgres, mongodb, rabbitmq, minio, apisix (opcional).
scripts/                generate-env.sh (+ plantillas de valores) — crea un entorno.
environments/           Configuración por despliegue y valores generados (solo se versiona example/).
docs/                   Esta documentación.
tests/                  Batería de verificación posterior a la instalación (./tests/run-tests.sh <entorno>).
build-images.sh         Construye y publica las imágenes de la plataforma.
k3s-bootstrap.sh        Prepara un host k3s de un solo nodo (CRDs, controlador, Gateways, operadores).
k3s-deploy.sh           Ejecuta el generador y las instalaciones de helm en orden.
docker-compose.core.yml Las dependencias de terceros, para desarrollo local.
```
