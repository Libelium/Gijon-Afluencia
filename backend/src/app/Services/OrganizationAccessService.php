<?php

namespace App\Services;

use App\Authorization\AppResourcePermission;
use App\Models\Alarm;
use App\Models\Authorization\ModelHasResourcePermission;
use App\Models\Dashboard;
use App\Models\FiwareTenant;
use App\Models\Organization;
use App\Models\OrganizationHasResource;
use App\Models\User;
use App\Repositories\ResourcePermissionRepository;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;

/**
 * Organization-wide access of a user: 'read' (consulta) or 'edit' (edicion).
 *
 * The platform authorizes per resource: a user sees an entity when it holds a permission over its
 * FIWARE tenant, and a dashboard or alarm when it holds one over that dashboard or alarm. An access
 * level is therefore two things kept together:
 *
 *  - an application role (org_viewer / org_editor) with the module permissions, and
 *  - resource permissions over the organization's tenants, dashboards and alarms, granted when the
 *    level is set and extended to every dashboard or alarm created afterwards (shareWithOrganization).
 *
 * What the user creates itself is never touched: changing or removing the level only revokes the
 * permissions over the organization's resources that belong to someone else.
 */
class OrganizationAccessService
{
    public const READ = 'read';
    public const EDIT = 'edit';

    public const LEVELS = [self::READ, self::EDIT];

    private const ROLES = [
        self::READ => 'org_viewer',
        self::EDIT => 'org_editor',
    ];

    /** Resources whose visibility follows the access level of the organization users. */
    private const SHARED_MODELS = [Dashboard::class, Alarm::class];

    /** @return AppResourcePermission[] */
    public static function resourcePermissionsFor(?string $level): array
    {
        return match ($level) {
            self::READ => [AppResourcePermission::READ],
            self::EDIT => [AppResourcePermission::READ, AppResourcePermission::UPDATE],
            default => [],
        };
    }

    /**
     * Sets the level of $user, replacing the previous one. Null removes the organization-wide
     * access and leaves only what the user owns.
     */
    public function apply(User $user, ?string $level): void
    {
        if ($level !== null && !in_array($level, self::LEVELS, true)) {
            throw new \InvalidArgumentException("Unknown access level: {$level}");
        }

        $organization = $user->organization;
        if (!$organization) {
            throw new \RuntimeException('The user does not belong to an organization');
        }

        DB::transaction(function () use ($user, $level, $organization) {
            foreach (self::ROLES as $role) {
                if ($user->hasRole($role)) {
                    $user->removeRole($role);
                }
            }
            if ($level !== null) {
                $user->assignRole(self::ROLES[$level]);
            }

            $this->revokeShared($user, $organization);

            $permissions = self::resourcePermissionsFor($level);
            if ($permissions) {
                foreach ($this->sharedResources($organization, $user) as $resource) {
                    ResourcePermissionRepository::giveUserResourcePermissionsTo($user, $permissions, $resource);
                }
            }

            $user->access_level = $level;
            $user->save();
        });
    }

    /**
     * Extends a newly created dashboard, alarm or tenant to the organization users that have an
     * access level. Called from the single place where resources are granted to their creator.
     */
    public function shareWithOrganization(Model $resource, User $owner): void
    {
        if (!$this->isShared($resource) || !$owner->organization_id) {
            return;
        }

        $members = User::where('organization_id', $owner->organization_id)
            ->whereIn('access_level', self::LEVELS)
            ->where('id', '!=', $owner->id)
            ->get();

        foreach ($members as $member) {
            ResourcePermissionRepository::giveUserResourcePermissionsTo(
                $member,
                self::resourcePermissionsFor($member->access_level),
                $resource
            );
        }
    }

    private function isShared(Model $resource): bool
    {
        return $resource instanceof FiwareTenant || in_array($resource::class, self::SHARED_MODELS, true);
    }

    /**
     * The organization's tenants, and the dashboards and alarms of its other users.
     *
     * @return Model[]
     */
    private function sharedResources(Organization $organization, User $user): array
    {
        $tenantIds = OrganizationHasResource::where('organization_id', $organization->id)
            ->where('resource_type', (new FiwareTenant())->getTable())
            ->pluck('resource_id');

        $memberIds = User::where('organization_id', $organization->id)
            ->where('id', '!=', $user->id)
            ->pluck('id');

        return [
            ...FiwareTenant::whereIn('id', $tenantIds)->get()->all(),
            ...Dashboard::whereIn('user_id', $memberIds)->get()->all(),
            ...Alarm::whereIn('user_id', $memberIds)->get()->all(),
        ];
    }

    /** Removes the read/update permissions of $user over the organization's shared resources. */
    private function revokeShared(User $user, Organization $organization): void
    {
        $permissionIds = ResourcePermissionRepository::getPermissionIds(
            [AppResourcePermission::READ, AppResourcePermission::UPDATE]
        )->all();

        foreach ($this->sharedResources($organization, $user) as $resource) {
            ModelHasResourcePermission::where('model_id', $user->id)
                ->where('model_type', $user->getTable())
                ->where('resource_type', $resource->getTable())
                ->where('resource_id', $resource->id)
                ->whereIn('resource_permission_id', $permissionIds)
                ->delete();
        }
    }
}
