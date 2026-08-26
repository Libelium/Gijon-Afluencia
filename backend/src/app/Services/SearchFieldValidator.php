<?php

namespace App\Services;

use Illuminate\Database\Eloquent\Relations\Relation;

class SearchFieldValidator
{
    /**
     * Check if a resource type exists in the morph map.
     *
     * @param string $resourceType
     * @return bool
     */
    public static function resourceTypeExists(string $resourceType): bool
    {
        return Relation::getMorphedModel($resourceType) !== null;
    }

    /**
     * Get the model class for a given resource type from the morph map.
     *
     * @param string $resourceType
     * @return class-string|null
     */
    public static function getModelClass(string $resourceType): ?string
    {
        return Relation::getMorphedModel($resourceType);
    }

    /**
     * Get the searchable fields whitelist for a given resource type model.
     *
     * @param string $resourceType
     * @return array
     */
    public static function getSearchableFields(string $resourceType): array
    {
        $modelClass = Relation::getMorphedModel($resourceType);

        return ($modelClass && method_exists($modelClass, 'getSearchableFields'))
            ? $modelClass::getSearchableFields()
            : ['name'];
    }

    /**
     * Validate search fields against the model's searchable whitelist.
     * Throws an exception if any field is not in the whitelist.
     *
     * @param array $fields
     * @param string $resourceType
     * @throws \InvalidArgumentException
     */
    public static function validateSearchFields(array $fields, string $resourceType): void
    {
        $whitelist = self::getSearchableFields($resourceType);
        $invalidFields = array_diff($fields, $whitelist);

        if (!empty($invalidFields)) {
            throw new \InvalidArgumentException(
                'Non-searchable fields for ' . $resourceType . ': ' . implode(', ', $invalidFields)
            );
        }
    }
}
