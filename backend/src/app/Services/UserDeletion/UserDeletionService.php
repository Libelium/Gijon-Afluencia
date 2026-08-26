<?php

namespace App\Services\UserDeletion;

use App\Enums\UserStatus;
use App\Models\User;
use App\Traits\KeycloakHelper;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class UserDeletionService
{
    use KeycloakHelper;

    public function __construct(
        private readonly TransferableRegistry $registry
    ) {}

    /**
     * Transfers data and marks the user as deleted, then removes from Keycloak.
     * Use this when there is no surrounding transaction.
     */
    public function deleteCompletely(User $user, ?User $transferTo = null): void
    {
        DB::transaction(fn () => $this->deleteCompletelyTransactional($user, $transferTo));

        $this->removeFromKeycloak($user);
    }

    /**
     * DB-only version. Safe to call inside an existing transaction.
     * Keycloak must be handled by the caller after the transaction commits.
     */
    public function deleteCompletelyTransactional(User $user, ?User $transferTo = null): void
    {
        // Deletable data must be removed first so that the org cascade
        // (organizations -> users ON DELETE CASCADE) does not find dangling FK rows.
        $this->deleteRelatedData($user);

        if ($transferTo !== null) {
            $this->transferAllData($user, $transferTo);
        } else {
            $this->cleanTransferableData($user);
        }

        $this->markAsDeleted($user);
    }

    public function removeFromKeycloak(User $user): void
    {
        if (!$user->keycloak_client_id) {
            return;
        }

        if (!$this->deleteUser($user->keycloak_client_id)) {
            Log::error('user_deletion.keycloak_failed', [
                'user_id'     => $user->id,
                'keycloak_id' => $user->keycloak_client_id,
            ]);
        }
    }

    private function transferAllData(User $from, User $to): void
    {
        foreach ($this->registry->getTransferable() as ['handler' => $handler, 'model' => $model]) {
            $handler::transfer($from, $to, $model);
        }
    }

    private function cleanTransferableData(User $user): void
    {
        foreach ($this->registry->getTransferable() as ['handler' => $handler, 'model' => $model]) {
            $handler::clean($user, $model);
        }
    }

    private function deleteRelatedData(User $user): void
    {
        foreach ($this->registry->getDeletable() as ['handler' => $handler, 'model' => $model]) {
            $handler::deleteForUser($user, $model);
        }
    }

    private function markAsDeleted(User $user): void
    {
        $user->status = UserStatus::Deleted;
        $user->save();
    }
}
