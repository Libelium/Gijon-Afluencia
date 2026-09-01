<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppPermission;
use App\Models\Entity;
use App\Helpers\AetherLinkHelper;
use App\Helpers\NotificationHelper;
use App\Models\EntityGroup;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Requests\Entities\CreateEntityRequest;
use App\Http\V1\Requests\Entities\UpdateEntityRequest;
use App\Http\V1\Resources\EntityResource;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Http\V1\Resources\EntityHealthcheckResource;
use App\Models\Device;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\Realtime\EntityCommand;
use App\Models\Realtime\EntityProperty;
use App\Repositories\EntityRepository;
use App\Repositories\LogsRepository;
use App\Repositories\PreferenceRepository;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use App\Authorization\AppResourcePermission;
use App\Helpers\Entities\RealtimeEntityResourcesHelper;

class EntityController extends Controller
{
    public function show(int $id)
    {
        $entity = Entity::with(['geolocation', 'fiwareScope', 'name'])->findOrFail($id);

        $this->authorize('read', $entity);

        return (new EntityResource($entity))->response();
    }


    /**
     * Get all entities associated with a specific device.
     *
     * @param  int  $id  The ID of the Device
     * @return \Illuminate\Http\Response
     */
    public function getEntitiesFromDeviceId(int $id)
    {
        $device = Device::findOrFail($id);

        $device->load([
            'entities.geolocation',
            'entities.fiwareScope',
            'entities.name',
            'entities.devices',
            'entities.tenant'
        ]);

        foreach ($device->entities as $entity) {
            $this->authorize('read', $entity);
        }
        return response()->json(EntityResource::collection($device->entities)->resolve());
    }
    public function store(CreateEntityRequest $request)
    {
        try {
            // Prepare entities for Context Broker - convert null attributes to empty object
            $preparedEntities = array_map(function ($entity) {
                if (!isset($entity['attributes']) || $entity['attributes'] === null) {
                    $entity['attributes'] = new \stdClass(); // Empty object for JSON encoding
                }
                return $entity;
            }, $request->entities);
            $user = Auth::user();
            $scope = PreferenceRepository::getMainScope($user);
            $tenant = $scope->tenant;

            // Collect unique datamodel types from all entities
            $datamodels = array_unique(array_map(function ($entity) {
                return $entity['type'];
            }, $request->entities));

            $subscriptionResult = AetherLinkHelper::addTypeSubscriptions($datamodels, $tenant->name, $scope->name);

            if (!$subscriptionResult) {
                return response('Error creating entity subscriptions', 500);
            }

            // Create entities in Context Broker
            $result = AetherLinkHelper::createContextBrokerEntity(
                $tenant->name,
                $scope->name,
                $preparedEntities,
            );

            // If Context Broker creation succeeded, save entities to local database
            if ($result) {
                foreach ($request->entities as $entityData) {
                    $entityUrn = $entityData['id'];
                    $datamodel = $entityData['type'];

                    // Check if entity already exists in database
                    $existingEntity = Entity::where('urn', $entityUrn)
                        ->where('fiware_scope_id', $scope->id)
                        ->first();

                    if (!$existingEntity) {
                        Entity::create([
                            'urn' => $entityUrn,
                            'datamodel' => $datamodel,
                            'fiware_scope_id' => $scope->id,
                            'tenant' => $tenant->name,
                            'scope' => $scope->name,
                        ]);
                    }
                }
            }

            return response($result, 201);
        } catch (\Exception $e) {
            return response('Error creating entity', 500);
        }
    }

