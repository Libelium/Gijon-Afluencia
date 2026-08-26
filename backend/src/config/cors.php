<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Cross-Origin Resource Sharing (CORS) Configuration
    |--------------------------------------------------------------------------
    |
    | Here you may configure your settings for cross-origin resource sharing
    | or "CORS". This determines what cross-origin operations may execute
    | in web browsers. You are free to adjust these settings as needed.
    |
    | To learn more: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
    |
    */

    'paths' => ['api/*'],

    'allowed_methods' => ['*'],

    /*
    | Allowlist of trusted frontend origins. Primary source is FRONTEND_URL. Extra
    | origins may be appended via CORS_ALLOWED_ORIGINS (both comma-separated).
    | Never use '*'.
    */
    'allowed_origins' => array_values(array_unique(array_filter(array_map(
        'trim',
        array_merge(
            explode(',', (string) env('FRONTEND_URL', '')),
            explode(',', (string) env('CORS_ALLOWED_ORIGINS', ''))
        )
    )))),

    'allowed_origins_patterns' => array_values(array_filter(array_map(
        'trim',
        explode(',', (string) env('CORS_ALLOWED_ORIGIN_PATTERNS', ''))
    ))),

    'allowed_headers' => ['*'],

    'exposed_headers' => ['X-Permissions'],

    'max_age' => 0,

    'supports_credentials' => false,

];
