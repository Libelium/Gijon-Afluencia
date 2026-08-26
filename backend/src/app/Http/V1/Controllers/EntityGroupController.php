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
use App\Helpers\NotificationHelper;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
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
        if ($type === 'AssetIntervention') {
            // Optional assignment written at creation (operator and/or team). See storeLinkedGroup.
            $rules['category']       = 'nullable|string';
            $rules['assignedTo']       = 'nullable|string';
            $rules['assignedToName']   = 'nullable|string';
            $rules['assignedTeam']     = 'nullable|string';
            $rules['assignedTeamName'] = 'nullable|string';
            $rules['assignmentType']   = 'nullable|string|in:individual,team';
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

        // A member Incident belongs to at most ONE AssetIntervention (exclusive membership).
        if ($type === 'AssetIntervention') {
            $this->assertIncidentsNotInAnotherIntervention($entityIds);
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

        // Exclusive membership: a member Incident may not already belong to ANOTHER AssetIntervention.
        if ($entityGroup->type === 'AssetIntervention') {
            $this->assertIncidentsNotInAnotherIntervention($entityIds, $entityGroup->id);
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

        if ($type === 'AssetIntervention') {
            // Starts 'open'. `refersTo` keeps the aggregated incidents as a Property array of URNs
            // (AetherLink doesn't relay Relationship `object`).
            if ($request->category) {
                $attributes['category'] = ['type' => 'Property', 'value' => $request->category];
            }
            $attributes['status'] = ['type' => 'Property', 'value' => 'open'];
            $attributes['operatorId'] = ['type' => 'Property', 'value' => (string) $user->id];
            $attributes['refersTo'] = ['type' => 'Property', 'value' => $entities->pluck('urn')->values()->all()];

            $attributes += $this->buildAssignmentCBAttributes($request);
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

        // Aggregating incidents moves them to 'assigned' (governed by the intervention now).
        if ($type === 'AssetIntervention') {
            $this->cascadeIncidentStatus($entities, 'assigned', (int) $user->id);

            // Best-effort: notify the operator / team assigned at creation.
            if ($request->assignedTo !== null || $request->assignedTeam !== null) {
                try {
                    NotificationHelper::notifyAssignees(
                        $request->assignedTo !== null ? (string) $request->assignedTo : null,
                        $request->assignedTeam !== null ? (string) $request->assignedTeam : null,
                        (int) $user->id,
                        ['ref' => $request->name, 'name' => $request->name],
                    );
                } catch (\Throwable $e) {
                    Log::warning('intervention.assign.notify.failed', ['error' => $e->getMessage()]);
                }
            }
        }

        $group->load(['linkedEntity', 'entities']);

        return (new EntityGroupResource($group))->response()->setStatusCode(201);
    }

    /**
     * Change an AssetIntervention's status and cascade it to all its member incidents (their status
     * is governed by the intervention). Each reporter is notified; the closure ('closed') carries a
     * dedicated message. Only valid for `AssetIntervention` groups.
     */
    public function updateStatus(Request $request, int $id)
    {
        $group = EntityGroup::with(['linkedEntity', 'entities'])->findOrFail($id);
        $this->authorize('update', $group);

        if ($group->type !== 'AssetIntervention') {
            abort(422, 'Status updates are only supported for AssetIntervention groups.');
        }

        $request->validate([
            'status' => ['required', 'string', Rule::in(self::INCIDENT_STATES)],
            'publicNote' => ['sometimes', 'nullable', 'string'],
        ]);
        $status = $request->input('status');
        $publicNoteRaw = $request->input('publicNote');
        $publicNote = is_string($publicNoteRaw) && trim($publicNoteRaw) !== '' ? $publicNoteRaw : null;

        // Update the intervention's own status in the Context Broker.
        $linked = $group->linkedEntity;
        if ($linked) {
            AetherLinkHelper::updateOnContextBroker($linked->urn, $linked->tenant, $linked->scope, [
                'status' => ['type' => 'Property', 'value' => $status],
            ]);
        }

        // Cascade to the member incidents (+ notify each reporter).
        $this->cascadeIncidentStatus($group->entities, $status, (int) Auth::id(), $publicNote);

        return response()->json(['id' => (string) $group->id, 'status' => $status]);
    }

    /**
     * Push a status to every Incident member (direct broker write, bypassing the per-entity API
     * guard) and notify each reporter. 'closed' uses a dedicated closure notification.
     */
    private function cascadeIncidentStatus($members, string $status, int $actorId, ?string $publicNote = null): void
    {
        foreach ($members as $member) {
            if ($member->datamodel !== 'Incident') {
                continue;
            }

            $attrs = ['status' => ['type' => 'Property', 'value' => $status]];
            if ($status === 'closed' && $publicNote !== null) {
                $attrs['publicNote'] = ['type' => 'Property', 'value' => $publicNote];
            }

            AetherLinkHelper::updateOnContextBroker($member->urn, $member->tenant, $member->scope, $attrs);

            // Best-effort: a notify failure must not abort the cascade for the remaining members.
            try {
                $isClose = $status === 'closed';
                NotificationHelper::notifyIncidentReporter(
                    $member->id,
                    $actorId,
                    $isClose ? 'notifications.interventionClosed' : 'notifications.incidentStatus',
                    $isClose ? '' : 'notifications.incidentStatusSub',
                    $isClose ? 'tabler-checkbox' : 'tabler-refresh',
                    ['ref' => NotificationHelper::incidentRef($member->id), 'status' => $status],
                );
            } catch (\Throwable $e) {
                Log::warning('incident.cascade.notify.failed', ['error' => $e->getMessage()]);
            }
        }
    }

    /**
     * Build the Context Broker attributes specific to a CrowdGroup (maxCapacity + location + totalArea).
     * Does not include initial stats (occupancy, visitors) — those are only set on creation.
     */
    private function buildCrowdGroupInitialCBAttributes(int $maxCapacity, ?array $polygon, ?int $totalArea = null): array
    {
        $attributes = [
            'maxCapacity' => ['type' => 'Property', 'value' => $maxCapacity],
        ];

        if ($polygon) {
            $attributes['location'] = ['type' => 'Property', 'value' => $polygon];
        }

        if ($totalArea !== null) {
            $attributes['totalArea'] = ['type' => 'Property', 'value' => $totalArea];
        }

        return $attributes;
    }

    /**
     * Build the Context Broker attributes for an AssetIntervention's assignment (operator and/or
     * team). Empty when nothing is assigned. `assignedAt` is stamped whenever a target is present.
     */
    private function buildAssignmentCBAttributes(Request $request): array
    {
        $attributes = [];

        if ($request->assignedTo !== null) {
            $attributes['assignedTo'] = ['type' => 'Property', 'value' => (string) $request->assignedTo];
        }
        if ($request->assignedToName !== null) {
            $attributes['assignedToName'] = ['type' => 'Property', 'value' => (string) $request->assignedToName];
        }
        if ($request->assignedTeam !== null) {
            $attributes['assignedTeam'] = ['type' => 'Property', 'value' => (string) $request->assignedTeam];
        }
        if ($request->assignedTeamName !== null) {
            $attributes['assignedTeamName'] = ['type' => 'Property', 'value' => (string) $request->assignedTeamName];
        }
        if ($request->assignmentType !== null) {
            $attributes['assignmentType'] = ['type' => 'Property', 'value' => (string) $request->assignmentType];
        }
        if ($request->assignedTo !== null || $request->assignedTeam !== null) {
            $attributes['assignedAt'] = ['type' => 'Property', 'value' => now()->toIso8601String()];
        }

        return $attributes;
    }

    /**
     * Enforce exclusive membership: none of the given Incident entities may already belong to another
     * AssetIntervention group. Aborts 422 listing the offending entity ids. `$excludeGroupId` skips the
     * group being updated so re-saving its own members does not trip the guard.
     */
    private function assertIncidentsNotInAnotherIntervention(array $entityIds, ?int $excludeGroupId = null): void
    {
        $clashing = EntityGroup::query()
            ->where('type', 'AssetIntervention')
            ->when($excludeGroupId, fn ($q) => $q->where('id', '!=', $excludeGroupId))
            ->whereHas('entities', fn ($q) => $q->whereIn('entities.id', $entityIds))
            ->with(['entities' => fn ($q) => $q->whereIn('entities.id', $entityIds)])
            ->get()
            ->flatMap(fn ($group) => $group->entities->pluck('id'))
            ->unique()
            ->values()
            ->all();

        if (!empty($clashing)) {
            abort(422, 'Incidents already belong to an intervention: ' . implode(', ', $clashing));
        }
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
            'AssetIntervention' => ['Incident'],
            default             => [],
        };
    }

    private function enqueueLinkedEntityGroupUpdate(int $groupId, bool $force = false): void
    {
        try {
            Http::post(config('services.queues-consumer.publish'), [
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
