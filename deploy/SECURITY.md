# Seguridad y gestión de secretos

Este kit de despliegue está pensado para poder publicarse sin riesgo: **no contiene ninguna
credencial.** Toda contraseña, clave y token está vacío, es un marcador `<CHANGE_ME>` o se genera
en el momento del despliegue dentro de una carpeta de entorno excluida de git.

## Reglas de oro

1. **Nunca subas un secreto.** Ni en `values.yaml`, ni en la documentación, ni en un ejemplo.
2. Las credenciales reales viven solo en `environments/<nombre>/` (excluido de git) o en tu gestor
   de secretos — nunca en los valores por defecto del chart ni en el `environments/example/` que
   sí se versiona.
3. Rota cualquier credencial que se haya expuesto alguna vez (registros, capturas de pantalla, un
   `git add` equivocado).

## Cómo llegan los secretos al clúster

Elige una estrategia. Son compatibles entre sí, componente a componente.

### 1. Entorno generado (por defecto, la más sencilla)

`scripts/generate-env.sh <nombre>` crea `environments/<nombre>/` con contraseñas nuevas y únicas,
enlazadas de forma coherente en todos los charts, más un `SECRETS.env` maestro; `k3s-deploy.sh`
añade un `keycloak-secrets.env` con los dos secretos de cliente de Keycloak. Estos ficheros están
excluidos de git. Despliega con `helm install -f environments/<nombre>/<chart>.values.yaml`.
Guarda `SECRETS.env` en tu gestor de contraseñas o bóveda y borra las copias locales al terminar.

### 2. External Secrets Operator (recomendada para GitOps y producción)

Pon `secretsStrategy.type: external` en `pid-gijon-core` y crea los Secrets referenciados con
[External Secrets Operator](https://external-secrets.io/) respaldado por Vault, AWS Secrets
Manager, GCP Secret Manager, etc. El chart entonces referencia Secrets existentes por nombre y no
genera ninguno. Véase [docs/05-secrets.md](docs/05-secrets.md).

### 3. Sealed Secrets

Cifra los Secrets con [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) y versiona
los recursos `SealedSecret` *cifrados*. Se pueden guardar en git sin riesgo.

### 4. `--set` en el momento de instalar

Pasa los valores directamente en la línea de comandos de Helm desde el almacén de secretos de tu
CI/CD (`--set credentials.password="$RABBITMQ_PASSWORD"`). Asegúrate de que tu CI enmascara los
valores en los registros.

## Higiene antes de cada commit

Antes de cada commit:

```bash
git diff --cached            # revisar a ojo que no hay secretos
```

Añade un escáner automático para cazar los descuidos:

- [`gitleaks`](https://github.com/gitleaks/gitleaks): `gitleaks protect --staged`
- [`detect-secrets`](https://github.com/Yelp/detect-secrets) como hook de pre-commit
- [`git-secrets`](https://github.com/awslabs/git-secrets) para los patrones de claves de AWS

## Qué se puede versionar y qué no

| Se puede | No se puede |
|----------|-------------|
| `charts/**` (campos de credenciales vacíos o con marcadores) | Cualquier contraseña, clave o token real |
| `environments/example/**` (solo marcadores) | `environments/<nombre>/**` (generado) |
| `SECURITY.md`, `docs/**`, `README.md` | `SECRETS.env`, `*.env` |

## Cómo comunicar una vulnerabilidad

El procedimiento está en el [`SECURITY.md`](../SECURITY.md) de la raíz del repositorio. En corto:
**no abras una incidencia pública**.