    /**
     * Updates or inserts properties for a given entity and handles related side effects.
     *
     * This method takes validated data from the request, transforms it if necessary (e.g., 'geolocation' to 'location'),
     * and updates the entity in the Context Broker. If the location is updated, it triggers a process
     * to send a command to disable GPS updates on any associated 'smsp_fiware' devices.
     *
     * @param int                 $id      The ID of the Entity to update.
     * @param UpdateEntityRequest $request The request object containing validated data.
     * @return Response A JSON response with the updated data and a potential warning, or an error response.
     */
    public function upsertProperties(int $id, UpdateEntityRequest $request): Response
    {
        $updateEntityRequest = $request->validated();
        $unmodifiedRequest = $updateEntityRequest;
        $isSmspFiware = false;

        // if it is empty, we don't need to update anything
        if (empty($updateEntityRequest)) {
            return response('No properties to update', 400);
        }

        $entity = Entity::findOrFail($id);
        $this->authorize('update', $entity);

        // An Incident inside an AssetIntervention has its status governed by the intervention only.
        if ($entity->datamodel === 'Incident' && array_key_exists('status', $updateEntityRequest)) {
            $inIntervention = EntityGroup::where('type', 'AssetIntervention')
                ->whereHas('entities', fn ($q) => $q->where('entities.id', $entity->id))
                ->exists();
            if ($inIntervention) {
                return response('Incident status is governed by its AssetIntervention', 422);
            }
        }

        if (array_key_exists('geolocation', $updateEntityRequest)) {
            $geolocationValue = $updateEntityRequest['geolocation'];
            $updateEntityRequest['location'] = $geolocationValue;
            unset($updateEntityRequest['geolocation']);
            $isSmspFiware = $this->handleSmartSpotLocationUpdate($entity, $geolocationValue);
        }

        $attrsToUpdate = [];
        $timestamp = $updateEntityRequest['timestamp'] ?? null;
        unset($updateEntityRequest['timestamp']); // Exclude global timestamp from attributes


        foreach ($updateEntityRequest as $attrName => $attrValue) {
            // Check if $attrValue is already in NGSI-LD format (has 'value' and 'type' keys)
            if (is_array($attrValue) && isset($attrValue['value']) && isset($attrValue['type'])) {
                // Already in NGSI-LD format, use directly
                $attrsToUpdate[$attrName] = $attrValue;
            } else {
                // Simple value, wrap it in NGSI-LD format
                $attrsToUpdate[$attrName] = [
                    "value" => $attrValue,
                    "type" => "Property"
                ];
                // Only add global timestamp if attribute doesn't have its own
                if ($timestamp) {
                    $attrsToUpdate[$attrName]["timestamp"] = $timestamp;
                }
            }
        }

        $result = AetherLinkHelper::updateOnContextBroker(
            $entity->urn,
            $entity->tenant,
            $entity->scope,
            $attrsToUpdate
        );

        if (!$result["updated"]) {
            return response($result["response"], $result["status"]);
        }

        // Best-effort: notify the reporter when an operator changes an Incident's status.
        if ($entity->datamodel === 'Incident' && array_key_exists('status', $attrsToUpdate)) {
            try {
                NotificationHelper::notifyIncidentReporter(
                    $entity->id,
                    (int) Auth::id(),
                    'notifications.incidentStatus',
                    'notifications.incidentStatusSub',
                    'tabler-refresh',
                    ['ref' => NotificationHelper::incidentRef($entity->id), 'status' => $attrsToUpdate['status']['value'] ?? null],
                );
            } catch (\Throwable $e) {
                Log::warning('incident.status.notify.failed', ['error' => $e->getMessage()]);
            }
        }

        // Notify the NEW assignee(s) when an AssetIntervention is (re)assigned. Compares against the
        // current mirror (still the OLD value — updated asynchronously) so re-sending the same
        // assignment does not re-notify. Best-effort.
        if ($entity->datamodel === 'AssetIntervention'
            && (array_key_exists('assignedTo', $attrsToUpdate) || array_key_exists('assignedTeam', $attrsToUpdate))) {
            $newAssignedTo = array_key_exists('assignedTo', $attrsToUpdate) ? ($attrsToUpdate['assignedTo']['value'] ?? null) : null;
            $newAssignedTeam = array_key_exists('assignedTeam', $attrsToUpdate) ? ($attrsToUpdate['assignedTeam']['value'] ?? null) : null;

            $assignedToChanged = $newAssignedTo !== null
                && (string) $newAssignedTo !== (string) NotificationHelper::incidentAttr($entity->id, 'assignedTo');
            $assignedTeamChanged = $newAssignedTeam !== null
                && (string) $newAssignedTeam !== (string) NotificationHelper::incidentAttr($entity->id, 'assignedTeam');

            if ($assignedToChanged || $assignedTeamChanged) {
                try {
                    NotificationHelper::notifyAssignees(
                        $assignedToChanged ? (string) $newAssignedTo : null,
                        $assignedTeamChanged ? (string) $newAssignedTeam : null,
                        (int) Auth::id(),
                        [
                            'ref'  => NotificationHelper::incidentRef($entity->id),
                            'name' => NotificationHelper::incidentAttr($entity->id, 'name'),
                        ],
                    );
                } catch (\Throwable $e) {
                    Log::warning('intervention.reassign.notify.failed', ['error' => $e->getMessage()]);
                }
            }
        }

        // Update units in EntityProperty table for each attribute that has unitCode
        foreach ($attrsToUpdate as $attrName => $attrData) {
            if (is_array($attrData) && isset($attrData['unitCode'])) {
                EntityProperty::where('entity_id', $entity->id)
                    ->where('name', $attrName)
                    ->update(['units' => $attrData['unitCode']]);
            }
        }

        if ($isSmspFiware) {
            $unmodifiedRequest['warning'] = 'GPS localization will be disabled for the related Smart Spot device.';
        }

        return response($unmodifiedRequest, 200);
    }

