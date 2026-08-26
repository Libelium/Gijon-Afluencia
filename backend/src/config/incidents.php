<?php

return [

    // Public-incidents shared workspace name; empty/unset = feature off. Its org is the
    // self-provisioning org (provisioning.self_provisioning_organization).
    'public_workspace' => env('PUBLIC_INCIDENTS_WORKSPACE'),

    // Reviewers workspace name; members hold incidents.review and receive every incident.
    // Empty/unset = off.
    'reviewers_workspace' => env('REVIEWERS_INCIDENTS_WORKSPACE'),

    // Role forced on operator users created via incidents.admin. Must match a role seeded by
    // PermissionsSyncSeeder.
    'operator_role' => env('OPERATOR_ROLE'),

];
