<?php

namespace App\Http\V1\Controllers\Realtime;

use App\Http\V1\Controllers\Controller;
use App\Models\Realtime\EntityProperty;
use App\Models\Realtime\EntityRelationship;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use App\Http\V1\Resources\Realtime\EntityPropertyResource;
use App\Http\V1\Resources\Realtime\EntityRelationshipResource;
use App\Http\V1\Resources\Realtime\EntityCommandResource;
use App\Repositories\Realtime\RealtimeEntityRepository;
use App\Repositories\EncryptedEntityRepository;
use App\Repositories\EntityRepository;
use App\Helpers\EncryptionHelper;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use App\Helpers\Entities\Commands\EntityCommandsHelper;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\CustomDatamodel;
use App\Models\Entity;
use App\Models\FiwareScope;
use Carbon\Carbon;
use Illuminate\Support\Facades\Log;
use Spatie\LaravelIgnition\Recorders\DumpRecorder\Dump;

class RealtimeEntityController extends Controller
{

    # Some attrs are backend only and should not be shown to the user
    private static array $ignored_entity_attrs = ['commands'];

    public function getEntityProperties(
        string $urn,
        string $tenant,
        string $scope,
        array $propNameFilter
    ): array {
        // it is supposed that the user has access to the device
        // get the properties that match the filter if any

        $base_query = EntityProperty::where('urn', $urn)
            ->where('tenant', $tenant)
            ->where('scope', $scope);

        if (count($propNameFilter) != 0) {
            $base_query = $base_query->whereIn('name', $propNameFilter);
        }

        $entity_properties = $base_query->get();

        $encryptedEntity = EncryptedEntityRepository::findByUrn($urn, $tenant, $scope);
        $shouldDecrypt = false;

        if ($encryptedEntity) {
            $user = auth()->user();
            if ($user) {
                $shouldDecrypt = $user->hasPermissionTo(
                    AppPermission::DATA_SOURCES_ENTITIES_DECRYPT_READ->value
                );
            }
        }

        # transform each to a resource
        $properties = array();
        foreach ($entity_properties as $entity_property) {

            if (in_array($entity_property->name, self::$ignored_entity_attrs)) {
                continue;
            }

            if ($encryptedEntity &&
                $encryptedEntity->isAttributeEncrypted($entity_property->name)) {

                if ($shouldDecrypt) {
                    try {
                        $entity_property->value = EncryptionHelper::decrypt($entity_property->value);
                    } catch (\Exception $e) {
                        Log::error("Decryption failed for {$urn}::{$entity_property->name}: {$e->getMessage()}");
                    }
                }
            }

            $property = new EntityPropertyResource($entity_property);
            array_push($properties, $property);
        }

        return $properties;
    }

    public function getEntityCommands(
        string $urn,
        string $tenant,
        string $scope,
        array $propNameFilter,
        bool $filterAvailable,
        bool $filterPending
    ): array {
        $entity_commands = RealtimeEntityRepository::getCommandsWithValues($urn, $tenant, $scope, $propNameFilter, $filterAvailable, $filterPending);

        # transform each to a resource
        $commands = [];
        foreach ($entity_commands as $entity_command) {
            $command = new EntityCommandResource($entity_command);
            array_push($commands, $command);
        }
        return $commands;
    }

