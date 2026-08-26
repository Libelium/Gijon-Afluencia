<?php

namespace App\Helpers;

use App\Models\User;
use App\Services\UserDeletion\UserDeletionService;
use App\Traits\KeycloakHelper;
use Illuminate\Support\Facades\DB;

class UserHelper
{
    use KeycloakHelper;

    public function __construct(
        private readonly UserDeletionService $deletionService
    ) {}

    /**
     * Swaps admin data preserving the admin user ID.
     */
    public function swapAdminData(
        User $currentAdmin,
        string $newName,
        string $newEmail,
        string $newKeycloakClientId,
        bool $cleanAdmin
    ): void {
        $oldEmail = $currentAdmin->email;

        $emailParts = explode('@', $oldEmail);
        $auxEmail = $emailParts[0] . '+aux@' . $emailParts[1];

        $auxUser = DB::transaction(function () use ($currentAdmin, $auxEmail, $newName, $newEmail, $newKeycloakClientId) {
            $auxUser = User::create([
                'name'               => $currentAdmin->name,
                'email'              => $auxEmail,
                'keycloak_client_id' => $currentAdmin->keycloak_client_id,
                'enabled'            => $currentAdmin->enabled,
                'organization_id'    => $currentAdmin->organization_id,
            ]);

            $currentAdmin->name               = $newName;
            $currentAdmin->email              = $newEmail;
            $currentAdmin->keycloak_client_id = $newKeycloakClientId;
            $currentAdmin->enabled            = true;
            $currentAdmin->save();

            return $auxUser;
        });

        $this->handleAuxiliaryUser($auxUser, $oldEmail, $cleanAdmin);

        $this->sendKeycloakResetPasswordEmail($newKeycloakClientId);
    }

    private function handleAuxiliaryUser(User $auxUser, string $originalEmail, bool $deleteUser): void
    {
        if ($deleteUser) {
            $this->deletionService->deleteCompletely($auxUser);
        } else {
            $auxUser->email = $originalEmail;
            $auxUser->save();
        }
    }
}
