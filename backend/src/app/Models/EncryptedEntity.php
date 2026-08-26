<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

/**
 * Model to manage FIWARE entities with encrypted data
 *
 * This table stores metadata about which entities have sensitive encrypted
 * data and which specific attributes are encrypted.
 *
 * @property int $id
 * @property string $entity_urn FIWARE entity URN
 * @property string $tenant FIWARE tenant
 * @property string $scope FIWARE scope
 * @property array $encrypted_attributes Array of encrypted attribute names
 * @property string $encryption_algorithm Algorithm used (AES-256-GCM)
 * @property string|null $datamodel_type FIWARE datamodel type
 * @property \Illuminate\Support\Carbon $created_at
 * @property \Illuminate\Support\Carbon $updated_at
 */
class EncryptedEntity extends Model
{
    use HasFactory;

    protected $table = 'encrypted_entities';

    protected $fillable = [
        'entity_urn',
        'tenant',
        'scope',
        'encrypted_attributes',
        'encryption_algorithm',
        'datamodel_type',
    ];

    protected $casts = [
        'encrypted_attributes' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * Checks if a specific attribute is encrypted
     *
     * @param string $attributeName Attribute name to check
     * @return bool True if the attribute is encrypted
     */
    public function isAttributeEncrypted(string $attributeName): bool
    {
        return in_array($attributeName, $this->encrypted_attributes ?? []);
    }
}