    /**
     * Deletes a specific property from an entity.
     *
     * @param int    $id            The ID of the Entity.
     * @param string $attributeName The name of the attribute to delete.
     * @return Response A JSON response indicating success or failure.
     */
    public function deleteProperty(int $id, string $attributeName): Response
    {
        $entity = Entity::findOrFail($id);
        $this->authorize('update', $entity);

        // Prevent deletion of critical attributes
        if (in_array($attributeName, ['location', 'geolocation', 'name', 'id', 'type'])) {
            return response(['error' => 'Cannot delete critical attribute: ' . $attributeName], 400);
        }

        $result = AetherLinkHelper::deleteAttributeOnContextBroker(
            $entity->urn,
            $entity->tenant,
            $entity->scope,
            $attributeName
        );

        if (!$result["deleted"]) {
            return response($result["response"], $result["status"]);
        }
        EntityProperty::where('entity_id', $entity->id)
            ->where('name', $attributeName)
            ->delete();

        return response(['message' => 'Attribute deleted successfully'], 200);
    }

    /**
     * Finds associated 'smsp_fiware' devices and sends commands to disable GPS and set new coordinates.
     *
     * @param Entity $entity The entity for which to find associated devices.
     * @param array $geolocationValue GeoJSON Point format: {"type": "Point", "coordinates": [lng, lat]}
     * @return bool Returns `true` if at least one command was sent, otherwise `false`.
     */
    private function handleSmartSpotLocationUpdate(Entity $entity, array $geolocationValue): bool
    {
        $smartSpotDevices = $this->getSmartSpotDevices($entity);
        if ($smartSpotDevices->isEmpty()) {
            return false;
        }

        $commandSent = false;
        foreach ($smartSpotDevices as $device) {
            if ($this->sendLocationCommandsToSmspFiwareDevice($device, $entity, $geolocationValue)) {
                $commandSent = true;
            }
        }

        return $commandSent;
    }

    /**
     * Get SmartSpot devices associated with an entity.
     */
    private function getSmartSpotDevices(Entity $entity)
    {
        return $entity->devices()->whereHas('deviceType', function ($query) {
            $query->where('code', 'smsp_fiware');
        })->get();
    }

    /**
     * Find entities from a device that have the rw_dho_upd_location command.
     */
    private function getEntitiesWithLocationCommand(Device $device)
    {
        $deviceEntities = $device->entities()->get();
        $entitiesWithCommand = $deviceEntities->filter(function ($entity) {
            return $entity->commands()->where('name', 'rw_dho_upd_location')->exists();
        });

        return $entitiesWithCommand;
    }

    /**
     * Send location commands to all entities of a device that have the command.
     * Falls back to main entity if no entity with the command is found.
     */
    private function sendLocationCommandsToSmspFiwareDevice(Device $device, Entity $sourceEntity, array $geolocationValue): bool
    {
        try {
            $entitiesWithCommand = $this->getEntitiesWithLocationCommand($device);
            $targetEntities = $entitiesWithCommand->isNotEmpty()
                ? $entitiesWithCommand
                : collect([$device->mainEntity->first()])->filter();

            if ($targetEntities->isEmpty()) {
                throw new \Illuminate\Database\Eloquent\ModelNotFoundException('No suitable entity found');
            }

            $payload = [
                "rw_dho_upd_location" => [
                    "type" => "Command",
                    "value" => false
                ],
                "rw_dho_latitude" => [
                    "type" => "Command",
                    "value" => (float) $geolocationValue['coordinates'][1]
                ],
                "rw_dho_longitude" => [
                    "type" => "Command",
                    "value" => (float) $geolocationValue['coordinates'][0]
                ]
            ];

            foreach ($targetEntities as $targetEntity) {
                AetherLinkHelper::updateOnContextBroker(
                    $targetEntity->urn,
                    $targetEntity->tenant,
                    $targetEntity->scope,
                    $payload
                );
            }

            return true;
        } catch (\Illuminate\Database\Eloquent\ModelNotFoundException $e) {
            Log::error('Failed to send disable GPS commands for smsp_fiware device.', [
                'device_serial' => $device->serial,
                'entity_id' => $sourceEntity->id,
                'error_message' => $e->getMessage(),
            ]);
            return false;
        }
    }


