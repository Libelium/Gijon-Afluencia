<?php

namespace App\Repositories;

use App\Authorization\AppResourcePermission;
use App\Models\Workspace;
use App\Authorization\ResourcePermissionCache;
use App\Models\Entity;
use App\Models\FiwareScope;
use Illuminate\Support\Facades\Auth;
use App\Models\Authorization\ModelHasResourcePermission;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;


class WorkspaceRepository
{
    public static function checkScopePermissions($scope, $permission)
    {
        $canPermission = ResourcePermissionRepository::UserHasResourcePermissionToModel(Auth::user(), $permission, 'fiware_scopes', $scope->id);

        if (!$canPermission) {
            $canPermission = ResourcePermissionRepository::UserHasResourcePermissionToModel(Auth::user(), $permission, 'fiware_tenants', $scope->fiware_tenant_id);
        }

        return $canPermission;
    }

    public static function checkEntityPermissions($entity, $permission)
    {
        $canPermission = ResourcePermissionRepository::UserHasResourcePermissionToModel(Auth::user(), $permission, 'entities', $entity->id);

        if (!$canPermission) {
            $canPermission = self::checkScopePermissions($entity->fiwareScope, $permission);
        }

        return $canPermission;
    }
    /**
     * Return paginated results using query and filters
     *
     * @return Illuminate\Support\Collection
     */