    public function getEntityRelationships(
        string $urn,
        string $tenant,
        string $scope,
        array $attrTypeFiler,
        array $attrPropFilter,
        array $attrRelFilter,
        array $attrCmdFilter,
        int $referenceDataNesting,
        array &$alreadyFetchedList,
        bool $lastSent,
        bool $filterCmdAvailable,
        bool $filterCmdPending
    ): array {
        $entity_relationships = array();

        if ($lastSent) {
            $entity_relationships = RealtimeEntityRepository::getLastRelationshipValues($urn, $tenant, $scope, $attrRelFilter);
        } else {
            $entity_relationships = EntityRelationship::where('urn', $urn);
            if (count($attrRelFilter) != 0) {
                $entity_relationships = $entity_relationships->whereIn('name', $attrRelFilter);
            }
            $entity_relationships = $entity_relationships->get();
        }

        $relationships = array();

        $alreadyFetchedList = array_merge($alreadyFetchedList, array($urn));

        $latestTimestamp = 0;

        # transform each to a resource, fetch the referenced data if requested
        # and compute the last_sent value
        foreach ($entity_relationships as $entity_relationship) {
            $relationship = new EntityRelationshipResource($entity_relationship);
            $relationship->referenced_data = null;
            $relationship->pruned_by_cicle = false;
            $relationship->last_sent = $lastSent;

            $thisTimestamp = strtotime($relationship->timestamp);
            if ($thisTimestamp > $latestTimestamp) {
                $latestTimestamp = $thisTimestamp;
            }

            if ($referenceDataNesting == 0) {
                array_push($relationships, $relationship);
                continue;
            }

            if (!in_array($entity_relationship->value, $alreadyFetchedList)) {
                # it is requested to get the referenced data
                $referencedUrn = $entity_relationship->value;
                $referencedData = $this->getEntity(
                    $referencedUrn,
                    $tenant,
                    $scope,
                    $attrTypeFiler,
                    $attrPropFilter,
                    $attrRelFilter,
                    $attrCmdFilter,
                    false,
                    $filterCmdAvailable,
                    $filterCmdPending,
                    $referenceDataNesting - 1,
                    $alreadyFetchedList,
                    false # do not throw error response, just return an empty array
                );
                $relationship->referenced_data = $referencedData;
            } else {
                $relationship->pruned_by_cicle = true;
            }

            array_push($relationships, $relationship);
        }

        // update the last_sent value
        if (!$lastSent) {
            foreach ($relationships as $relationship) {
                $thisTimestamp = strtotime($relationship->timestamp);
                $relationship->last_sent = $thisTimestamp == $latestTimestamp;
            }
        }

        return $relationships;
    }

    public function getEntity(
        string $urn,
        string $tenant,
        string $scope,
        array $attrTypeFiler,
        array $attrPropFilter,
        array $attrRelFilter,
        array $attrCmdFilter,
        bool $getOnlyLastSent,
        bool $filterCmdAvailable,
        bool $filterPending,
        int $referenceDataNesting,
        array $alreadyFetchedList,
        bool $throwErrorResponse = true
    ): array {
        if (count($attrTypeFiler) == 0) {
            $attrTypeFiler = array('Property', 'Relationship', 'Command');
        }

        $entity_model = Entity::select('entities.*')
            ->where('urn', $urn)
            ->join('fiware_scopes', function ($join) use ($tenant, $scope) {
                $join->on('entities.fiware_scope_id', '=', 'fiware_scopes.id')
                    ->join('fiware_tenants', function ($join) use ($tenant) {
                        $join->on('fiware_scopes.fiware_tenant_id', '=', 'fiware_tenants.id')
                            ->where('fiware_tenants.name', $tenant);
                    })
                    ->where('fiware_scopes.name', $scope);
            })
            ->first();

        if (!$entity_model && $throwErrorResponse) {
            response()->json(
                'Entity not found',
                404
            )->throwResponse();
        }

        try {
            $this->authorize('read', $entity_model);
        } catch (\Exception $e) {
            if ($throwErrorResponse) {
                throw $e;
            } else {
                return [];
            }
        }

        $entity = [];

        # if properties were requested (its in attrTypeFiler)
        if (in_array('Property', $attrTypeFiler)) {
            $props = $this->getEntityProperties($urn, $tenant, $scope, $attrPropFilter);
            $entity = array_merge($entity, $props);
        }

        # if relationships were requested (its in attrTypeFiler)
        if (in_array('Relationship', $attrTypeFiler)) {
            $entity = array_merge(
                $entity,
                $this->getEntityRelationships(
                    $urn,
                    $tenant,
                    $scope,
                    $attrTypeFiler,
                    $attrPropFilter,
                    $attrRelFilter,
                    $attrCmdFilter,
                    $referenceDataNesting,
                    $alreadyFetchedList,
                    $getOnlyLastSent,
                    $filterCmdAvailable,
                    $filterPending
                )
            );
        }

        # if commands were requested (its in attrTypeFiler)
        if (in_array('Command', $attrTypeFiler)) {
            $commands = $this->getEntityCommands($urn, $tenant, $scope, $attrCmdFilter, $filterCmdAvailable, $filterPending);
            $entity = array_merge($entity, $commands);
        }

        return $entity;
    }


