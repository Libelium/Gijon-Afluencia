<?php

return [

    // Administrador del broker que siembra MqttUserSeeder. Solo se guarda la derivacion de la
    // credencial (MQTT_ADMIN_PASSWORD_HASH), nunca material que permita reconstruirla.
    'admin' => [
        'username' => env('MQTT_ADMIN_USERNAME'),
        'password_hash' => env('MQTT_ADMIN_PASSWORD_HASH'),
    ],

];
