<?php

namespace App\Authorization;

use App\Authorization\AppResourcePermission;
use App\Models\Authorization\ResourcePermission;
use Illuminate\Cache\CacheManager;
use Illuminate\Contracts\Cache\Repository;
use Illuminate\Support\Collection;

class ResourcePermissionCache
{

    protected Repository $cache;

    protected CacheManager $cacheManager;
    protected Collection $resource_permissions;

    public function __construct(CacheManager $cacheManager)
    {
        $this->cacheManager = $cacheManager;
        $this->cache = $this->cacheManager->store();
        $this->loadCachedResourcePermissions();
    }

    protected function loadCachedResourcePermissions(): void
    {
        $this->resource_permissions = $this->cache->remember(
            'resource_permissions',
            \DateInterval::createFromDateString('24 hours'),
            function () {
                return ResourcePermission::all()->keyBy('name');
            }
        );
    }

    public function reset(): void
    {
        $this->cache->forget('resource_permissions');
    }

    public function getPermissionId(AppResourcePermission $permission): int
    {
        $resource_permission = $this->resource_permissions[$permission->value] ?? null;

        if (!$resource_permission) {
            throw new \Exception('Resource permission: ' . $permission->value . ' not found in the resource permissions cache');
        }

        return $resource_permission->id;
    }

    public function getPermissionName(int $permission_id): string
    {
        foreach ($this->resource_permissions as $name => $permission) {
            if ($permission->id === $permission_id) {
                return $name;
            }
        }

        throw new \Exception('Resource permission id: ' . $permission_id . ' not found in the resource permissions cache');
    }
}