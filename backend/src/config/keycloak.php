<?php

return [
    'url' => env('KEYCLOAK_URL'),

    'realm' => env('KEYCLOAK_REALM'),

    'client_id' => env('KEYCLOAK_CLIENT_ID'),

    'client_secret' => env('KEYCLOAK_CLIENT_SECRET'),

    'redirect_uri' => env('KEYCLOAK_REDIRECT_URI'),

    'frontend_client_id' => env('KEYCLOAK_FRONTEND_CLIENT_ID', 'pid-gijon-client'),

    // Destino al que Keycloak devuelve al usuario tras las acciones de cuenta (reset de clave).
    'frontend_url' => env('FRONTEND_URL'),

    'realm_public_key' => env('KEYCLOAK_PUBLIC_KEY', null),

    'token_encryption_algorithm' => env('KEYCLOAK_ENCRYPTION_ALGORITHM', 'RS256'),

    'load_user_from_database' => env('KEYCLOAK_LOAD_USER_FROM_DATABASE', true),

    'user_provider_custom_retrieve_method' => null,

    'user_provider_credential' => env('KEYCLOAK_USER_PROVIDER_CREDENTIAL', 'email'),

    'token_principal_attribute' => env('KEYCLOAK_TOKEN_PRINCIPAL_ATTRIBUTE', 'email'),

    'append_decoded_token' => env('KEYCLOAK_APPEND_DECODED_TOKEN', false),

    // Recursos exigidos en resource_access, separados por comas. Vacio a proposito: cruza roles
    // de cliente, que este realm no define; quien restringe por cliente es allowed_clients.
    'allowed_resources' => env('KEYCLOAK_ALLOWED_RESOURCES', null),

    'ignore_resources_validation' => env('KEYCLOAK_IGNORE_RESOURCES_VALIDATION', true),

    // Clientes emisores (claim azp) admitidos, separados por comas: la clave publica es la del
    // realm, asi que sin esto vale cualquier token del realm. ExtendedKeycloakGuard le suma
    // client_id, frontend_client_id y provisioning.self_provisioning_clients; vacia no restringe.
    'allowed_clients' => env('KEYCLOAK_ALLOWED_CLIENTS'),

    'leeway' => env('KEYCLOAK_LEEWAY', 60),

    'input_key' => env('KEYCLOAK_TOKEN_INPUT_KEY', null),

    'admin' => [
        'client' => env('KC_ADMIN_CLIENT'),
        'username' => env('KC_ADMIN_USER'),
        'password' => env('KC_ADMIN_PASSWORD'),
        'realm' => env('KC_MASTER_REALM'),
    ],

    'impersonation' => [
        'client' => env('KC_IMPERSONATION_CLIENT_ID'),
        'secret' => env('KC_IMPERSONATION_CLIENT_SECRET'),
        'username' => env('KC_IMPERSONATION_USERNAME'),
        'password' => env('KC_IMPERSONATION_PASSWORD'),
        'url' => env('KC_IMPERSONATION_URL'),
        'realm' => env('KC_IMPERSONATION_REALM')
    ],

    'mfa_role_name' => env('KEYCLOAK_MFA_ROLE_NAME', 'mail-mfa'),
];