    public static function paginate($request)
    {
        $user_id = Auth::id();

        $query = Workspace::query()
            // search
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'like', '%' . $search . '%')->orWhere('description', 'like', '%' . $search . '%');
            })
            // sort
            ->when($request->orderBy, function ($query, $orderBy) use ($request) {
                return $query->orderBy($orderBy, $request->orderDirection ? 'asc' : 'desc');
            })
            ->groupBy('workspaces.id');

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            $user_id,
            Workspace::class
        );

        // pagination
        $workspaces = $query->with(['users', 'resources', 'admin'])->paginate(
            $request->paginationSize,
            ['workspaces.*'],
            'page',
            $request->page
        );

        return [
            'rows' => $workspaces->items(),
            'count' => $workspaces->total(),
        ];
    }

    public static function createWorkspaceUsers($workspace, $users)
    {
        $user_ids = [];
        foreach ($users as $user) {
            $user_ids[] = $user['id'];
        }

        $workspace->users()->sync($user_ids);

        // remove previous permissions (except for the owner)
        ModelHasResourcePermission::where('resource_id', $workspace->id)
            ->where('resource_type', 'workspaces')
            ->where('model_type', 'users')
            ->whereNot('model_id', Auth::id())->delete();

        // add read permissions to the users
        $permissions = [];

        $permissions_per_user = [app(ResourcePermissionCache::class)->getPermissionId(AppResourcePermission::READ)];

        if ($workspace->collaborative) {
            $permissions_per_user[] = app(ResourcePermissionCache::class)->getPermissionId(AppResourcePermission::UPDATE);
        }

        $now = now();
        foreach ($user_ids as $user_id) {
            foreach ($permissions_per_user as $permission_id) {
                $permissions[] = [
                    'resource_id' => $workspace->id,
                    'resource_type' => 'workspaces',
                    'resource_permission_id' => $permission_id,
                    'model_id' => $user_id,
                    'model_type' => 'users',
                    'created_at' => $now,
                    'updated_at' => $now,
                ];
            }
        }

        $unique = collect($permissions)
            ->unique(fn ($r) => $r['model_id'] . '|' . $r['model_type'] . '|' . $r['resource_permission_id'] . '|' . $r['resource_type'] . '|' . $r['resource_id'])
            ->values()
            ->all();

        ModelHasResourcePermission::upsert(
            $unique,
            ['model_id', 'model_type', 'resource_permission_id', 'resource_type', 'resource_id'],
            ['updated_at']
        );
    }
    /**
    * Crea las asociaciones workspace–recurso–permiso tras validar que el usuario
    * tenga permiso (directo o indirecto) sobre cada recurso.
    *
    * - Recolecta permisos de la petición y separa recursos por tipo.
    * - Mapea cada clave de permiso a su Enum e ID en BD.
    * - Carga entidades y scopes (y sus tenants) necesarios.
    * - Calcula recursos autorizados por permiso (directo por entidad, o indirecto
    *   vía scope o tenant).
    * - Construye e inserta las filas en la tabla pivot en lotes.
    *
    * No inserta nada si no hay permisos, no hay modelos actor del usuario,
    * o ningún recurso queda autorizado.
    *
    * @param $workspace Workspace destino.
    * @param array<array{id:int,type:string,permissions:string[]}> $resources
    *        Recursos a asociar (ids + tipo + permisos solicitados).
    * @return void
    */
    public static function createWorkspaceResources($workspace, array $resources): void
    {
        $user = Auth::user();

        [$permissionKeys, $byType] = self::collectPermissionKeysAndSplitResources($resources);
        if (empty($permissionKeys)) return;

        [$permissionEnumByKey, $permissionIdByKey] = self::mapPermissionKeys($permissionKeys);

        [$entitiesByIdMap, $entityTenantIds] = self::loadEntities($byType['entityIds']);
        [$scopeIdToTenantId, $scopeTenantIds] = self::loadScopes($byType['fiwareScopeIds']);

        $userActorModels = ResourcePermissionRepository::getUserModels($user);
        if (empty($userActorModels)) return;

        [$allowedEntities, $allowedScopes, $allowedTenants] =
            self::computeAllowedSets(
                $permissionKeys,
                $permissionIdByKey,
                $userActorModels,
                $byType['entityIds'],
                $entitiesByIdMap,
                $byType['fiwareScopeIds'],
                $entityTenantIds,
                $scopeTenantIds
            );

        $rows = self::buildInsertRows(
            $workspace,
            $resources,
            $permissionIdByKey,
            $permissionEnumByKey,
            $allowedEntities,
            $allowedScopes,
            $allowedTenants,
            $entitiesByIdMap,
            $scopeIdToTenantId
        );

        if (empty($rows)) return;

        self::insertInChunks($workspace, $rows, chunkSize: 1000);
    }

    /**
    * Extrae las claves de permisos únicas de la lista de recursos y
    * separa los recursos por tipo para su procesamiento.
    *
    * @param array $resources Lista de recursos a procesar.
    *
    * @return array [
    *   array $permissionKeys, // Claves de permisos únicas (READ O WRITE)
    *   array $byType => [
    *       'entityIds'      => array, // IDs de entidades
    *       'fiwareScopeIds' => array, // IDs de scopes FIWARE
    *       'other'          => array, // Otros tipos de recursos con sus IDs
    *   ]
    * ]
    */

    private static function collectPermissionKeysAndSplitResources(array $resources): array
    {
        // permisos únicos
        $permissionKeys = [];
        foreach ($resources as $r) {
            foreach (($r['permissions'] ?? []) as $p) $permissionKeys[$p] = true;
        }
        $permissionKeys = array_keys($permissionKeys);

        // ids por tipo
        $entityIds = $scopeIds = [];
        $otherByType = [];
        foreach ($resources as $r) {
            $id = (int)$r['id'];
            if ($r['type'] === 'entities')        $entityIds[] = $id;
            elseif ($r['type'] === 'fiware_scopes') $scopeIds[]  = $id;
            else                                    $otherByType[$r['type']][] = $id;
        }
        $entityIds = array_values(array_unique($entityIds));
        $scopeIds  = array_values(array_unique($scopeIds));
        foreach ($otherByType as $t => $ids) $otherByType[$t] = array_values(array_unique($ids));

        return [
            $permissionKeys,
            ['entityIds' => $entityIds, 'fiwareScopeIds' => $scopeIds, 'other' => $otherByType],
        ];
    }

    /**
    * Genera mapas que relacionan cada clave de permiso con:
    * - Su AppResourcePermission (enum) asociado .
    * - Su ID en base de datos.
    *
    * @param array $permissionKeys Claves de permisos únicas.
    *
    * @return array [
    *   array $enumByKey, // Mapa clave => enum
    *   array $idByKey    // Mapa clave => ID en BD, "read" => 1, "update" => 2
    * ]
    */

    private static function mapPermissionKeys(array $permissionKeys): array
    {
        $enumByKey = $idByKey = [];
        foreach ($permissionKeys as $key) {
            $enumByKey[$key] = AppResourcePermission::fromValue($key);
            $idByKey[$key]   = app(ResourcePermissionCache::class)->getPermissionId($enumByKey[$key]);
        }
        return [$enumByKey, $idByKey];
    }

    /**
    * Carga entidades desde la base de datos junto con su scope relacionado,
    * y extrae los IDs de tenants asociados.
    *
    * @param array $entityIds IDs de entidades a cargar.
    *
    * @return array [
    *   \Illuminate\Support\Collection $entitiesByIdMap, // Entidades indexadas por ID
    *   array $tenantIds, // IDs únicos de tenants relacionados
    * ]
    */
    private static function loadEntities(array $entityIds): array
    {
        if (empty($entityIds)) return [collect(), []];

        $entities = Entity::query()
            ->with('fiwareScope:id,fiware_tenant_id')
            ->whereIn('id', $entityIds)
            ->get()
            ->keyBy('id');

        $tenantIds = [];
        foreach ($entities as $e) {
            $t = $e->fiwareScope?->fiware_tenant_id;
            if ($t) $tenantIds[] = (int)$t;
        }
        $tenantIds = array_values(array_unique($tenantIds));

        return [$entities, $tenantIds];
    }

    /**
    * Carga scopes desde la base de datos y obtiene un mapa de:
    * scope_id => tenant_id, así como una lista de tenant IDs únicos.
    *
    * @param array $scopeIds IDs de scopes a cargar.
    *
    * @return array [
    *   array $scopeIdToTenantId, // Mapa scope_id => tenant_id
    *   array $tenantIds          // IDs únicos de tenants
    * ]
    */
    private static function loadScopes(array $scopeIds): array
    {
        if (empty($scopeIds)) return [[], []];

        $map = []; $tenantIds = [];
        $scopes = FiwareScope::query()
            ->whereIn('id', $scopeIds)
            ->get(['id','fiware_tenant_id']);

        foreach ($scopes as $s) {
            $tid = $s->fiware_tenant_id ? (int)$s->fiware_tenant_id : null;
            $map[(int)$s->id] = $tid;
            if ($tid) $tenantIds[] = $tid;
        }
        $tenantIds = array_values(array_unique($tenantIds));

        return [$map, $tenantIds];
    }

    /**
    * Determina los recursos que el usuario tiene autorizados según
    * sus permisos sobre entidades, scopes y tenants.
    *
    * Proceso:
    * 1. Verifica permisos directos sobre entidades.
    * 2. Si no tiene permisos directos sobre la entidad, fallback al scope de la entidad.
    * 3. Para los fiware_scopes verifica si tiene permisos sobre ellos.
    * 4. Verifica permisos a nivel de tenants para todas entidades y todos fiware_scopes 
    *    (los que vienen en los recursos).
    *
    * @param array $permissionKeys Claves de permisos a evaluar.
    * @param array $permissionIdByKey Mapa clave => ID de permiso en BD.
    * @param array $userActorModels Modelos de usuario a usar para verificación de permisos.
    * @param array $entityIds IDs de entidades.
    * @param \Illuminate\Support\Collection $entitiesByIdMap Entidades indexadas por ID.
    * @param array $fiwareScopeIds IDs de scopes FIWARE.
    * @param array $entityTenantIds IDs de tenants relacionados con entidades.
    * @param array $scopeTenantIds IDs de tenants relacionados con scopes.
    *
    * @return array [
    *   array $allowedEntity, // Mapa por permiso: entity_id => true
    *   array $allowedScope,  // Mapa por permiso: scope_id => true
    *   array $allowedTenant, // Mapa por permiso: tenant_id => true
    * ]
    */

    private static function computeAllowedSets(
        array $permissionKeys,
        array $permissionIdByKey,
        array $userActorModels,
        array $entityIds,
        \Illuminate\Support\Collection $entitiesByIdMap,
        array $fiwareScopeIds,
        array $entityTenantIds,
        array $scopeTenantIds
    ): array {
        $allowedEntity   = []; 
        $allowedScope    = []; 
        $allowedTenant   = []; 

        foreach ($permissionKeys as $key) {
            $pid = $permissionIdByKey[$key] ?? null;

            // por defecto, sets vacíos
            $allowedEntity[$key] = [];
            $allowedScope[$key]  = [];
            $allowedTenant[$key] = [];

            if (!$pid) continue;

            // entities directos
            if (!empty($entityIds)) {
                $ids = ResourcePermissionRepository::userHasResourcePermissionToModelsBulk(
                    $userActorModels, $pid, 'entities', $entityIds
                );
                $allowedEntity[$key] = array_fill_keys($ids, true);

                // fallback scope para entidades que no quedaron permitidas
                $pending = [];
                foreach ($entityIds as $eid) {
                    if (!isset($allowedEntity[$key][$eid])) {
                        $sid = $entitiesByIdMap->get($eid)?->fiwareScope?->id;
                        if ($sid !== null) $pending[$eid] = (int)$sid;
                    }
                }
                if (!empty($pending)) {
                    $scopeIds = array_values(array_unique(array_values($pending)));
                    $allowedScopesFromPending = ResourcePermissionRepository::userHasResourcePermissionToModelsBulk(
                        $userActorModels, $pid, 'fiware_scopes', $scopeIds
                    );
                    $scopeSet = array_fill_keys($allowedScopesFromPending, true);
                    foreach ($pending as $eid => $sid) {
                        if (isset($scopeSet[$sid])) $allowedEntity[$key][$eid] = true;
                    }
                }
            }

            // scopes directos
            if (!empty($fiwareScopeIds)) {
                $scopes = ResourcePermissionRepository::userHasResourcePermissionToModelsBulk(
                    $userActorModels, $pid, 'fiware_scopes', $fiwareScopeIds
                );
                $allowedScope[$key] = array_fill_keys($scopes, true);
            }

            // tenants (union)
            $tenantUnion = array_values(array_unique(array_merge($entityTenantIds, $scopeTenantIds)));
            if (!empty($tenantUnion)) {
                $tids = ResourcePermissionRepository::userHasResourcePermissionToModelsBulk(
                    $userActorModels, $pid, 'fiware_tenants', $tenantUnion
                );
                $allowedTenant[$key] = array_fill_keys($tids, true);
            }
        }

        return [$allowedEntity, $allowedScope, $allowedTenant];
    }

    /**
    * Construye filas listas para insertar en la base de datos con la
    * relación entre el workspace, los recursos y los permisos validados.
    *
    * Reglas de autorización:
    * - Si el recurso es entidad, revisa permisos directos, luego indirectos por scope y tenant.
    * - Si es un scope, revisa permisos directos o indirectos por tenant.
    * - Si es otro tipo, verifica permisos individualmente.
    *
    * @param $workspace Workspace al que se asocian los recursos.
    * @param array $resources Recursos a procesar.
    * @param array $permissionIdByKey Mapa clave => ID de permiso en BD.
    * @param array $permissionEnumByKey Mapa clave => Enum del permiso.
    * @param array $allowedEntitySetByPerm Recursos de entidades permitidos por permiso.
    * @param array $allowedScopeSetByPerm Recursos de scopes permitidos por permiso.
    * @param array $allowedTenantSetByPerm Tenants permitidos por permiso.
    * @param \Illuminate\Support\Collection $entitiesByIdMap Entidades indexadas por ID.
    * @param array $scopeIdToTenantId Mapa scope_id => tenant_id.
    *
    * @return array Filas a insertar en la tabla pivot.
    */

    private static function buildInsertRows(
        $workspace,
        array $resources,
        array $permissionIdByKey,
        array $permissionEnumByKey,
        array $allowedEntitySetByPerm,
        array $allowedScopeSetByPerm,
        array $allowedTenantSetByPerm,
        \Illuminate\Support\Collection $entitiesByIdMap,
        array $scopeIdToTenantId
    ): array {
        $rows = [];
        $now  = Carbon::now();
        $morph = $workspace->getMorphClass();

        foreach ($resources as $r) {
            $rid = (int)$r['id'];
            $type = $r['type'];

            foreach ($r['permissions'] as $key) {
                $pid = $permissionIdByKey[$key] ?? null;
                if (!$pid) continue;

                $authorized = false;

                if ($type === 'entities') {
                    if (isset($allowedEntitySetByPerm[$key][$rid])) {
                        $authorized = true;
                    } else {
                        $entity = $entitiesByIdMap->get($rid);
                        if (!$entity) continue;
                        $sid = $entity->fiwareScope?->id;
                        $tid = $entity->fiwareScope?->fiware_tenant_id;

                        $authorized =
                            ($sid && isset($allowedScopeSetByPerm[$key][$sid]))
                            || ($tid && isset($allowedTenantSetByPerm[$key][$tid]));
                    }
                } elseif ($type === 'fiware_scopes') {
                    $authorized =
                        isset($allowedScopeSetByPerm[$key][$rid])
                        || (($scopeIdToTenantId[$rid] ?? null) && isset($allowedTenantSetByPerm[$key][$scopeIdToTenantId[$rid]]));
                } else {
                    // chequeo unitario para otros tipos
                    $enum = $permissionEnumByKey[$key];
                    $authorized = ResourcePermissionRepository::UserHasResourcePermissionToModel(
                        Auth::user(), $enum, $type, $rid
                    );
                }

                if (!$authorized) continue;

                $rows[] = [
                    'model_id'               => $workspace->id,
                    'model_type'             => $morph,
                    'resource_id'            => $rid,
                    'resource_type'          => $type,
                    'resource_permission_id' => $pid,
                    'created_at'             => $now,
                    'updated_at'             => $now,
                ];
            }
        }

        return $rows;
    }
    /**
    * Inserta filas en la base de datos en chunks dentro de una transacción
    * para optimizar rendimiento y evitar bloqueos por grandes cantidades de datos.
    *
    * @param $workspace Workspace relacionado.
    * @param array $rows Filas a insertar.
    * @param int $chunkSize Tamaño de cada lote de inserción (default 1000).
    *
    * @return void
    */

    private static function insertInChunks($workspace, array $rows, int $chunkSize = 1000): void
    {
        $unique = collect($rows)
            ->unique(fn ($r) => $r['model_id'] . '|' . $r['model_type'] . '|' . $r['resource_permission_id'] . '|' . $r['resource_type'] . '|' . $r['resource_id'])
            ->values()
            ->all();

        DB::transaction(function () use ($unique, $chunkSize) {
            foreach (array_chunk($unique, $chunkSize) as $chunk) {
                ModelHasResourcePermission::upsert(
                    $chunk,
                    ['model_id', 'model_type', 'resource_permission_id', 'resource_type', 'resource_id'],
                    ['updated_at']
                );
            }
        });
    }

    private static function findInResources($resources, $id, $type, $permission)
    {
        foreach ($resources as $resource) {
            $permission_ids = [];
            foreach ($resource['permissions'] as $perm) {
                $permission_ids[] = app(ResourcePermissionCache::class)->getPermissionId(AppResourcePermission::fromValue($perm));
            }
            if ($resource['id'] === $id && $resource['type'] === $type && in_array($permission, $permission_ids)) {
                return true;
            }
        }

        return false;
    }

    private static function getDiffPermissions($workspace, $resources)
    {
        $old = $workspace->resources;

        $diff = [];

        foreach ($old as $old_resource) {
            $found = self::findInResources($resources, $old_resource->resource_id, $old_resource->resource_type, $old_resource->resource_permission_id);

            if (!$found) {
                $diff[] = [
                    'id' => $old_resource->resource_id,
                    'type' => $old_resource->resource_type,
                    'resource_permission_id' => $old_resource->resource_permission_id,
                ];
            }
        }

        return $diff;
    }

    /**
     * Delete all resources associated with a workspace.
     * Used before recreating resources to avoid duplicates.
     */
    public static function deleteAllWorkspaceResources($workspace)
    {
        $workspace->resources()->delete();
    }

    /**
     * Storing a new workspace.
     */
    public static function store($request)
    {
        $user = Auth::user();

        $workspace = Workspace::create([
            'name' => $request->name,
            'description' => $request->description,
            'user_id' => $user->id,
            'collaborative' => $request->collaborative,
        ]);

        $default_permissions = AppResourcePermission::defaultPermissions();

        $user->giveResourcePermissionsTo($default_permissions, $workspace, true);

        if ($request->has('users')) {
            self::createWorkspaceUsers($workspace, $request->users);
        }

        if ($request->has('resources')) {
            self::createWorkspaceResources($workspace, $request->resources);
        }

        $workspace->load('users', 'resources', 'admin');

        return $workspace;
    }

    /**
     * Updating a workspace.
     */
    public static function update($request, $id, $can_update_users)
    {
        $workspace = Workspace::findOrFail($id);

        DB::transaction(function () use ($workspace, $request, $can_update_users) {
            $workspace->update([
                'name' => $request->name,
                'description' => $request->description,
                'collaborative' => $request->collaborative,
            ]);

            if ($can_update_users) {
                $workspace->users()->detach();
                if ($request->has('users')) {
                    self::createWorkspaceUsers($workspace, $request->users);
                }
            }

            self::deleteAllWorkspaceResources($workspace);
            if ($request->has('resources')) {
                self::createWorkspaceResources($workspace, $request->resources);
            }
        });

        $workspace->load('users', 'resources', 'admin');

        return $workspace;
    }

    /**
     * This method adds the device and all its related entities to the workspace.
     */
    public static function addDeviceToWorkspace($device, $workspace, $permissions)
    {
        $models = array_merge([$device], $device->entities->all());

        foreach ($permissions as $permission) {
            foreach ($models as $model) {
                self::addModelToWorkspace($model, $workspace, $permission);
            }
        }
    }

    public static function removeDeviceFromAllWorkspaces($device)
    {
        $models = array_merge([$device], $device->entities->all());

        foreach ($models as $model) {
            self::removeFromAllWorkspaces($model);
        }
    }

    /**
     * This method adds the probe to the workspace.
     */
    public static function addProbeToWorkspace($probe, $workspace, $permissions)
    {
        foreach ($permissions as $permission) {
            self::addModelToWorkspace($probe, $workspace, $permission);
        }
    }

    public static function removeProbeFromAllWorkspaces($probe)
    {
        self::removeFromAllWorkspaces($probe);
    }

    public static function addModelToWorkspace($model, $workspace, $permission)
    {
        $workspace->resources()->create(
            [
                'resource_id' => $model->id,
                'resource_type' => $model->getTable(),
                'resource_permission_id' => app(ResourcePermissionCache::class)
                    ->getPermissionId($permission),
            ]
        );
    }

    public static function removeFromAllWorkspaces($model)
    {
        ModelHasResourcePermission::where('resource_id', $model->id)
            ->where('resource_type', $model->getTable())
            ->where('model_type', 'workspaces')
            ->delete();
    }

    public static function addModelToWorkspaceWithPermissions($model, $workspace, $permissions)
    {
        foreach ($permissions as $permission) {
            self::addModelToWorkspace($model, $workspace, $permission);
        }
    }
}