    public function getEntityRequest(string $urn, Request $request): Response
    {
        $headers = $request->headers->all();
        $tenant = $headers['tenant'][0] ?? null;
        $scope = $headers['scope'][0] ?? null;

        if ($tenant == null || $scope == null) {
            return response('Missing headers (tenant,scope)', 400);
        }

        $typeFilter = $request->input('attrTypeFilter', 'Property,Relationship,Command');
        $typeFilter = explode(',', $typeFilter);

        $nameFilter = $request->input('attrNameFilter', '');
        if ($nameFilter == '') {
            $nameFilter = [];
        } else {
            $nameFilter = explode(',', $nameFilter);
        }

        $propFilter = $request->input('attrPropFilter', '');
        if ($propFilter == '') {
            $propFilter = [];
        } else {
            $propFilter = explode(',', $propFilter);
        }

        $relFilter = $request->input('attrRelFilter', '');
        if ($relFilter == '') {
            $relFilter = [];
        } else {
            $relFilter = explode(',', $relFilter);
        }

        $cmdFilter = $request->input('attrCmdFilter', '');
        if ($cmdFilter == '') {
            $cmdFilter = [];
        } else {
            $cmdFilter = explode(',', $cmdFilter);
        }

        $propFilter = array_merge($propFilter, $nameFilter);
        $relFilter = array_merge($relFilter, $nameFilter);
        $cmdFilter = array_merge($cmdFilter, $nameFilter);

        $lastSent = (bool) $request->input('lastSent', false);

        $filterCmdAvailable = $request->input('filterCmdAvailable', false);

        $filterCmdPending = $request->input('filterCmdPending', false);

        $referenceDataNesting = (int) $request->input('referenceDataNesting', 0);

        $entity = $this->getEntity(
            $urn,
            $tenant,
            $scope,
            $typeFilter,
            $propFilter,
            $relFilter,
            $cmdFilter,
            $lastSent,
            $filterCmdAvailable,
            $filterCmdPending,
            $referenceDataNesting,
            []
        );

        // to array
        $entity = array_map(function ($item) {
            return $item->toArray(null);
        }, $entity);

        return response($entity, 200);
    }

    public function getLastDataRequest(string $urn, Request $request): Response
    {
        $records = $this->getEntityRequest($urn, $request)->getContent(); //Para luego pasarselo a la funcion
        $records = collect(json_decode($records, true));

        $time_last_data = $records->pluck('timestamp')->filter()
            ->map(fn($t) => Carbon::parse($t))
            ->max();

        $time_last_data = $time_last_data?->format('Y-m-d H:i:s');
        return response($time_last_data, 200);
    }

    public function getLastDataRequestBulk(Request $request): Response
    {

        $request->validate([
            'entities' => 'required|array',
            'entities.*.urn' => 'required|string',
        ]);

        $headers = $request->headers->all();
        $tenant = $headers['tenant'][0] ?? null;
        $scope = $headers['scope'][0] ?? null;

        $entities = $request->input('entities');

        $entityRecords = [];

        foreach ($entities as $entity) {
            $urn = $entity['urn'];
            $data =  new Request([
                'tenant' => $tenant,
                'scope' => $scope,
            ]);
            $data->headers->add($request->headers->all());
            $records = $this->getLastDataRequest($urn, $data)->getContent();

            $entityRecords[] = [
                'urn' => $urn,
                'record' => $records,
            ];
        }

        $response = [
            'tenant' => $tenant,
            'scope' => $scope,
            'entities' => $entityRecords,
        ];

        return response($response, 200);
    }

