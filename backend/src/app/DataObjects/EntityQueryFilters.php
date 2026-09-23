<?php

namespace App\DataObjects;

/** The filters that narrow an entity listing, so each call says what it filters by. */
class EntityQueryFilters
{
    /**
     * @param string[]|null $types      datamodels to keep
     * @param int[]|null    $groups     entity-group ids the entity must belong to
     * @param string[]|null $excluded   urn patterns to leave out
     * @param array|null    $bounds     south/west/north/east, in degrees
     * @param string[]|null $urn        urn patterns to keep
     */
    public function __construct(
        public readonly string|null $tenant = null,
        public readonly string|null $scope = null,
        public readonly string|null $searchText = null,
        public readonly array|null $types = null,
        public readonly array|null $groups = null,
        public readonly bool $onlyCanUpdate = false,
        public readonly array|null $excluded = null,
        public readonly array|null $bounds = null,
        public readonly array|null $urn = null,
    ) {
    }
}