    public function sendCommands(int $id, Request $request): Response
    {
        $entity = Entity::find($id);
        $this->authorize('update', $entity);

        # get available commands
        $availableCommands = EntityCommand::select('name')->where('urn', $entity->urn)->where('available', true)->get();

        # now, transform it into a list of strings
        $availableCommands = array_map(function ($command) {
            return $command["name"];
        }, $availableCommands->toArray());

        $unavailable = [];

        # check if all requested commands are available
        foreach ($request->all() as $commandName => $commandValue) {
            if (!in_array($commandName, $availableCommands)) {
                array_push($unavailable, $commandName);
            }
        }

        # show an error with the unavailable commands, if any
        if (count($unavailable) > 0) {
            $unavailableString = implode(", ", $unavailable);
            return response(['errors' => 'You cannot send any of: ' . $unavailableString], 400);
        }

        $commandsToSend = [];
        foreach ($request->all() as $commandName => $commandValue) {
            $commandsToSend[$commandName] = [
                "value" => $commandValue,
                "type" => "Command"
            ];
        }

        # now, we can send the request to the context broker
        $result = AetherLinkHelper::updateOnContextBroker(
            $entity->urn,
            $entity->tenant,
            $entity->scope,
            $commandsToSend
        );

        $updated = $result["updated"];

        if (!$updated) {
            $response = $result["response"];
            $status = $result["status"];
            return response($response, $status);
        }

        // Update pending values
        foreach ($commandsToSend as $commandName => $commandValue) {
            $entityCommand = EntityCommand::where('entity_id', $id)->where('name', $commandName)->first();
            $entityCommand->pending_value = $commandValue['value'];
            $entityCommand->pending = true;
            $entityCommand->updated_at = now();
            $entityCommand->save();
        }

        // Log the command sent
        $logMessage = "Configurarion sent to entity " . $entity->urn;
        $logLevel = "INFO";
        $extra = [
            'origin' => 'platform',
            'values' => $commandsToSend
        ];

        LogsRepository::create($logMessage, $logLevel, 'entities', $id, $extra);

        $device_ids = $entity->devices->pluck('id')->toArray();

        $logs = [];
        foreach ($device_ids as $device_id) {
            $logMessage = "Configuration sent to device.";
            $logs[] = LogsRepository::create($logMessage, $logLevel, 'devices', $device_id, $extra);
        }

        return response(['data' => 'Command sent!!'], 204);
    }

    public function sendCommandsBulk(Request $request): Response
    {
        $ids = $request->input('ids', []);
        $commands = $request->except('ids');

        if (empty($ids)) {
            return response('No entities provided', 400);
        }

        $responses = [];

        foreach ($ids as $id) {
            // create a request with the commands
            $commandRequest = new Request($commands);
            $response = $this->sendCommands($id, $commandRequest);
            // save response to return it after all the requests
            array_push($responses, $response);
        }

        return response($responses, 207);
    }


    public function listAll()
    {
        // Query 1: Get entities with scope/tenant from main DB
        $query = Entity::select(
            'entities.id',
            'entities.urn',
            'entities.datamodel',
            'fiware_scopes.name as scope_name',
            'fiware_tenants.name as tenant_name'
        );

        // Permission check joins fiware_scopes
        $query = EntityRepository::updateRequestWithPermissionCheck(
            $query,
            Auth::user()->id,
            AppResourcePermission::READ
        );

        // Join fiware_tenants after fiware_scopes is available
        $query->leftJoin('fiware_tenants', 'fiware_tenants.id', '=', 'fiware_scopes.fiware_tenant_id')
            ->groupBy('entities.id', 'fiware_scopes.name', 'fiware_tenants.name');

        $entities = $query->get();

        // Query 2: Get geolocations from realtime DB
        $entityUrns = $entities->pluck('urn')->filter()->unique()->toArray();

        if (!empty($entityUrns)) {
            $geolocations = DB::connection('pgsql_realtime')
                ->table('entity_properties')
                ->whereIn('entity_properties.urn', $entityUrns)
                ->where('entity_properties.name', 'location')
                ->select('entity_properties.urn', 'entity_properties.value as geolocation')
                ->get()
                ->keyBy('urn');

            $entities->each(function ($entity) use ($geolocations) {
                if (isset($geolocations[$entity->urn])) {
                    $entity->geolocation_raw = $geolocations[$entity->urn]->geolocation;
                }
            });
        }

        // Build response
        $result = $entities->map(function ($entity) {
            return [
                'id' => $entity->id,
                'urn' => $entity->urn,
                'datamodel' => $entity->datamodel,
                'scope' => $entity->scope_name,
                'tenant' => $entity->tenant_name,
                'geolocation' => isset($entity->geolocation_raw)
                    ? RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($entity->geolocation_raw)
                    : null,
            ];
        });

        return response()->json($result);
    }

