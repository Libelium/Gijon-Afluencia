<?php

namespace App\Traits;

trait Searchable
{
    /**
     * Get the fields that are allowed for searching.
     * Override the static $searchable property in your model to customize
     * which columns are permitted as search fields.
     *
     * @return array
     */
    public static function getSearchableFields(): array
    {
        return property_exists(static::class, 'searchable')
            ? static::$searchable
            : ['name'];
    }
}
