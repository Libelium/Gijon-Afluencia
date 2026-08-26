<?php

namespace App\Repositories;

use App\Models\Organization;
use App\Models\OrganizationHasResource;
use App\Models\FiwareScope;
use Illuminate\Database\Eloquent\Collection;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Auth;
use App\Authorization\AppResourcePermission;

class OrganizationRepository
{
    public static function assignResourceToOrganization(
        int $organizationId,
        Model $model
    ): OrganizationHasResource {
        return OrganizationHasResource::create([
            'organization_id' => $organizationId,
            'resource_id' => $model->id,
            'resource_type' => $model->getTable(),
        ]);
    }

    public static function unassignResourceFromAnyOrganization(
        Model $model
    ): void {
        OrganizationHasResource::where([
            'resource_id' => $model->id,
            'resource_type' => $model->getTable(),
        ])->delete();
    }

    public static function getResourceOrganization(Model $model): ?Organization
    {
        $ohr = OrganizationHasResource::where([
            'resource_id' => $model->id,
            'resource_type' => $model->getTable(),
        ])->first();

        if (!$ohr) {
            return null;
        }

        return Organization::find($ohr->organization_id);
    }

    public static function getOrganizationScopes(int $organizationId): Collection
    {
        $organization_tenant_scopes = OrganizationHasResource::where(
            'organization_id',
            $organizationId
        )->where(function ($query) {
            $query->where('resource_type', 'fiware_tenants')
                ->orWhere('resource_type', 'fiware_scopes');
        })->get();

        $scope_ids = [];
        $tenant_ids = [];

        foreach ($organization_tenant_scopes as $ots) {
            if ($ots->resource_type === 'fiware_scopes') {
                $scope_ids[] = $ots->resource_id;
            } else {
                $tenant_ids[] = $ots->resource_id;
            }
        }

        return FiwareScope::with(["tenant"])
            ->whereIn('id', $scope_ids)
            ->orWhereIn('fiware_tenant_id', $tenant_ids)
            ->get();
    }

    /**
     * Return paginated results using query and filters
     *
     * @return Illuminate\Support\Collection
     */

    public static function paginate($request)
    {
        $query = Organization::query()
            // search
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'ilike', '%' . $search . '%');
            })
            // sort
            ->when($request->orderBy, function ($query, $orderBy) use ($request) {
                return $query->orderBy($orderBy, $request->orderDirection ? 'asc' : 'desc');
            });

        // pagination
        $organizations = $query->paginate(
            $request->paginationSize,
            ['organizations.*'],
            'page',
            $request->page
        );

        return [
            'rows' => $organizations->items(),
            'count' => $organizations->total(),
        ];
    }


    public static function getOrganizationScope(Organization $org, string $type): FiwareScope
    {
        $scopeId = PreferenceRepository::getOrganizationPreference($org, $type);

        if ($scopeId == null) {
            throw new \Exception("Organization does not have a scope defined for platform data");
        }

        $scope = FiwareScope::with('tenant')->find($scopeId);

        if ($scope == null) {
            throw new \Exception("Scope with id $scopeId not found");
        }

        return $scope;
    }
}
