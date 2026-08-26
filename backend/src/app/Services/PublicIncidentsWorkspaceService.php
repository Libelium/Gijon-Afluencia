<?php

namespace App\Services;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Authorization\ResourcePermissionCache;
use App\Models\Entity;
use App\Models\Organization;
use App\Models\OrganizationHasResource;
use App\Models\User;
use App\Models\Workspace;
use App\Repositories\OrganizationRepository;
use App\Repositories\WorkspaceRepository;

/**
 * Incident sharing via two workspaces of the configured organization:
 *
 *  - Public workspace  (PUBLIC_INCIDENTS_WORKSPACE): members = all citizens; receives only
 *    PUBLIC incidents (privacy=public) -> every citizen sees them.
 *  - Reviewers workspace (REVIEWERS_INCIDENTS_WORKSPACE): members = org users with the
 *    incidents.review permission; receives EVERY incident (public + private) -> reviewers
 *    see them all.
 *
 * The creator always keeps READ+UPDATE over their own incident (grantCreator), so a private
 * incident is visible to its creator and to reviewers only. Each workspace is opt-in via its
 * env name + SELF_PROVISIONING_ORGANIZATION; unset name = that workspace is off (no-op).
 */
class PublicIncidentsWorkspaceService
{
    /** Non-Incident module datamodels (notices, surveys, services, operator teams) shared READ with the PUBLIC workspace. */
    public const PUBLIC_READONLY_DATAMODELS = [
        'SpecialAnnouncement',
        'SurveyResponse',
        'PointOfInterest',
        'OperatorsTeam',
    ];

    /** Of those, the ones an incidents-admin may edit ('SurveyResponse' is a citizen's answer, not admin-editable). */
    public const ADMIN_EDITABLE_DATAMODELS = [
        'SpecialAnnouncement',
        'PointOfInterest',
        'OperatorsTeam',
    ];

    public static function enabled(): bool
    {
        return !empty(config('incidents.public_workspace')) && self::organizationId() !== null;
    }

    /** Citizen organization id, taken from SELF_PROVISIONING_ORGANIZATION ({"name": id}). */
    public static function organizationId(): ?int
    {
        $org = config('provisioning.self_provisioning_organization', []);
        $id = is_array($org) ? (array_values($org)[0] ?? null) : null;
        return $id !== null ? (int) $id : null;
    }

    private static function ownerId(): ?int
    {
        return Organization::find(self::organizationId())?->admin;
    }

    /**
     * Is this entity inside one of the citizen organization's scopes? Guards the datamodel-driven
     * sharing: `PointOfInterest` is generic, so matching on datamodel alone would share another
     * organization's entity into the citizen workspace.
     */
    private static function belongsToOrgScopes(Entity $entity): bool
    {
        $orgId = self::organizationId();
        if ($orgId === null || $entity->fiware_scope_id === null) {
            return false;
        }

        $scopeIds = collect(OrganizationRepository::getOrganizationScopes($orgId))->pluck('id')->all();

        return in_array((int) $entity->fiware_scope_id, array_map('intval', $scopeIds), true);
    }

    public static function workspace(): ?Workspace
    {
        if (!self::enabled()) {
            return null;
        }
        return Workspace::where('name', config('incidents.public_workspace'))
            ->where('user_id', self::ownerId())
            ->first();
    }

    /**
     * Create the workspace (owned by the org admin), assign it to the organization, and add
     * all of the organization's users. Idempotent — safe to re-run. (Used by the seeder.)
     */
    public static function ensureWorkspace(): ?Workspace
    {
        if (!self::enabled()) {
            return null;
        }
        $orgId = self::organizationId();
        $ownerId = self::ownerId();
        if ($ownerId === null) {
            return null;
        }

        $workspace = Workspace::firstOrCreate(
            ['name' => config('incidents.public_workspace'), 'user_id' => $ownerId],
            ['description' => 'Public citizen incidents', 'collaborative' => false],
        );

        OrganizationHasResource::firstOrCreate([
            'organization_id' => $orgId,
            'resource_id' => $workspace->id,
            'resource_type' => $workspace->getTable(),
        ]);

        // Membership + READ resource permission on the workspace. The workspace listing filters
        // by READ resource permission (model_has_resource_permissions), not by membership alone,
        // so without this the workspace would not be listed/usable for its members.
        $members = User::where('organization_id', $orgId)->get();
        $workspace->users()->syncWithoutDetaching($members->pluck('id')->all());
        foreach ($members as $member) {
            $member->giveResourcePermissionsTo([AppResourcePermission::READ], $workspace);
        }
        // Owner (org admin) can manage it.
        User::find($ownerId)?->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $workspace);

