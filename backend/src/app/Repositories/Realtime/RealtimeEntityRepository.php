<?php

namespace App\Repositories\Realtime;

use App\Models\Realtime\EntityRelationship;
use Illuminate\Database\Eloquent\Collection;
use Illuminate\Support\Facades\DB;

class RealtimeEntityRepository
{
    public static function getLastRelationshipValues(
        string $urn,
        string $tenant,
        string $scope,
        array $nameFilter
    ): Collection {
        $lastRelationshipValues = EntityRelationship::where('urn', $urn)
            ->where('tenant', $tenant)
            ->where('scope', $scope)
            ->where('timestamp', function ($query) use ($urn) {
                $query->selectRaw('max("timestamp")')
                    ->from('entity_relationships as er2')
                    ->where('er2.urn', $urn)
                    ->whereColumn('er2.name', 'entity_relationships.name');
            });

        if (count($nameFilter) != 0) {
            $lastRelationshipValues = $lastRelationshipValues->whereIn('name', $nameFilter);
        }

        $lastRelationshipValues = $lastRelationshipValues->get();

        return $lastRelationshipValues;
    }

    public static function getCommandsWithValues(
        string $urn,
        string $tenant,
        string $scope,
        array $nameFiler,
        bool $filterAvailable,
        bool $filterPending
    ) {
        $base_query = DB::connection('pgsql_realtime')
            ->table('entity_commands')
            ->select(
                'entity_commands.urn',
                'entity_commands.tenant',
                'entity_commands.scope',
                'entity_commands.entity_id',
                'entity_commands.name',
                'entity_commands.status',
                'entity_commands.info',
                'entity_commands.status_timestamp',
                'entity_commands.info_timestamp',
                'entity_commands.available',
                'entity_commands.pending',
                'entity_commands.pending_value',
                'entity_properties.value as current_value',
                'entity_properties.value_type'
            )
            ->leftJoin(
                'entity_properties',
                function ($join) {
                    $join->on('entity_commands.urn', '=', 'entity_properties.urn');
                    $join->on('entity_commands.tenant', '=', 'entity_properties.tenant');
                    $join->on('entity_commands.scope', '=', 'entity_properties.scope');
                    $join->on('entity_commands.name', '=', 'entity_properties.name');
                }
            )
            ->where('entity_commands.urn', $urn)
            ->where('entity_commands.tenant', $tenant)
            ->where('entity_commands.scope', $scope);

        if ($filterAvailable) {
            $base_query = $base_query->where('entity_commands.available', true);
        }

        if ($filterPending) {
            $base_query = $base_query->where('entity_commands.pending', true);
        }

        if ($nameFiler != null) {
            $base_query = $base_query->whereIn('entity_commands.name', $nameFiler);
        }

        $entity_commands = $base_query->get();

        return $entity_commands;
    }
}