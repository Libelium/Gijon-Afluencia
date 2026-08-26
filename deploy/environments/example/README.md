# environments/

Cada despliegue («entorno») vive en su propia carpeta aquí. Solo se versiona esta carpeta
`example/`, que contiene la plantilla de entrada:

- **`config.env.example`** — los ajustes no secretos que tienes que editar.

## Crear un entorno

```bash
./scripts/generate-env.sh <nombre>      # 1) crea environments/<nombre>/config.env
# edita environments/<nombre>/config.env
./scripts/generate-env.sh <nombre>      # 2) genera los ficheros de valores y SECRETS.env
```

Esto produce (todo **excluido de git**):

```
environments/<nombre>/
  config.env              tus ajustes ya editados
  SECRETS.env             todas las contraseñas y claves generadas (guárdalo en una bóveda, chmod 600)
  stackgres.values.yaml   ┐
  mongodb.values.yaml     │ valores de Helm listos para usar, con las contraseñas
  rabbitmq.values.yaml    │ enlazadas de forma coherente en todos los charts
  minio.values.yaml       │ (se omite cuando STORAGE_TYPE=s3)
  pid-gijon-core.values.yaml ┘
  tests.env               configuración ya preparada para la batería de verificación
```

Volver a ejecutar el generador es seguro: reutiliza las contraseñas que ya estén en `SECRETS.env`,
de modo que solo genera los campos nuevos.

No versiones nada que no sea `example/` — véase [../../SECURITY.md](../../SECURITY.md).
