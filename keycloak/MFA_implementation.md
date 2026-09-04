# Doble factor por correo (2FA)

La imagen incluye la extensión [keycloak-2fa-email-authenticator](https://github.com/mesutpiskin/keycloak-2fa-email-authenticator),
compilada con Maven en el primer stage del `Dockerfile` y fijada al commit
`7dbcdf7`, la última versión compatible con Keycloak 25.x.

La extensión añade un paso de autenticación nuevo — *Email OTP* — que envía un código de un solo
uso al correo del usuario. Usando su variante **condicional** el segundo factor se exige solo a
quien tenga un rol determinado, en lugar de a todo el mundo.

La extensión se limita a **estar disponible** en la imagen: el flujo de autenticación se
configura desde la consola de administración y no viene activado en el realm exportado.

## Requisitos previos

1. **SMTP configurado**. En *Realm settings → Email* del realm hay que rellenar el servidor y el
   remitente. El `realm.json` deja ahí valores de ejemplo (`smtp.pid.gijon.example`), que hay que
   sustituir por los reales; sin un SMTP válido el código nunca sale.
2. **Un rol que active el 2FA**, por ejemplo `email_2fa_role`, creado en *Realm roles*. Se asigna
   a los usuarios que deban usar el segundo factor.

## Configuración del flujo

En *Authentication*:

1. Duplicar el flujo **browser** con un nombre propio.
2. Dentro del paso *… forms*, añadir **Conditional Email OTP** justo después de
   *Username Password Form* y marcarlo como **Required**.
3. En los ajustes del paso (*Conditional Email OTP config*) dar un alias y, en **Force OTP for
   Role**, seleccionar el rol del punto 2 de los requisitos. El selector filtra por roles de
   cliente: hay que cambiarlo a *Filter by realm roles*. Ahí se ajustan también la longitud del
   código (6 dígitos) y su caducidad (300 s).
4. Si existiera un paso *Browser - Conditional OTP* heredado y no se usa TOTP, eliminarlo.
5. **Bind flow** del flujo nuevo como *Browser flow*.

Variantes útiles:

- **Exceptuar a un grupo** (por ejemplo, cuentas de desarrollo): crear otro rol y seleccionarlo en
  **Skip OTP for Role**, dentro de la misma configuración del paso.
- **Obligatorio para todo el realm**: usar el paso **Email OTP** en lugar de
  **Conditional Email OTP**.

Con el flujo enlazado, un usuario con el rol recibe el código por correo y Keycloak le muestra la
vista `email-code-form.ftl` del tema para introducirlo.

## Temas

En *Realm settings → Themes* deben estar seleccionados `pidtheme` como **Login theme** y
**Email theme** (el `realm.json` ya lo deja así). El primero aporta la vista del código; el
segundo, el correo que lo transporta.

Un tema de Keycloak puede personalizar cuatro secciones — *login*, *account*, *admin* y *email* —;
aquí solo se personalizan **login** y **email**. La carpeta raíz del tema contiene un
`theme.properties` que declara su padre (`parent=keycloak`), y cada sección la suya:

```
pidtheme
├── email
│   ├── html            # plantillas .ftl del correo en HTML
│   ├── text            # las MISMAS plantillas .ftl en texto plano
│   ├── messages        # messages_<locale>.properties
│   └── theme.properties
├── login
│   ├── messages        # messages_<locale>.properties
│   ├── resources
│   │   ├── css
│   │   ├── img
│   │   ├── js
│   │   └── webfonts
│   ├── *.ftl           # plantillas de las vistas
│   └── theme.properties
└── theme.properties
```

Lo que no está en la carpeta se resuelve en el tema padre, así que solo hay que copiar los
ficheros que realmente se modifican. Las plantillas de referencia de esta versión están en
<https://github.com/keycloak/keycloak/tree/archive/release/25.0/themes/src/main/resources>.

Detalles a tener en cuenta:

- `login/theme.properties` declara los scripts (`scripts=js/…`), los estilos (`styles=css/…`) y
  pares clave-valor accesibles desde las plantillas como `${properties.<clave>}`.
- `email/html` y `email/text` deben contener **los mismos** nombres de fichero: si el cliente de
  correo no interpreta HTML, se entrega la versión de texto.
- Las vistas realmente sobrescritas hoy son `error.ftl`, `info.ftl`, `login.ftl`,
  `login-page-expired.ftl`, `login-reset-password.ftl`, `login-update-password.ftl`,
  `register.ftl`, `template.ftl` y `email-code-form.ftl` (esta última, de la extensión de 2FA).
- Tras tocar los `messages_*.properties`, `python3 i18n_validity_check.py` comprueba que ningún
  idioma se ha quedado sin una clave.
