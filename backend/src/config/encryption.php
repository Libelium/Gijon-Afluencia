<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Encryption Master Key
    |--------------------------------------------------------------------------
    |
    | This master key is used to encrypt/decrypt sensitive data stored in the
    | database. It must be a 32-byte (256-bit) key in base64 format.
    |
    | To generate a new key, run:
    | php -r "echo 'base64:' . base64_encode(random_bytes(32)) . PHP_EOL;"
    |
    */

    'master_key' => env('ENCRYPTION_ENTITIES_KEY'),

    'generic_key' => env('GENERIC_ENCRYPTION_KEY'),

    /*
    |--------------------------------------------------------------------------
    | Encryption Algorithm
    |--------------------------------------------------------------------------
    |
    | Encryption algorithm used. Default is AES-256-GCM which is an
    | AEAD (Authenticated Encryption with Associated Data) algorithm that
    | provides both confidentiality and authenticity.
    |
    */

    'algorithm' => 'AES-256-GCM',

];
