<?php

namespace App\Helpers;

use App\Models\Organization;
use App\Models\Preference;
use App\Models\Preferencable;
use App\Models\User;
use App\Traits\KeycloakHelper;
use Illuminate\Support\Facades\Log;

class MfaRoleSyncHelper
{
    use KeycloakHelper;

    private function getMfaRoleName(): string
    {
        return config('keycloak.mfa_role_name');
    }

    /**
     * Sync MFA role for all users in the organization.
     * When org MFA is activated: all users get MFA enabled (Keycloak role + user preference)
     * When org MFA is deactivated: users keep their MFA active, but can now disable it individually
     */
    public function syncOrganizationMfaRole(Organization $organization, bool $mfaActive): void
    {
        $users = $organization->users()->whereNotNull('keycloak_client_id')->get();

        foreach ($users as $user) {
            if ($mfaActive) {
                // Org enables MFA: activate for all users and set their preference
                $this->syncUserMfaRole($user, true);
                $this->setUserMfaPreference($user, true);
            }
            // When org disables MFA, we do NOT deactivate users' MFA
            // Users keep MFA active but can now disable it individually
        }
    }

    /**
     * Set the user's activeMFA preference in the database
     */
    private function setUserMfaPreference(User $user, bool $mfaActive): void
    {
        $preference = Preference::where('name', 'activeMFA')->first();

        if (!$preference) {
            Log::warning('mfa.preference.not_found', [
                'user_id' => $user->id,
            ]);
            return;
        }

        $value = $mfaActive ? 'true' : 'false';

        Preferencable::updateOrCreate(
            [
                'user_id' => $user->id,
                'preference_id' => $preference->id,
            ],
            [
                'value' => $value,
            ]
        );
    }

    public function syncUserMfaRole(User $user, bool $mfaActive): bool
    {
        if (empty($user->keycloak_client_id)) {
            Log::warning('mfa.role.sync.user.skip', [
                'user_id' => $user->id,
                'reason' => 'No keycloak_client_id',
            ]);
            return false;
        }

        $roleName = $this->getMfaRoleName();

        if ($mfaActive) {
            return $this->assignRealmRoleToUser($user->keycloak_client_id, $roleName);
        }

        return $this->removeRealmRoleFromUser($user->keycloak_client_id, $roleName);
    }
}
