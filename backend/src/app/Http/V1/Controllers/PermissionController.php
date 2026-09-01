<?php

namespace App\Http\V1\Controllers;

use Spatie\Permission\Models\Permission;

use Illuminate\Http\Request;
use App\Http\V1\Resources\PermissionResource;
use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use Illuminate\Support\Facades\Auth;
use App\Models\User;
use App\Models\Organization;
use App\Models\FiwareTenant;
use App\Models\FiwareScope;
use App\Repositories\ResourcePermissionRepository;

class PermissionController extends Controller
{
    /**
     * Header the API gateway must send on the `internal/*` endpoints, carrying the shared
     * secret configured as `services.api-gateway.secret` (env API_GATEWAY_SECRET).
     */
    private const GATEWAY_SECRET_HEADER = 'X-Gateway-Secret';

    /**
     * Service-to-service authentication for the `internal/*` endpoints.
     *
     * These routes sit outside `auth:api` on purpose — the API gateway calls them while it is
     * still deciding whether to let a request through — so the shared secret is the only thing
     * separating them from the outside world. Two rules matter here:
     *
     *  - FAIL CLOSED. If no secret is configured the endpoints are unusable (503), never open.
     *    An unconfigured secret is a deployment error, and answering "allowed" to an
     *    unauthenticated caller would turn these endpoints into an authorization oracle.
     *  - Constant-time comparison, so the secret cannot be recovered byte by byte.
     */
    private function assertGatewayAuthenticated(Request $request): void
    {
        $expected = config('services.api-gateway.secret');

        if (!is_string($expected) || $expected === '') {
            abort(503, 'Internal gateway authentication is not configured');
        }

        $provided = $request->header(self::GATEWAY_SECRET_HEADER);

        if (!is_string($provided) || $provided === '' || !hash_equals($expected, $provided)) {
            abort(401, 'Invalid or missing gateway credentials');
        }
    }

    public function index(Request $request)
    {

        $this->authorize('list', Permission::class);

        $prefix = $request->input('prefix', null);

        $hiddenPermissions = AppPermission::hiddenPermissions();

        if ($prefix) {
            $permissions = Permission::where('name', 'like', $prefix . '%')->whereNotIn('name', $hiddenPermissions)->get();
        } else {
            $permissions = Permission::whereNotIn('name', $hiddenPermissions)->get();
        }

        return response(PermissionResource::collection($permissions), 200);
    }

    public function show(int $id)
    {
        $permission = Permission::findOrFail($id);

        $this->authorize('read', $permission);

        if (!$permission) {
            return response('Permission not found', 404);
        }

        return response(new PermissionResource($permission), 200);
    }

    /**
     * Internal endpoint for APISIX to check write permissions
     * Validates if a Keycloak user has UPDATE permission on an organization (tenant)
     *
     * Requires the X-Gateway-Secret header (see assertGatewayAuthenticated): the caller is
     * trusted infrastructure, not an end user, and the body names the user to check.
     *
     * @param Request $request
     * @return \Illuminate\Http\JsonResponse
     */
    public function checkWritePermission(Request $request)
    {
        $this->assertGatewayAuthenticated($request);

        $request->validate([
            'keycloak_user_id' => 'required|string',
            'organization_id' => 'required|integer|exists:organizations,id',
        ]);

        // Find user by Keycloak client ID
        $user = User::where('keycloak_client_id', $request->keycloak_user_id)->first();

        if (!$user) {
            return response()->json([
                'allowed' => false,
                'message' => 'User not found'
            ], 403);
        }

        // Find organization
        $organization = Organization::find($request->organization_id);

        if (!$organization) {
            return response()->json([
                'allowed' => false,
                'message' => 'Organization not found'
            ], 403);
        }

        // Check if user has UPDATE permission on the organization
        $hasPermission = ResourcePermissionRepository::UserHasResourcePermissionTo(
            $user,
            AppResourcePermission::UPDATE,
            $organization
        );

        if ($hasPermission) {
            return response()->json([
                'allowed' => true,
                'user_id' => $user->id,
                'organization_id' => $organization->id,
            ], 200);
        }

        return response()->json([
            'allowed' => false,
            'message' => 'User does not have write permission on this organization'
        ], 403);
    }

    /**
     * Internal endpoint for APISIX to check FIWARE write permissions
     * Validates if a Keycloak user has UPDATE permission on FiwareTenant and optionally FiwareScope
     *
     * Note: Keycloak user ID is extracted from the authenticated JWT token (sub claim)
     *
     * Requires the X-Gateway-Secret header (see assertGatewayAuthenticated) on top of the
     * forwarded JWT.
     *
     * @param Request $request
     * @return \Illuminate\Http\JsonResponse
     */
    public function checkFiwareWritePermission(Request $request)
    {
        $this->assertGatewayAuthenticated($request);

        $request->validate([
            'tenant_name' => 'required|string',
            'scope_name' => 'nullable|string',
        ]);

        // Get Keycloak user ID from authenticated user (JWT token's 'sub' claim)
        $keycloakUserId = Auth::user()->keycloak_client_id ?? Auth::id();

        if (!$keycloakUserId) {
            return response()->json([
                'allowed' => false,
                'message' => 'User not authenticated'
            ], 401);
        }

        // Find user by Keycloak client ID
        $user = User::where('keycloak_client_id', $keycloakUserId)->first();

        if (!$user) {
            return response()->json([
                'allowed' => false,
                'message' => 'User not found'
            ], 403);
        }

        // Find FIWARE tenant by name
        $tenant = FiwareTenant::where('name', $request->tenant_name)->first();

        if (!$tenant) {
            return response()->json([
                'allowed' => false,
                'message' => 'FIWARE tenant not found'
            ], 403);
        }

        // Check if user has UPDATE permission on the tenant
        $hasTenantPermission = ResourcePermissionRepository::UserHasResourcePermissionTo(
            $user,
            AppResourcePermission::UPDATE,
            $tenant
        );

        if (!$hasTenantPermission) {
            return response()->json([
                'allowed' => false,
                'message' => 'User does not have write permission on this FIWARE tenant'
            ], 403);
        }

        // If scope is provided, validate scope permissions
        if ($request->scope_name) {
            $scope = FiwareScope::where('name', $request->scope_name)
                ->where('fiware_tenant_id', $tenant->id)
                ->first();

            if (!$scope) {
                return response()->json([
                    'allowed' => false,
                    'message' => 'FIWARE scope not found for this tenant'
                ], 403);
            }

            // Check if user has UPDATE permission on the scope
            $hasScopePermission = ResourcePermissionRepository::UserHasResourcePermissionTo(
                $user,
                AppResourcePermission::UPDATE,
                $scope
            );

            if (!$hasScopePermission) {
                return response()->json([
                    'allowed' => false,
                    'message' => 'User does not have write permission on this FIWARE scope'
                ], 403);
            }

            return response()->json([
                'allowed' => true,
                'user_id' => $user->id,
                'tenant_id' => $tenant->id,
                'tenant_name' => $tenant->name,
                'scope_id' => $scope->id,
                'scope_name' => $scope->name,
            ], 200);
        }

        // Only tenant validation (for LD endpoints without scope)
        return response()->json([
            'allowed' => true,
            'user_id' => $user->id,
            'tenant_id' => $tenant->id,
            'tenant_name' => $tenant->name,
        ], 200);
    }
}