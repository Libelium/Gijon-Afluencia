<?php

return [

    // Proxies de los que se aceptan las cabeceras X-Forwarded-* (IP de origen y esquema), en
    // TRUSTED_PROXIES. Nunca un comodin: con '*' cualquiera puede falsear su IP.
    'proxies' => array_values(array_filter(array_map(
        'trim',
        explode(',', (string) env('TRUSTED_PROXIES', '127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16'))
    ))),

];
