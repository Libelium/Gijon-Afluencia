<?php

return [

    // Keycloak clients (token azp) allowed to JIT-provision a user.
    // SELF_PROVISIONING_CLIENTS env = JSON array of client ids; empty = none.
    'self_provisioning_clients' => json_decode(env('SELF_PROVISIONING_CLIENTS', '[]'), true) ?: [],

    // Role assigned to every self-provisioned user (grants its abilities). Empty = no role.
    'self_provisioning_role' => env('SELF_PROVISIONING_ROLE', ''),

    // Organization that self-provisioned users join, as JSON {"name": id} (the value/id is
    // what's used). Also the org that owns the public-incidents workspace.
    'self_provisioning_organization' => json_decode(env('SELF_PROVISIONING_ORGANIZATION', '{}'), true) ?: [],

];
