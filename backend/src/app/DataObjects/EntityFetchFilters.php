<?php

namespace App\DataObjects;

use Illuminate\Http\Request;

/**
 * The attribute filters and fetch options shared by the realtime entity read
 * endpoints (getEntityRequest / getEntitiesRequest).
 *
 * The parsing used to be copied verbatim into each endpoint; capturing it once
 * here keeps a single source of truth for how the request is interpreted. The
 * factory reproduces the original parsing exactly, including the fact that the
 * command flags are taken as-is (not cast) and that a blank list yields [].
 */
class EntityFetchFilters
{
    /**
     * @param string[] $typeFilter
     * @param string[] $propFilter
     * @param string[] $relFilter
     * @param string[] $cmdFilter
     */
    public function __construct(
        public readonly array $typeFilter,
        public readonly array $propFilter,
        public readonly array $relFilter,
        public readonly array $cmdFilter,
        public readonly bool $lastSent,
        public readonly mixed $filterCmdAvailable,
        public readonly mixed $filterCmdPending,
        public readonly int $referenceDataNesting,
    ) {
    }

    public static function fromRequest(Request $request): self
    {
        $typeFilter = explode(',', $request->input('attrTypeFilter', 'Property,Relationship,Command'));

        $nameFilter = self::explodeList($request->input('attrNameFilter', ''));
        $propFilter = self::explodeList($request->input('attrPropFilter', ''));
        $relFilter  = self::explodeList($request->input('attrRelFilter', ''));
        $cmdFilter  = self::explodeList($request->input('attrCmdFilter', ''));

        return new self(
            typeFilter: $typeFilter,
            propFilter: array_merge($propFilter, $nameFilter),
            relFilter: array_merge($relFilter, $nameFilter),
            cmdFilter: array_merge($cmdFilter, $nameFilter),
            lastSent: (bool) $request->input('lastSent', false),
            filterCmdAvailable: $request->input('filterCmdAvailable', false),
            filterCmdPending: $request->input('filterCmdPending', false),
            referenceDataNesting: (int) $request->input('referenceDataNesting', 0),
        );
    }

    /**
     * Reproduces the endpoints' original list parsing: a blank value yields an
     * empty array, anything else is split on commas.
     */
    private static function explodeList(mixed $value): array
    {
        return $value == '' ? [] : explode(',', $value);
    }
}