    public function paginate(Request $request)
    {
        $paginationSize = $request->input('paginationSize', '10');
        $page = $request->input('page', 1);
        $orderColumn = $request->input('orderBy', 'entities.id');
        $orderColumn = "entities.id";
        $orderDirection = $request->input('orderDirection', true) == true ? 'desc' : 'asc';
        $searchText = $request->input('search', '');
        $tenant = $request->input('tenant', null);
        $scope = $request->input('scope', null);
        $onlyCanUpdate = $request->input('onlyCanUpdate', false);

        $types = $request->input('types', null);
        if ($types != null) {
            $types = explode(',', $types);
        }

        $groups = $request->input('groups', null);
        if ($groups != null) {
            $groups = explode(',', $groups);
        }

        $excluded = $request->input('excluded', null);

        $urn = $request->input('urn', null);
        if ($urn != null && !is_array($urn)) {
            $urn = explode(',', $urn);
        }

        $bounds = $request->input('bounds', null);
        if ($bounds != null) {
            if (
                !is_array($bounds)
                || count(array_intersect_key(array_flip(['south', 'west', 'north', 'east']), $bounds)) !== 4
                || count(array_filter($bounds, 'is_numeric')) !== count($bounds)
            ) {
                return response('Invalid bounds, expected numeric south/west/north/east', 400);
            }
        }

        if ($tenant == null && $scope != null) {
            return response('Undefined tenant for given scope', 400);
        }

        $records = EntityRepository::paginate(
            Auth::user()->id,
            $paginationSize,
            $page,
            $orderColumn,
            $orderDirection,
            $tenant,
            $scope,
            $searchText,
            $types,
            $groups,
            $onlyCanUpdate,
            $excluded,
            $bounds,
            $urn,
        );

        $result = [
            'count' => $records->total(),
            'rows' => EntityResource::collection($records->items()),
            'items' => $records->items(),
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function paginateDatamodels(Request $request)
    {
        $searchText = $request->input('search', '');
        $tenant = $request->input('tenant', null);
        $scope = $request->input('scope', null);

        if ($tenant == null && $scope != null) {
            return response('Undefined tenant for given scope', 400);
        }

        $records = EntityRepository::listDatamodels(
            Auth::user()->id,
            $tenant,
            $scope,
            $searchText,
        );

        $rows = $records->map(fn ($item) => ['datamodel' => $item->datamodel])->values();

        $result = [
            'count' => $rows->count(),
            'rows' => $rows,
            'items' => [],
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    // given a urn and a fiware_scope_id, return the entity_id of the entitiy with that urn and fiware_scope_id
    public function getEntityIdTenantScope(Request $request)
    {
        $urn = $request->input('urn', null);
        $fiware_scope_id = $request->input('scope', null);

        if ($urn == null || $fiware_scope_id == null) {
            return response('Missing parameters', 400);
        }

        $entity = Entity::where('urn', $urn)->where('fiware_scope_id', $fiware_scope_id)->first();

        if ($entity == null) {
            return response('Entity not found', 404);
        }

        $this->authorize('read', $entity);

        return response([
            'entity_id' => $entity->id,
            'tenant' => $entity->tenant,
            'scope' => $entity->scope
        ], 200);
    }

    public function getLastDataTimestamps(Request $request): Response
    {
        $request->validate([
            'entities'      => 'required|array',
            'entities.*.id' => 'required|integer',
        ]);

        $input = $request->input('entities');
        $results = [];

        foreach ($input as $item) {
            $id = $item['id'];

            $entity = Entity::find($id);

            if (! $entity) {
                $results[] = [
                    'id'             => $id,
                    'last_timestamp' => null,
                ];
                continue;
            }

            $lastTs = $entity->getLastDataTimestamp();

            $results[] = [
                'id'             => $id,
                'last_timestamp' => $lastTs,
            ];
        }

        return response($results, 200);
    }

    public function uploadDataToEntity(Request $request)
    {
        $request->validate([
            'fileName' => 'nullable|string',
            'data' => 'nullable|string',
            'file' => 'nullable|file',
        ]);

        $this->authorize('uploadDataToEntity', Entity::class);

        if ($request->hasFile('file')) {
            $file = $request->file('file');
            $content = file_get_contents($file->getRealPath());
            $originalName = $file->getClientOriginalName();
        } else {
            if (!$request->filled('data')) {
                return response('No data or file uploaded', 422);
            }
            $content = $request->input('data');
            $originalName = $request->input('fileName') ?? 'upload.csv';
        }

        $extension = pathinfo($originalName, PATHINFO_EXTENSION) ?: 'csv';

        $timestamp = time();
        $filenameWithoutExt = pathinfo($originalName, PATHINFO_FILENAME);
        $filenameWithoutExt = preg_replace('/[^A-Za-z0-9_\-]/', '_', $filenameWithoutExt);
        $finalFilename = sprintf("%s_%s.%s", $filenameWithoutExt, $timestamp, $extension);

        $s3_path = "entities/uploads/" . $finalFilename;

        Storage::disk('s3')->put($s3_path, $content);
        $params = [
            'user_id' => Auth::id(),
            'storage_file_path' => $s3_path,
        ];

        $user = Auth::user();
        $organization = $user->organization;
        $dataScopeId = PreferenceRepository::getOrganizationPreference($organization, 'mainScope');

        if ($dataScopeId) {
            $dataScope = FiwareScope::with('tenant')->find($dataScopeId);

            if ($dataScope && $dataScope->tenant) {
                $params['tenant'] = $dataScope->tenant->name;
                $params['scope']  = $dataScope->name;
            }
        }

        $message = [
            'task'   => 'platform.data.importation_job',
            'params' => $params
        ];

        $response = Http::withHeaders(['X-Queues-Consumer-Token' => config('services.queues-consumer.token')])
            ->post(config('services.queues-consumer.publish'), $message);

        if ($response->status() >= 400) {
            return response('Error uploading data to entity', 500);
        }
        return response('Data uploaded to entity', 202);
    }

    /**
     * Create entities from a JSON/GeoJSON file upload.
     * Parses the file content and creates each entity in the Context Broker.
     *
     * @param Request $request
     * @return Response
     */
    public function storeFromFile(Request $request)
    {
        $request->validate([
            'file' => 'required|file|mimes:json,geojson,txt',
        ]);

        try {
            $file = $request->file('file');

            $content = file_get_contents($file->getRealPath());

            $data = json_decode($content, true);

            if (json_last_error() !== JSON_ERROR_NONE) {
                return response(['error' => 'Invalid JSON file'], 422);
            }

            $parsedEntities = $this->parseEntitiesFromFile($data);

            if (empty($parsedEntities)) {
                return response(['error' => 'No valid entities found in file'], 422);
            }

            $uniqueEntities = [];
            foreach ($parsedEntities as $entity) {
                $uniqueEntities[$entity['id']] = $entity;
            }
            $uniqueEntities = array_values($uniqueEntities);

            // Prepare entities for Context Broker
            $preparedEntities = array_map(function ($entity) {
                $attributes = $entity['attributes'] ?? null;
                if ($attributes === null) {
                    $attributes = new \stdClass();
                }
                return [
                    'id' => $entity['id'],
                    'type' => $entity['type'],
                    'attributes' => $attributes,
                ];
            }, $uniqueEntities);

            $user = Auth::user();
            $scope = PreferenceRepository::getMainScope($user);
            $tenant = $scope->tenant;

            // Collect unique datamodel types from all entities
            $datamodels = array_unique(array_map(function ($entity) {
                return $entity['type'];
            }, $uniqueEntities));


            $subscriptionResult = AetherLinkHelper::addTypeSubscriptions($datamodels, $tenant->name, $scope->name);

            if (!$subscriptionResult) {
                return response(['error' => 'Error creating entity subscriptions'], 500);
            }


            // Create entities in Context Broker
            $result = AetherLinkHelper::createContextBrokerEntity(
                $tenant->name,
                $scope->name,
                $preparedEntities,
            );


            // If Context Broker creation succeeded, save entities to local database
            if ($result) {
                foreach ($uniqueEntities as $entityData) {
                    $entityUrn = $entityData['id'];
                    $datamodel = $entityData['type'];

                    // Use firstOrCreate to avoid race conditions and duplicate key errors
                    $entity = Entity::firstOrCreate(
                        [
                            'urn' => $entityUrn,
                            'fiware_scope_id' => $scope->id,
                        ],
                        [
                            'datamodel' => $datamodel,
                            'tenant' => $tenant->name,
                            'scope' => $scope->name,
                        ]
                    );
                }

                return response([
                    'message' => 'Entities created successfully',
                    'total_entities_in_file' => count($parsedEntities),
                ], 201);
            } else {
                return response(['error' => 'Error creating entities in Context Broker'], 500);
            }
        } catch (\Exception $e) {
            return response(['error' => 'Error creating entities: ' . $e->getMessage()], 500);
        }
    }

    /**
     * Parse entities from JSON/GeoJSON file data.
     *
     * @param array $data
     * @return array
     */
    private function parseEntitiesFromFile(array $data): array
    {
        $entities = [];

        // Check if it's a GeoJSON FeatureCollection
        if (isset($data['type']) && $data['type'] === 'FeatureCollection' && isset($data['features'])) {
            foreach ($data['features'] as $feature) {
                $entity = $this->parseGeoJSONFeature($feature);
                if ($entity) {
                    $entities[] = $entity;
                }
            }
        }
        // Check if it's an array of entities
        elseif (is_array($data) && !isset($data['type'])) {
            foreach ($data as $item) {
                $entity = $this->parseEntityObject($item);
                if ($entity) {
                    $entities[] = $entity;
                }
            }
        }
        // Single entity object
        elseif (isset($data['id']) || isset($data['entity_id'])) {
            $entity = $this->parseEntityObject($data);
            if ($entity) {
                $entities[] = $entity;
            }
        }

        return $entities;
    }

    /**
     * Parse a GeoJSON feature into an entity.
     *
     * @param array $feature
     * @return array|null
     */
    private function parseGeoJSONFeature(array $feature): ?array
    {
        if (!isset($feature['properties']['entity_id'])) {
            return null;
        }

        $entityId = $feature['properties']['entity_id'];
        $entityDatamodel = $this->extractDatamodelFromUrn($entityId);

        // Build attributes from properties (excluding entity_id and timestamp)
        $attributes = [];
        foreach ($feature['properties'] as $key => $value) {
            if ($key === 'entity_id' || $key === 'timestamp') {
                continue;
            }

            $attributes[$key] = [
                'type' => 'Property',
                'value' => $value,
            ];
        }

        // Add location from geometry if present
        if (isset($feature['geometry'])) {
            $attributes['location'] = [
                'type' => 'Property',
                'value' => $feature['geometry'],
            ];
        }

        return [
            'id' => $entityId,
            'type' => $entityDatamodel,
            'attributes' => !empty($attributes) ? $attributes : null,
        ];
    }

    /**
     * Parse a regular entity object.
     *
     * @param array $item
     * @return array|null
     */
    private function parseEntityObject(array $item): ?array
    {
        $entityId = $item['id'] ?? $item['entity_id'] ?? null;
        if (!$entityId) {
            return null;
        }

        $entityDatamodel = $item['type'] ?? $this->extractDatamodelFromUrn($entityId);

        // Build attributes from remaining properties
        $attributes = [];
        $excludedKeys = ['id', 'entity_id', 'type'];

        foreach ($item as $key => $value) {
            if (in_array($key, $excludedKeys)) {
                continue;
            }

            // Check if value is already in NGSI-LD format
            if (is_array($value) && isset($value['type']) && isset($value['value'])) {
                // Force type to Property (Context Broker doesn't accept GeoProperty)
                $value['type'] = 'Property';
                $attributes[$key] = $value;
            } else {
                $attributes[$key] = [
                    'type' => 'Property',
                    'value' => $value,
                ];
            }
        }

        return [
            'id' => $entityId,
            'type' => $entityDatamodel,
            'attributes' => !empty($attributes) ? $attributes : null,
        ];
    }

    /**
     * Extract the entity type from a URN.
     * e.g., urn:ngsi-ld:TouristDestination:TD1011 -> TouristDestination
     *
     * @param string $urn
     * @return string
     */
    private function extractDatamodelFromUrn(string $urn): string
    {
        $parts = explode(':', $urn);
        if (count($parts) >= 3) {
            return $parts[2];
        }
        return 'Unknown';
    }

    public function paginateHealthchecks(Request $request)
    {
        abort_unless(Auth::user()->can(AppPermission::ADMINISTRATION_IMPERSONATION_READ->value), 403);

        $requestBody = json_decode($request->getContent(), true);
        $paginationSize = $requestBody['paginationSize'] ?? '10';
        $page = $requestBody['page'] ?? 1;
        $orderColumn = $requestBody['orderBy'] ?? 'overall_status';
        $orderDirection = ($requestBody['orderDirection'] ?? true) == true ? 'desc' : 'asc';
        $searchText = $requestBody['search'] ?? null;
        $selectedDeviceTypes = $requestBody['selectedDeviceTypes'] ?? [];
        $selectedStatus = $requestBody['selectedStatus'] ?? [];
        $selectedOrganizations = $requestBody['selectedOrganizations'] ?? null;


        $healthchecks = EntityRepository::paginateHealthchecks(
            Auth::user()->id,
            $paginationSize,
            $page,
            $orderColumn,
            $orderDirection,
            $searchText,
            $selectedDeviceTypes,
            $selectedStatus,
            $selectedOrganizations
        );

        $result = [
            'count' => $healthchecks->total(),
            'rows' => EntityHealthcheckResource::collection($healthchecks->items()),
            'items' => $healthchecks->items(),
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function paginateEntitiesWithCommands(Request $request)
    {
        $user = Auth::user();

        $fiwareScope = PreferenceRepository::getMainScope($user);
        $scope = $fiwareScope->name;
        $tenant = $fiwareScope->tenant->name;

        $perPage = $request->input('paginationSize', 15);
        $page = $request->input('page', 1);
        $search = $request->input('search');

        $matchingEntityIds = $search
            ? EntityProperty::where('tenant', $tenant)
                ->where('scope', $scope)
                ->where('name', 'name')
                ->where('value', 'ilike', "%{$search}%")
                ->pluck('entity_id')
            : null;

        $distinctEntities = EntityCommand::select('entity_id', 'urn', 'tenant', 'scope')
            ->where('tenant', $tenant)
            ->where('scope', $scope)
            ->when($matchingEntityIds, fn($q) => $q->whereIn('entity_id', $matchingEntityIds))
            ->groupBy('entity_id', 'urn', 'tenant', 'scope')
            ->paginate($perPage, ['*'], 'page', $page);

        $pageUrns = $distinctEntities->getCollection()->pluck('urn')->all();
        $entityNames = EntityProperty::whereIn('urn', $pageUrns)
            ->where('tenant', $tenant)
            ->where('scope', $scope)
            ->where('name', 'name')
            ->get()
            ->keyBy('urn');

        $pageEntityIds = $distinctEntities->getCollection()->pluck('entity_id')->all();
        $platformEntities = Entity::whereIn('id', $pageEntityIds)->get()->keyBy('id');

        $data = $distinctEntities->getCollection()->map(function ($item) use ($entityNames, $platformEntities) {
            $platformEntity = $platformEntities->get($item->entity_id);

            return [
                'entity_id' => $item->entity_id,
                'urn'       => $item->urn,
                'tenant'    => $item->tenant,
                'scope'     => $item->scope,
                'datamodel' => $platformEntity?->datamodel,
                'name'      => $entityNames->get($item->urn)?->value,
            ];
        });

        return response()->json([
            'data'         => $data,
            'total'        => $distinctEntities->total(),
            'per_page'     => $distinctEntities->perPage(),
            'current_page' => $distinctEntities->currentPage(),
            'last_page'    => $distinctEntities->lastPage(),
        ]);
    }

    public function entitiesForAlarmActionByIds(Request $request)
    {
        $entityIds = $request->input('entity_ids', []);

        if (empty($entityIds)) {
            return response()->json([]);
        }

        $user = Auth::user();
        $fiwareScope = PreferenceRepository::getMainScope($user);
        $scope = $fiwareScope->name;
        $tenant = $fiwareScope->tenant->name;

        $entities = Entity::whereIn('id', $entityIds)->get();
        foreach ($entities as $entity) {
            $this->authorize('read', $entity);
        }

        $rows = EntityCommand::select('entity_id', 'urn', 'tenant', 'scope')
            ->where('tenant', $tenant)
            ->where('scope', $scope)
            ->whereIn('entity_id', $entityIds)
            ->groupBy('entity_id', 'urn', 'tenant', 'scope')
            ->get();

        $urns = $rows->pluck('urn')->all();
        $entityIdsArr = $rows->pluck('entity_id')->all();

        $entityNames = EntityProperty::whereIn('urn', $urns)
            ->where('tenant', $tenant)
            ->where('scope', $scope)
            ->where('name', 'name')
            ->get()
            ->keyBy('urn');

        $platformEntities = Entity::whereIn('id', $entityIdsArr)->get()->keyBy('id');

        $data = $rows->map(function ($item) use ($entityNames, $platformEntities) {
            $platformEntity = $platformEntities->get($item->entity_id);
            return [
                'entity_id' => $item->entity_id,
                'urn'       => $item->urn,
                'tenant'    => $item->tenant,
                'scope'     => $item->scope,
                'datamodel' => $platformEntity?->datamodel,
                'name'      => $entityNames->get($item->urn)?->value,
            ];
        });

        return response()->json($data);
    }
}
