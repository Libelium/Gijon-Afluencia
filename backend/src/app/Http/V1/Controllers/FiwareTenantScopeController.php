<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Controllers\Controller;
use App\Models\FiwareTenant;
use App\Models\FiwareScope;
use App\Http\V1\Resources\FiwareTenantResource;
use App\Http\V1\Resources\FiwareScopeResource;
use App\Http\V1\Resources\FiwareServiceResource;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Repositories\FiwareTenantScopeRepository;
use Illuminate\Support\Facades\Auth;
use App\Http\V1\Resources\DefaultArrayResource;

use App\Helpers\AetherLinkHelper;
use App\Models\Organization;
use App\Repositories\OrganizationRepository;
use App\Repositories\PreferenceRepository;
use App\Authorization\AppPermission;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class FiwareTenantScopeController extends Controller
{
    /**
     * Returns the externally-reachable Fiware Manager URL (config `services.data-report.external`,
     * env DATA_REPORT_EXTERNAL). Used by the browser device simulator to reach the command-proxy.
     * Gated by the DATA_SOURCES_READ permission.
     */
    public function getFiwareManagerUrl()
    {
        abort_unless(Auth::user()->can(AppPermission::DATA_SOURCES_READ->value), 403);

        return response()->json(['url' => config('services.data-report.external')]);
    }

    /**
     * Server-side proxy to the Fiware Manager command-proxy (avoids browser CORS for the device
     * simulator). Forwards the measurement body to `{DATA_REPORT}/api/v1/command-proxy/iot/json`
     * with the device id (`i`) and apikey (`k`), and returns any queued commands ({} if none).
     * Gated by the DATA_SOURCES_READ permission.
     */
    public function proxyFiwareManagerCommand(Request $request)
    {
        abort_unless(Auth::user()->can(AppPermission::DATA_SOURCES_READ->value), 403);

        $i = $request->input('i');
        $k = $request->input('k');
        $payload = $request->input('payload', []);

        if (! $i || ! $k) {
            return response()->json(['message' => 'Missing device id (i) or apikey (k)'], 422);
        }

        $url = config('services.data-report.base') . '/api/v1/command-proxy/iot/json'
            . '?i=' . urlencode($i) . '&k=' . urlencode($k) . '&getCmd=1';

        $response = Http::withHeaders(['Content-Type' => 'application/json'])
            ->timeout(30)
            ->post($url, $payload);

        // 204 = no queued commands
        if ($response->status() === 204) {
            return response()->json((object) []);
        }

        return response()->json($response->json() ?? (object) [], $response->status());
    }

    public function getTenants()
    {
        $tenants = FiwareTenantScopeRepository::listReadableTenants(Auth::user()->id);

        $result = [
            'rows' => FiwareTenantResource::collection($tenants),
            'items' => $tenants,
        ];

        return (new DefaultArrayResource($result))->response();
    }

    public function getScopes()
    {
        $scopes = FiwareTenantScopeRepository::listReadableScopes(Auth::user()->id);

        $result = [
            'rows' => FiwareScopeResource::collection($scopes),
            'items' => $scopes,
        ];

        return (new DefaultArrayResource($result))->response();
    }


    public function getTenant(int $id)
    {
        $tenant = FiwareTenant::with('scopes')->findOrFail($id);

        $this->authorize('read', $tenant);

        return (new FiwareTenantResource($tenant))->response();
    }

    public function getTenantScopes(int $id)
    {
        $tenant = FiwareTenant::with('scopes')->findOrFail($id);

        $this->authorize('read', $tenant);

        $result = [
            'rows' => FiwareScopeResource::collection($tenant->scopes),
            'items' => $tenant->scopes,
        ];

        return (new DefaultArrayResource($result))->response();
    }

    public function getTenantScopeServices()
    {
        $user = Auth::user();
        $scopes = FiwareTenantScopeRepository::listReadableScopes($user->id);
        $services = [];
        foreach ($scopes as $scope) {
            $res = AetherLinkHelper::getIotaServices($scope->tenant->name, $scope->name);
            $services = array_merge($services, $res);
        }

        $result = [
            'count' => count($services),
            'rows' => FiwareServiceResource::collection($services),
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function getTenantScopeServicesOrganization(int $organizationId)
    {
        $scopes = OrganizationRepository::getOrganizationScopes($organizationId);

        $services = [];
        foreach ($scopes as $scope) {
            if (!$scope->tenant) {
                continue;
            }

            $res = AetherLinkHelper::getIotaServices($scope->tenant->name, $scope->name);
            if (is_array($res)) {
                $services = array_merge($services, $res);
            }
        }

        $result = [
            'count' => count($services),
            'rows' => FiwareServiceResource::collection($services),
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function getScopeTenant(int $scopeId)
    {
        $scope = FiwareScope::with('tenant')->findOrFail($scopeId);

        $this->authorize('read', $scope);

        return (new FiwareTenantResource($scope->tenant))->response();
    }
}