        return $workspace;
    }

    /** Add a (newly self-registered) citizen to the workspace so they see public incidents. */
    public static function addUser(User $user): void
    {
        if (!self::enabled() || (int) $user->organization_id !== self::organizationId()) {
            return;
        }
        $workspace = self::workspace();
        if (!$workspace) {
            return;
        }
        $workspace->users()->syncWithoutDetaching([$user->id]);
        // READ resource permission so the workspace is listed/usable for this member.
        $user->giveResourcePermissionsTo([AppResourcePermission::READ], $workspace);
    }

    /**
    /** Grant the creator READ+UPDATE on their incident — only they can edit it. Always runs. */
    public static function grantCreator(Entity $entity, User $creator): void
    {
        $creator->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $entity);
    }

    /** Share a public incident with the public workspace (READ for every citizen). Idempotent. */
    public static function shareIncident(Entity $entity): void
    {
        self::shareWith($entity, self::workspace());
    }

    /**
     * Reverse of shareIncident(): remove this incident from the PUBLIC workspace ONLY, so a public
     * incident becomes private — gone from every citizen's map/list, still visible to its creator
     * (grantCreator) and to reviewers (reviewers workspace). Used by moderation to take objectionable
     * content out of public view. Deliberately NOT WorkspaceRepository::removeFromAllWorkspaces()
     * (that would also drop the reviewers share). Idempotent and null-safe.
     */
    public static function unshareIncident(Entity $entity): void
    {
        $workspace = self::workspace();
        if (!$workspace) {
            return;
        }
        $workspace->resources()
            ->where('resource_type', $entity->getTable())
            ->where('resource_id', $entity->id)
            ->delete();
    }

    // ---- Reviewers workspace: members = org users with incidents.review; holds ALL incidents ----

    public static function reviewersEnabled(): bool
    {
        return !empty(config('incidents.reviewers_workspace')) && self::organizationId() !== null;
    }

    public static function reviewersWorkspace(): ?Workspace
    {
        if (!self::reviewersEnabled()) {
            return null;
        }
        return Workspace::where('name', config('incidents.reviewers_workspace'))
            ->where('user_id', self::ownerId())
            ->first();
    }

    /** Org users holding the incidents.review permission (directly or via role). */
    public static function reviewerUsers()
    {
        $orgId = self::organizationId();
        if ($orgId === null) {
            return collect();
        }
        return User::permission(AppPermission::INCIDENTS_REVIEW->value)
            ->where('organization_id', $orgId)
            ->get();
    }

    /**
     * Create the reviewers workspace (owned by the org admin), assign it to the organization
     * and add every reviewer as a member (READ). Idempotent — safe to re-run. (Used by the seeder.)
     */
    public static function ensureReviewersWorkspace(): ?Workspace
    {
        if (!self::reviewersEnabled()) {
            return null;
        }
        $orgId = self::organizationId();
        $ownerId = self::ownerId();
        if ($ownerId === null) {
            return null;
        }

        $workspace = Workspace::firstOrCreate(
            ['name' => config('incidents.reviewers_workspace'), 'user_id' => $ownerId],
            ['description' => 'All citizen incidents (for reviewers)', 'collaborative' => false],
        );

        OrganizationHasResource::firstOrCreate([
            'organization_id' => $orgId,
            'resource_id' => $workspace->id,
            'resource_type' => $workspace->getTable(),
        ]);

        foreach (self::reviewerUsers() as $reviewer) {
            $workspace->users()->syncWithoutDetaching([$reviewer->id]);
            $reviewer->giveResourcePermissionsTo([AppResourcePermission::READ], $workspace);
        }
        // Owner (org admin) can manage it.
        User::find($ownerId)?->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $workspace);

        return $workspace;
    }

    /** Add a reviewer to the reviewers workspace. No-op unless they hold incidents.review. */
    public static function addReviewer(User $user): void
    {
        if (!self::reviewersEnabled() || (int) $user->organization_id !== self::organizationId()) {
            return;
        }
        if (!$user->can(AppPermission::INCIDENTS_REVIEW->value)) {
            return;
        }
        $workspace = self::reviewersWorkspace();
        if (!$workspace) {
            return;
        }
        $workspace->users()->syncWithoutDetaching([$user->id]);
        $user->giveResourcePermissionsTo([AppResourcePermission::READ], $workspace);
    }

    /**
     * Share an incident with the reviewers workspace — every incident, any privacy. Reviewers
     * (operators / the municipality) must be able to ACT on incidents (accept, resolve, status
     * transitions), which the entity pipeline treats as an UPDATE — so they get READ + UPDATE
     * (the public citizen workspace stays READ-only). Idempotent.
     */
    public static function shareIncidentToReviewers(Entity $entity): void
    {
        self::shareWith($entity, self::reviewersWorkspace(), [AppResourcePermission::READ, AppResourcePermission::UPDATE]);
    }

    /**
     * Share a non-incident incidents-module entity (PUBLIC_READONLY_DATAMODELS) with the
     * PUBLIC/guest workspace as READ-only, so citizens/guests (incidents.read) can see them —
     * mirroring how public incidents are shared via shareIncident(). Idempotent.
     */
    public static function shareEntityToPublic(Entity $entity): void
    {
        if (!self::belongsToOrgScopes($entity)) {
            return;
        }

        self::shareWith($entity, self::workspace(), [AppResourcePermission::READ]);
    }

    /** Org users holding the incidents.admin permission (directly or via role). */
    public static function adminUsers()
    {
        $orgId = self::organizationId();
        if ($orgId === null) {
            return collect();
        }
        return User::permission(AppPermission::INCIDENTS_ADMIN->value)
            ->where('organization_id', $orgId)
            ->get();
    }

    /**
     * READ+UPDATE for every incidents-admin of the org on an ADMIN_EDITABLE_DATAMODELS entity, so
     * they can edit it without a blanket tenant/scope grant. Per-user and not workspace-held on
     * purpose: the reviewers workspace also holds plain operators, who must not edit these.
     * Idempotent, no-op for other datamodels.
     */
    public static function grantAdminUpdate(Entity $entity): void
    {
        if (!in_array($entity->datamodel, self::ADMIN_EDITABLE_DATAMODELS, true)) {
            return;
        }
        if (!self::belongsToOrgScopes($entity)) {
            return;
        }

        foreach (self::adminUsers() as $admin) {
            $admin->giveResourcePermissionsTo(
                [AppResourcePermission::READ, AppResourcePermission::UPDATE],
                $entity
            );
        }
    }

    /**
     * Add an entity to a workspace with the given resource permissions (default READ), for each
     * permission not already granted on that entity in the workspace. Idempotent per-permission
     * (so an existing READ-only share is upgraded to also carry UPDATE), null-safe.
     */
    private static function shareWith(Entity $entity, ?Workspace $workspace, array $permissions = [AppResourcePermission::READ]): void
    {
        if (!$workspace) {
            return;
        }
        foreach ($permissions as $permission) {
            $permId = app(ResourcePermissionCache::class)->getPermissionId($permission);
            $already = $workspace->resources()
                ->where('resource_type', $entity->getTable())
                ->where('resource_id', $entity->id)
                ->where('resource_permission_id', $permId)
                ->exists();
            if (!$already) {
                WorkspaceRepository::addModelToWorkspace($entity, $workspace, $permission);
            }
        }
    }
}
