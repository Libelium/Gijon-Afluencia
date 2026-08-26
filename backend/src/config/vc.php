<?php

return [
    'verifier_host' => env('VC_VERIFIER_HOST'),
    'token_path' => env('VC_VERIFIER_TOKEN_PATH', '/token'),
    'jwks_path' => env('VC_VERIFIER_JWKS_PATH', '/.well-known/jwks'),
    'client_id' => env('VC_CLIENT_ID'),
    'scope' => env('VC_SCOPE', 'operator'),
    'credential_type' => env('VC_CREDENTIAL_TYPE'),
    'role_target' => env('VC_ROLE_TARGET'),
];
