<?php

namespace App\Http\V1\Controllers;

use App\Models\EntityGroup;
use App\Models\Entity;
use Illuminate\Http\Request;
use App\Http\V1\Resources\EntityGroupResource;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Http\V1\Requests\PaginationRequest;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use App\Repositories\ResourcePermissionRepository;
use App\Repositories\OrganizationRepository;
use App\Repositories\PreferenceRepository;
use App\Authorization\AppResourcePermission;
use App\Helpers\AetherLinkHelper;
use Illuminate\Support\Facades\Http;
use Illuminate\Validation\Rule;

class EntityGroupController extends Controller
{
    /** The lifecycle states an incident / intervention can hold (canonical model + `assigned`). */
    private const INCIDENT_STATES = ['open', 'inProgress', 'assigned', 'resolved', 'closed', 'cancelled'];
    public function paginate(PaginationRequest $request)
    {

        $this->authorize('list', EntityGroup::class);

        $query = EntityGroup::with(['entities', 'linkedEntity'])
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'like', '%' . $search . '%');
            })
            ->when($request->types, function ($query, $types) {
                $hasNull = in_array('null', $types);
                $nonNullTypes = array_values(array_filter($types, fn($t) => $t !== 'null'));

                return $query->where(function ($q) use ($hasNull, $nonNullTypes) {
                    if ($hasNull)
                        $q->whereNull('type');
                    if (!empty($nonNullTypes))
                        $q->orWhereIn('type', $nonNullTypes);
                });
            })
            // Keep only groups that contain at least one entity of the given datamodel(s).
            ->when($request->entityDatamodels, function ($query, $entityDatamodels) {
                $datamodels = is_array($entityDatamodels) ? $entityDatamodels : explode(',', $entityDatamodels);

                return $query->whereHas('entities', function ($q) use ($datamodels) {
                    $q->whereIn('entities.datamodel', $datamodels);
                });
            })
            ->when($request->linked_entity_ids, function ($query, $linkedEntityIds) {
                return $query->whereIn('entity_id', $linkedEntityIds);
            })
            ->when($request->orderBy, function ($query, $orderBy) use ($request) {
                return $query->orderBy($orderBy, $request->orderDirection ? 'asc' : 'desc');
            });

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            Auth::id(),
            EntityGroup::class
        );

        // pagination
        $entityGroups = $query->paginate(
            $request->paginationSize,
            ['entity_groups.*'],
            'page',
            $request->page
        );

        $result = [
            'rows' => EntityGroupResource::collection($entityGroups->items()),
            'count' => $entityGroups->total(),
            'items' => $entityGroups->items(),
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $user = Auth::user();

        $this->authorize('create', EntityGroup::class);

        $type = $request->input('type');

        $rules = [
            'name'          => 'required|string',
            'description'   => 'nullable|string',
            'entities'      => 'required|array',
            'entities.*.id' => 'required|integer',
        ];
        if ($type !== null) {
            $rules['urn'] = ['required', 'string', Rule::unique('entities', 'urn')];
        }
        if ($type === 'CrowdGroup') {
            $rules['max_capacity'] = 'required|integer|min:1';
            $rules['total_area'] = 'nullable|integer|min:1';
            $rules['location'] = 'nullable|array';
            $rules['location.type'] = 'required_with:location|string|in:Polygon';
            $rules['location.coordinates'] = 'required_with:location|array';
        }
        $request->validate($rules);

        $entityIds = array_column($request->entities, 'id');
        $entities  = Entity::whereIn('id', $entityIds)->get();

        foreach ($entities as $entity) {
            $this->authorize('read', $entity);
            if ($type !== null) {
                $this->validateMemberEntity($entity, $type);
            }
        }

        if ($type !== null) {
            return $this->storeLinkedGroup($request, $user, $type, $entityIds, $entities);
        }

        $entityGroup = new EntityGroup([
            'name'        => $request->name,
            'description' => $request->description,
            'user_id'     => $user->id,
        ]);

        if (!$entityGroup->save()) {
            return response('The operation couldn\'t be completed (store)', 500);
        }

        $entityGroup->entities()->attach($entityIds);
        OrganizationRepository::assignResourceToOrganization($user->organization_id, $entityGroup);
        $user->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $entityGroup, true);

        return (new EntityGroupResource($entityGroup))->response()->setStatusCode(201);
    }

    /**
     * Display the specified resource.
     */
    public function show(int $id)
    {
        $entityGroup = EntityGroup::with(['entities', 'linkedEntity'])
            ->findOrFail($id);

        $this->authorize('read', $entityGroup);

        return (new EntityGroupResource($entityGroup))->response();
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, int $id)
    {
        $entityGroup = EntityGroup::with('linkedEntity')->findOrFail($id);

        $this->authorize('update', $entityGroup);

        $rules = [
            'name'          => 'required|string',
            'description'   => 'nullable|string',
            'entities'      => 'required|array',
            'entities.*.id' => 'required|integer',
        ];
        if ($entityGroup->type === null) {
            $rules['user_id'] = 'required|numeric';
        }
        if ($entityGroup->type === 'CrowdGroup') {
            $rules['max_capacity'] = 'required|integer|min:1';
            $rules['total_area'] = 'nullable|integer|min:1';
        }
        $request->validate($rules);

        $entityIds = array_column($request->entities, 'id');
        $entities  = Entity::whereIn('id', $entityIds)->get();

        foreach ($entities as $entity) {
            $this->authorize('read', $entity);
            if ($entityGroup->type !== null) {
                $this->validateMemberEntity($entity, $entityGroup->type);
            }
        }

        $fieldsToFill = ['name', 'description'];
        if ($entityGroup->type === 'CrowdGroup') {
            $fieldsToFill[] = 'max_capacity';
            $fieldsToFill[] = 'total_area';
        }
        $entityGroup->fill($request->only($fieldsToFill));

        if (!$entityGroup->save()) {
            return response('The operation couldn\'t be completed (update)', 500);
        }

        $entityGroup->entities()->sync($entityIds);

        if ($entityGroup->type !== null) {
            $this->enqueueLinkedEntityGroupUpdate($entityGroup->id, force: true);
        }

        return response(null, 204);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(int $id)
    {
        $entityGroup = EntityGroup::with('linkedEntity')->findOrFail($id);

        $this->authorize('delete', $entityGroup);

        DB::transaction(function () use ($entityGroup) {
            ResourcePermissionRepository::deleteAllPermissionsForResource($entityGroup);
            OrganizationRepository::unassignResourceFromAnyOrganization($entityGroup);

            if ($entityGroup->linkedEntity) {
                $linkedEntity = $entityGroup->linkedEntity;

                AetherLinkHelper::deleteEntities(
                    [$linkedEntity->urn],
                    $linkedEntity->tenant,
                    $linkedEntity->scope
                );

                $entityGroup->delete();
                $linkedEntity->delete();
            } else {
                $entityGroup->delete();
            }
        });

        return response(null, 204);
    }

    /**
     * Handle the creation of a typed group linked to a Context Broker entity.
     */
    private function storeLinkedGroup(Request $request, $user, string $type, array $entityIds, $entities)
    {
        $scope  = PreferenceRepository::getMainScope($user);
        $tenant = $scope->tenant;

        if (!AetherLinkHelper::addTypeSubscriptions([$type], $tenant->name, $scope->name)) {
            return response('Error creating entity subscriptions', 500);
        }

        $attributes = ['name' => ['type' => 'Property', 'value' => $request->name]];

        $crowdTotalArea = null;

        if ($type === 'CrowdGroup') {
            $crowdTotalArea = $request->total_area ? (int) $request->total_area : null;
            $attributes += $this->buildCrowdGroupInitialCBAttributes((int) $request->max_capacity, $request->location, $crowdTotalArea);
            $attributes['occupancy'] = ['type' => 'Property', 'value' => 0];
            $attributes['visitors']  = ['type' => 'Property', 'value' => 0];
        }

        if (!AetherLinkHelper::createContextBrokerEntity($tenant->name, $scope->name, [[
            'id'         => $request->urn,
            'type'       => $type,
            'attributes' => $attributes,
        ]])) {
            return response('Error creating entity in Context Broker', 500);
        }

        $linkedEntity = Entity::firstOrCreate(
            ['urn' => $request->urn, 'fiware_scope_id' => $scope->id],
            ['datamodel' => $type, 'tenant' => $tenant->name, 'scope' => $scope->name]
        );

        $group = EntityGroup::firstOrCreate(
            ['entity_id' => $linkedEntity->id],
            [
                'name'         => $request->name,
                'description'  => $request->description ?? '',
                'type'         => $type,
                'user_id'      => $user->id,
                'max_capacity' => $request->max_capacity ?? null,
                'total_area'   => $crowdTotalArea,
            ]
        );

        $group->entities()->sync($entityIds);
        OrganizationRepository::assignResourceToOrganization($user->organization_id, $group);
        $user->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $group, true);
        $this->enqueueLinkedEntityGroupUpdate($group->id);

        $group->load(['linkedEntity', 'entities']);

        return (new EntityGroupResource($group))->response()->setStatusCode(201);
    }

    /**
     * Validate that a member entity is allowed for the given group type.
     */
    private function validateMemberEntity(Entity $entity, string $type): void
    {
        $allowedDatamodels = $this->getAllowedMemberDatamodels($type);

        if (!empty($allowedDatamodels) && !in_array($entity->datamodel, $allowedDatamodels)) {
            abort(422, "Entity datamodel '{$entity->datamodel}' is not allowed in a {$type} group.");
        }
    }

    /**
     * Returns the allowed member datamodels for a given group type.
     */
    private function getAllowedMemberDatamodels(string $type): array
    {
        return match ($type) {
            'ParkingGroup'      => ['ParkingSpot'],
            'CrowdGroup'        => ['CrowdFlowEvent'],
            default             => [],
        };
    }

    private function enqueueLinkedEntityGroupUpdate(int $groupId, bool $force = false): void
    {
        try {
            Http::withHeaders(['X-Queues-Consumer-Token' => config('services.queues-consumer.token')])
                ->post(config('services.queues-consumer.publish'), [
                'task'   => 'platform.entity_groups.update',
                'params' => ['group_id' => $groupId, 'force' => $force],
            ]);
        } catch (\Illuminate\Http\Client\ConnectionException $e) {
            \Illuminate\Support\Facades\Log::warning('EntityGroup queue publish failed', [
                'group_id' => $groupId,
                'error'    => $e->getMessage(),
            ]);
        }
    }
}
