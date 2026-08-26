<?php

namespace App\Repositories;

use App\Models\EncryptedEntity;
use Illuminate\Database\Eloquent\Collection;

/**
 * Repository to manage operations on encrypted entities
 */
class EncryptedEntityRepository
{
    /**
     * Finds an encrypted entity by its URN, tenant and scope
     *
     * @param string $urn Entity URN
     * @param string $tenant FIWARE tenant
     * @param string $scope FIWARE scope
     * @return EncryptedEntity|null
     */
    public static function findByUrn(string $urn, string $tenant, string $scope): ?EncryptedEntity
    {
        return EncryptedEntity::where('entity_urn', $urn)
            ->where('tenant', $tenant)
            ->where('scope', $scope)
            ->first();
    }
}
