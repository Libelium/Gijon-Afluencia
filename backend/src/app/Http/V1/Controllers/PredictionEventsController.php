<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\User;
use App\Services\PredictionEventsRegistry;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

/**
 * The events registry of the predictions component, per tenant and scope: the days the occupancy
 * model must not learn from. Listing needs `prediction_events.read` and read access to the tenant
 * (or the scope); changing it, `prediction_events.update` and update access.
 *
 * The tenant and scope are those of the predictions deployment, the ones its prediction
 * entities are published in.
 */
class PredictionEventsController extends Controller
{
    public function __construct(private PredictionEventsRegistry $registry)
    {
    }

    public function index(Request $request): JsonResponse
    {
        $request->validate(self::TARGET_RULES);
        [$tenant, $scope] = $this->authorizeTarget($request, AppPermission::PREDICTION_EVENTS_READ, AppResourcePermission::READ);

        return response()->json([
            'rows' => $this->registry->events($tenant->name, $scope->name),
            'canEdit' => $this->allowed(Auth::user(), AppPermission::PREDICTION_EVENTS_UPDATE, AppResourcePermission::UPDATE, $tenant, $scope),
        ]);
    }

    public function store(Request $request): JsonResponse
    {
        $event = $request->validate(self::TARGET_RULES + [
            'date' => 'required|date_format:Y-m-d',
            'end_date' => 'nullable|date_format:Y-m-d|after_or_equal:date',
            'event_type' => 'required|string|max:60',
            'device_ids' => 'nullable|array|max:50',
            'device_ids.*' => 'string|max:255|starts_with:urn:ngsi-ld:|not_regex:/,/',
            'notes' => 'nullable|string|max:500',
            'start_hour' => 'nullable|integer|between:0,23|required_with:end_hour',
            'end_hour' => 'nullable|integer|between:1,24|required_with:start_hour|gt:start_hour',
        ]);
        [$tenant, $scope] = $this->authorizeTarget($request, AppPermission::PREDICTION_EVENTS_UPDATE, AppResourcePermission::UPDATE);

        return response()->json($this->registry->append($tenant->name, $scope->name, $event), 201);
    }

    public function destroy(Request $request, string $id): JsonResponse
    {
        $request->validate(self::TARGET_RULES);
        [$tenant, $scope] = $this->authorizeTarget($request, AppPermission::PREDICTION_EVENTS_UPDATE, AppResourcePermission::UPDATE);

        if (!$this->registry->delete($tenant->name, $scope->name, $id)) {
            return response()->json(['message' => 'The event is no longer in the registry as it was listed. Reload it.'], 409);
        }

        return response()->json(null, 204);
    }

    private const TARGET_RULES = [
        'tenant' => 'required|string|max:255',
        'scope' => 'required|string|max:255',
    ];

    /** @return array{0: FiwareTenant, 1: FiwareScope} */
    private function authorizeTarget(Request $request, AppPermission $permission, AppResourcePermission $access): array
    {
        $user = Auth::user();
        abort_unless($user->can($permission->value), 403);

        $tenant = FiwareTenant::where('name', $request->input('tenant'))->first();
        $scope = $tenant?->scopes()->where('name', $request->input('scope'))->first();
        abort_unless($tenant && $scope, 404, 'Unknown tenant or scope');
        abort_unless($this->allowed($user, $permission, $access, $tenant, $scope), 403);

        return [$tenant, $scope];
    }

    /** Access to the tenant covers its scopes, as in the entity listings. */
    private function allowed(User $user, AppPermission $permission, AppResourcePermission $access, FiwareTenant $tenant, FiwareScope $scope): bool
    {
        return $user->can($permission->value)
            && ($user->hasResourcePermissionTo($access, $tenant) || $user->hasResourcePermissionTo($access, $scope));
    }
}
