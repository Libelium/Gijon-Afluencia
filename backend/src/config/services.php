<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'mailgun' => [
        'domain' => env('MAILGUN_DOMAIN'),
        'secret' => env('MAILGUN_SECRET'),
        'endpoint' => env('MAILGUN_ENDPOINT', 'api.mailgun.net'),
        'scheme' => 'https',
    ],

    'postmark' => [
        'token' => env('POSTMARK_TOKEN'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'sparkpost' => [
        'secret' => env('SPARKPOST_SECRET'),
    ],

    'stripe' => [
        'model' => App\Models\User::class,
        'key' => env('STRIPE_KEY'),
        'secret' => env('STRIPE_SECRET'),
    ],

    'googlemaps' => [
        'key' => env('GOOGLE_MAPS_KEY')
    ],

    'aether-link' => [
        'time-series' => env('AETHER_LINK_URL') . "/api/v1/time-series/",
        'subscription-types' => env('AETHER_LINK_URL') . "/api/v1/context-broker/platformTypeSubscriptions",
        'data-types' => env('AETHER_LINK_URL') . "/api/v1/context-broker/dataTypes",
        'entity' => [
            'update' => env('AETHER_LINK_URL') . "/api/v1/context-broker/entities/update",
            'create' => env('AETHER_LINK_URL') . "/api/v1/context-broker/entities/create",
            'delete' => env('AETHER_LINK_URL') . "/api/v1/context-broker/entities/delete",
            'delete-attribute' => env('AETHER_LINK_URL') . "/api/v1/context-broker/entities",
        ],
        'iota' => [
            'services' => env('AETHER_LINK_URL') . "/api/v1/iota/services",
            'provision-service' => env('AETHER_LINK_URL') . "/api/v1/iota/provision/service",
            'provision-device' => env('AETHER_LINK_URL') . "/api/v1/iota/provision/device",
            'delete-device' => env('AETHER_LINK_URL') . "/api/v1/iota/devices",
        ]
    ],

    'queues-consumer' => [
        'publish' => env('QUEUES_CONSUMER_API_URL') . "/publish",
        // Secreto compartido con queues-consumer. El consumer es fail-closed:
        // sin cabecera X-Queues-Consumer-Token responde 401, y si el secreto no
        // esta configurado en su lado responde 503 (GDTIS-PT01-SEC-017).
        'token' => env('QUEUES_CONSUMER_API_TOKEN'),
    ],

    'generative_api' => [
        'base' => env('GENERATIVE_API_URL'),
        'generate' => env('GENERATIVE_API_URL') . "/api/generate",
        'chat' => env('GENERATIVE_API_URL') . "/api/chat",
        'list' => env('GENERATIVE_API_URL') . "/api/list",
    ],
    'api-gateway' => [
        'secret' => env('API_GATEWAY_SECRET'),
    ],
    'data-report' => [
        'base' => env('DATA_REPORT', ''),
        // Externally-reachable Fiware Manager URL (for the browser: device simulator command-proxy).
        // Falls back to DATA_REPORT if unset.
        'external' => env('DATA_REPORT_EXTERNAL', env('DATA_REPORT', '')),
    ],
    'dlm' => [
        'base_url'              => env('DLM_BASE_URL'),
        'token'                 => env('DLM_TOKEN'),
        'timeout'               => env('DLM_TIMEOUT', 15),
        'stripe_payment_method' => env('DLM_STRIPE_PAYMENT_METHOD_PATH', '/api/V1/stripe/payment-method'),
    ],

    'chatbot' => [
        'base_url' => env('CHATBOT_API_URL', 'http://chatbot:8000'),
        'timeout'  => env('CHATBOT_TIMEOUT', 300),
    ],

    'statuscake' => [
        'api_key' => env('STATUSCAKE_API_KEY'),
    ],

    'telegram' => [
        'client_id' => env('TELEGRAM_CLIENT_ID'),
        'enabled' => env('TELEGRAM_ENABLED', false),
    ],

    'sms' => [
        'enabled' => env('SMS_ENABLED', false),
    ],

    'whatsapp' => [
        'enabled' => env('WHATSAPP_ENABLED', false),
    ],

    'push-notifications' => [
        'enabled' => env('PUSH_NOTIFICATIONS_ENABLED', false),
    ],

];
