<?php

namespace App\Services;

use App\Authorization\AppResourcePermission;
use App\Models\User;
use Spatie\Permission\Models\Role;

class UserProvisioningService
{
    /**
     * JIT-provision a self-registered user from $profile. Returns null if the token has no email.
     */
    public static function ensureUserProvisioned(object $decodedToken, array $profile = []): ?User
    {
        $email = strtolower($decodedToken->email ?? '');
        if ($email === '') {
            return null;
        }

        // users.name = First Name + Last Name (given_name + family_name claims), not the
        // username (= email). Falls back to the full name claim, then the email.
        $given = trim($decodedToken->given_name ?? '');
        $family = trim($decodedToken->family_name ?? '');
        $name = trim($given . ' ' . $family);
        if ($name === '') {
            $name = $decodedToken->name ?? $email;
        }
        $keycloakClientId = $decodedToken->sub ?? '';
        $organizationId = $profile['organization_id'] ?? null;
        $existing = User::where('email', $email)->first();
        if ($existing) {
            return $existing->keycloak_client_id === $keycloakClientId ? $existing : null;
        }

        $user = User::create([
            'email' => $email,
            'name' => $name,
            'keycloak_client_id' => $keycloakClientId,
            'organization_id' => $organizationId,
            'created_by' => null,
            'enabled' => true,
        ]);

        // Resource permissions over the user's own record only.
        $user->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $user, true);

        // Assign the role configured for this client, if any.
        $roleName = $profile['role'] ?? null;
        if ($roleName) {
            $role = Role::where('name', $roleName)->whereNull('organization_id')->first();
            if ($role) {
                $user->assignRole($role);
            }
        }

        // Add the new citizen to the public-incidents workspace. No-op unless the feature is
        // enabled via env (PUBLIC_INCIDENTS_WORKSPACE + SELF_PROVISIONING_ORGANIZATION).
        PublicIncidentsWorkspaceService::addUser($user);

        try {
            (new \App\Helpers\UserLocaleSyncHelper())->syncUserLocale($user);
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::warning('locale.sync.provision.failed', [
                'user_id' => $user->id,
                'error' => $e->getMessage(),
            ]);
        }

        return $user;
    }
}