    public function getEntitiesRequest(Request $request): Response
    {
        $request->validate([
            'entities' => 'required|array',
            'entities.*.urn' => 'required|string',
            'entities.*.tenant' => 'required|string',
            'entities.*.scope' => 'required|string',
        ]);

        $entities = $request->input('entities');

        $typeFilter = $request->input('attrTypeFilter', 'Property,Relationship,Command');
        $typeFilter = explode(',', $typeFilter);

        $nameFilter = $request->input('attrNameFilter', '');
        if ($nameFilter == '') {
            $nameFilter = [];
        } else {
            $nameFilter = explode(',', $nameFilter);
        }

        $propFilter = $request->input('attrPropFilter', '');
        if ($propFilter == '') {
            $propFilter = [];
        } else {
            $propFilter = explode(',', $propFilter);
        }

        $relFilter = $request->input('attrRelFilter', '');
        if ($relFilter == '') {
            $relFilter = [];
        } else {
            $relFilter = explode(',', $relFilter);
        }

        $cmdFilter = $request->input('attrCmdFilter', '');
        if ($cmdFilter == '') {
            $cmdFilter = [];
        } else {
            $cmdFilter = explode(',', $cmdFilter);
        }

        $propFilter = array_merge($propFilter, $nameFilter);
        $relFilter = array_merge($relFilter, $nameFilter);
        $cmdFilter = array_merge($cmdFilter, $nameFilter);

        $lastSent = (bool) $request->input('lastSent', false);

        $filterCmdAvailable = $request->input('filterCmdAvailable', false);

        $filterCmdPending = $request->input('filterCmdPending', false);

        $referenceDataNesting = (int) $request->input('referenceDataNesting', 0);

        $data = [];

        foreach ($entities as $entity) {
            $e = $this->getEntity(
                $entity['urn'],
                $entity['tenant'],
                $entity['scope'],
                $typeFilter,
                $propFilter,
                $relFilter,
                $cmdFilter,
                $lastSent,
                $filterCmdAvailable,
                $filterCmdPending,
                $referenceDataNesting,
                []
            );

            // to array
            $e = array_map(function ($item) {
                return $item->toArray(null);
            }, $e);

            $data = array_merge($data, [$e]);
        }

        return response($data, 200);
    }

    public function getLastDataTimeEntitiesRequest(Request $request): Response
    {
        $records = $this->getEntitiesRequest($request)->getContent();
        $records = json_decode($records, true);

        $flattedArray = array_merge(...$records);

        usort($flattedArray, function ($a, $b) {
            return strtotime($b['timestamp']) - strtotime($a['timestamp']);
        });

        return response($flattedArray, 200);
    }

    public function getLastDataTimeEntitiesRequestBulk(Request $request): Response
    {
        $request->validate([
            'bulkEntities' => 'required|array',
            'bulkEntities.*' => 'required|array',
            'bulkEntities.*.*.urn' => 'required|string',
            'bulkEntities.*.*.tenant' => 'required|string',
            'bulkEntities.*.*.scope' => 'required|string',
        ]);

        $bulkEntities = $request->input('bulkEntities');

        $allRecords = [];

        foreach ($bulkEntities as $entities) {
            $subRequest = new Request(['entities' => $entities] + $request->all());

            $records = $this->getLastDataTimeEntitiesRequest($subRequest)->getContent();
            $records = json_decode($records, true);

            usort($records, function ($a, $b) {
                return strtotime($b['timestamp']) - strtotime($a['timestamp']);
            });

            $allRecords[] = $records;
        }

        return response($allRecords, 200);
    }

    public function getAvailableMeasuresRequest(Request $request): Response
    {
        $user = auth()->user();

        // 1. Get all entity URNs the user has READ access to (main DB)
        $query = Entity::query();
        $query = EntityRepository::updateRequestWithPermissionCheck(
            $query,
            $user->id,
            AppResourcePermission::READ
        );
        $urns = $query->distinct()->pluck('entities.urn')->toArray();

        if (empty($urns)) {
            return response([], 200);
        }

        // 2. Get distinct measures for those URNs from realtime DB (skip relationships)
        $properties = EntityProperty::whereIn('urn', $urns)
            ->whereNotIn('value_type', ['Relationship', 'Command'])
            ->select('name', 'units', 'value_type')
            ->distinct()
            ->orderBy('name')
            ->get();

        // 3. Map to Variable shape applying name translation
        $result = $properties->map(function ($prop) {
            $customDatamodel = CustomDatamodel::where('command', $prop->name)->first();
            $name = EntityCommandsHelper::getCommandNameFromCSV($customDatamodel)
                ?? RealtimeEntityResourcesHelper::camelCaseToSpaced($prop->name);
            return [
                'id'         => $prop->name,
                'name'       => $name,
                'units'      => EntityCommandsHelper::getCommandPropertyFromCSV('units', $customDatamodel) ?? $prop->units,
                'value_type' => $prop->value_type,
            ];
        })->values();

        return response($result, 200);
    }
}
