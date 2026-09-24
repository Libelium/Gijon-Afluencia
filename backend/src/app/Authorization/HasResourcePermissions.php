<?php

namespace App\Authorization;

use App\Authorization\AppResourcePermission;
use App\Models\Authorization\ModelHasResourcePermission;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Collection;
use App\Repositories\ResourcePermissionRepository;
use App\Models\User;
use App\Services\OrganizationAccessService;
trait HasResourcePermissions
{

    public function hasResourcePermissionTo(AppResourcePermission $permission, Model $model): bool
    {
        return ResourcePermissionRepository::UserHasResourcePermissionTo($this, $permission, $model);
    }

    public function giveResourcePermissionTo(AppResourcePermission $permission, Model $model, bool $applyToOrgAdmin = false): ModelHasResourcePermission
    {

        if ($applyToOrgAdmin) {
            $admin = $this->organization->load('adminUser')->adminUser;
            if ($admin->id !== $this->id) {
                ResourcePermissionRepository::giveUserResourcePermissionTo($admin, $permission, $model);
            }
        }

        return ResourcePermissionRepository::giveUserResourcePermissionTo($this, $permission, $model);
    }

    public function giveResourcePermissionsTo(array $permissions, Model $model, bool $applyToOrgAdmin = false): array
    {

        if ($applyToOrgAdmin) {
            $admin = $this->organization->load('adminUser')->adminUser;
            if ($admin->id !== $this->id) {
                ResourcePermissionRepository::giveUserResourcePermissionsTo($admin, $permissions, $model);
            }
        }

        $records = ResourcePermissionRepository::giveUserResourcePermissionsTo($this, $permissions, $model);

        // A resource created for the organization (applyToOrgAdmin) also reaches the users with an
        // organization access level; the service ignores the models that are not shared.
        if ($applyToOrgAdmin) {
            app(OrganizationAccessService::class)->shareWithOrganization($model, $this);
        }

        return $records;
    }

    public function revokeResourcePermissionTo(AppResourcePermission $permission, Model $model)
    {
        ResourcePermissionRepository::revokeUserResourcePermissionTo($this, $permission, $model);
    }

    public function revokeResourcePermissionsTo(array $permissions, Model $model)
    {
        return ResourcePermissionRepository::revokeUserResourcePermissionsTo($this, $permissions, $model);
    }

    public function getResourcePermissions(Model $model): Collection
    {
        return ResourcePermissionRepository::getUserResourcePermissions($this, $model);
    }

    public function getResourcePermissionForDevice(Model $model): array
    {
        return ResourcePermissionRepository::getUserResourcePermissionsForDevice($this, $model);
    }
}