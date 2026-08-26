<?php

return [
    'realm_public_key' => env('KEYCLOAK_PUBLIC_KEY', null),

    'token_encryption_algorithm' => env('KEYCLOAK_ENCRYPTION_ALGORITHM', 'RS256'),

    'load_user_from_database' => env('KEYCLOAK_LOAD_USER_FROM_DATABASE', true),

    'user_provider_custom_retrieve_method' => null,

    'user_provider_credential' => env('KEYCLOAK_USER_PROVIDER_CREDENTIAL', 'email'),

    'token_principal_attribute' => env('KEYCLOAK_TOKEN_PRINCIPAL_ATTRIBUTE', 'email'),

    'append_decoded_token' => env('KEYCLOAK_APPEND_DECODED_TOKEN', false),

    'allowed_resources' => env('KEYCLOAK_ALLOWED_RESOURCES', null),

    'ignore_resources_validation' => env('KEYCLOAK_IGNORE_RESOURCES_VALIDATION', true),

    'leeway' => env('KEYCLOAK_LEEWAY', 60),

    'input_key' => env('KEYCLOAK_TOKEN_INPUT_KEY', null),

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
