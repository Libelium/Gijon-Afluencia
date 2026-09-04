<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\Dashboard;
use App\Models\Entity;
use App\Models\FiwareScope;
use Illuminate\Http\Request;
use App\Http\V1\Controllers\Controller;
use App\Models\FiwareTenant;
use Illuminate\Support\Facades\Http;
use App\Repositories\ResourcePermissionRepository;
use Illuminate\Support\Facades\Auth;

class TimeSeriesController extends Controller
{

    public static function authorize_timeseries_request(object $authorizable, array $request_body)
    {
        foreach ($request_body as $sub_request) {
            if (!is_array($sub_request)) {
                response()->json(['error' => 'invalid request body'], 400)->throwResponse();
            }

            $entity_ids = $sub_request['device_ids'] ?? [];
            $options = $sub_request['options'] ?? null;
            if (!is_array($options)) {
                response()->json(['error' => 'options not provided, tenant and scope are needed'], 400)->throwResponse();
            }

            $tenant = $options['tenant'] ?? null;
            $scope = $options['scope'] ?? null;

            if (!$tenant || !$scope) {
                response()->json(['error' => 'tenant and scope are needed'], 400)->throwResponse();
            }

            $scope_model = FiwareScope::join(
                'fiware_tenants',
                function ($join) use ($tenant) {
                    $join->on('fiware_scopes.fiware_tenant_id', '=', 'fiware_tenants.id')
                        ->where('fiware_tenants.name', $tenant);
                }
            )->where('fiware_scopes.name', $scope)->first();

            if (!$scope_model) {
                response()->json(['error' => 'scope not found'], 404)->throwResponse();
            }

            # With no explicit entities the whole scope series is requested, so the
            # permission is required on the scope itself.
            if (!is_array($entity_ids) || $entity_ids === []) {
                $authorizable->authorize('read', $scope_model);
                continue;
            }

            $unauthorized = ResourcePermissionRepository::getUnauthorizedEntityUrns(
                Auth::user(),
                $entity_ids,
                $scope_model->id
            );

            if (!empty($unauthorized)) {
                response()->json([
                    'message' => 'You are not allowed to read entities: ' . implode(', ', $unauthorized)
                ], 403)->throwResponse();
            }
        }
    }

    public static function authorize_timeseries_request_with_model(object $authorizable, array $request_body, $model_type = null, $model_id = null)
    {
        $source_model = null;

        $allowed_urns = [];

        if ($model_type == 'dashboards') {
            $source_model = Dashboard::findOrFail($model_id);

            $authorizable->authorize('read', $source_model);

            $allowed_urns = $source_model->entities_urn();
        } else {
            response()->json(['error' => 'model type not supported'], 400)->throwResponse();
        }

        foreach ($request_body as $sub_request) {
            if (!is_array($sub_request)) {
                response()->json(['error' => 'invalid request body'], 400)->throwResponse();
            }

            $options = $sub_request['options'] ?? null;
            if (!is_array($options)) {
                response()->json(['error' => 'options not provided, tenant and scope are needed'], 400)->throwResponse();
            }

            $tenant = $options['tenant'] ?? null;
            $scope = $options['scope'] ?? null;

            if (!$tenant || !$scope) {
                response()->json(['error' => 'tenant and scope are needed'], 400)->throwResponse();
            }

            $tenant_model = FiwareTenant::where('name', $tenant)->first();

            $scope_model = $tenant_model
                ? FiwareScope::where('fiware_scopes.name', $scope)
                    ->where('fiware_scopes.fiware_tenant_id', $tenant_model->id)
                    ->first()
                : null;

            if (!$scope_model) {
                response()->json(['error' => 'scope not found'], 404)->throwResponse();
            }

            self::assert_entities_allowed($sub_request['device_ids'] ?? null, $allowed_urns);
        }
    }

    # Exact match: a substring match is bypassed with a URN that contains an authorised one.
    # Fails closed on a missing or empty list: aether-link only filters by entity when
    # device_ids has content, so letting it through would return the whole scope series.
    private static function assert_entities_allowed($entity_ids, $allowed_urns): void
    {
        if (!is_array($entity_ids) || $entity_ids === []) {
            response()->json(['error' => 'device_ids required'], 400)->throwResponse();
        }

        $allowed_urns = collect($allowed_urns)->all();

        foreach ($entity_ids as $entity_id) {
            if (!in_array($entity_id, $allowed_urns, true)) {
                response()->json(['message' => 'You are not allowed to read the entity ' . $entity_id], 403)->throwResponse();
            }
        }
    }

    public function authorize_request(Request $request)
    {
        # check if the user has access to all the requested entities
        $request_body = json_decode($request->getContent(), true);

        if (!is_array($request_body)) {
            response()->json(['error' => 'invalid request body'], 400)->throwResponse();
        }

        $headers = $request->headers->all();

        // if X-Permissions-Model-Type and X-Permissions-Model-Id are present
        // then we need to check if the user has access to the model

        if (array_key_exists('x-permissions-model-type', $headers) && array_key_exists('x-permissions-model-id', $headers)) {
            $model_type = $headers['x-permissions-model-type'][0];
            $model_id = $headers['x-permissions-model-id'][0];

            $this->authorize_timeseries_request_with_model($this, $request_body, $model_type, $model_id);
        } else {
            $this->authorize_timeseries_request($this, $request_body);
        }
    }

    # Returns the sanitised body: the tenant and scope sent downstream are rewritten with the
    # dashboard's own scope instead of whatever the client sent.
    public function authorize_request_for_slug(Request $request, string $slug): array
    {

        # 404 and not 403 when the dashboard is missing or unpublished: a 403 confirms the slug.
        $dashboard = Dashboard::publishedBySlug($slug);

        if (!$dashboard) {
            response()->json(['message' => 'Dashboard not found'], 404)->throwResponse();
        }

        $allowed_urns = $dashboard->entities_urn();
        $dashboard_scope_ids = $dashboard->entities_scope_ids();

        # check if the user has access to all the requested entities
        $request_body = json_decode($request->getContent(), true);

        if (!is_array($request_body)) {
            response()->json(['error' => 'invalid request body'], 400)->throwResponse();
        }

        foreach ($request_body as $index => $sub_request) {
            if (!is_array($sub_request)) {
                response()->json(['error' => 'invalid request body'], 400)->throwResponse();
            }

            $entity_ids = $sub_request['device_ids'] ?? null;

            self::assert_entities_allowed($entity_ids, $allowed_urns);

            $scope_model = self::resolve_public_scope($entity_ids, $dashboard_scope_ids);

            $options = is_array($sub_request['options'] ?? null) ? $sub_request['options'] : [];
            $options['tenant'] = $scope_model->tenant->name;
            $options['scope'] = $scope_model->name;

            $request_body[$index]['options'] = $options;
        }

        return $request_body;
    }

    # The tenant and scope decide which schema aether-link queries, so on the public path they
    # are resolved from the dashboard's entities; anything but a single scope is rejected.
    private static function resolve_public_scope(array $entity_ids, $dashboard_scope_ids): FiwareScope
    {
        $scope_ids = Entity::whereIn('urn', $entity_ids)
            ->whereIn('fiware_scope_id', $dashboard_scope_ids)
            ->distinct()
            ->pluck('fiware_scope_id');

        $scope_model = $scope_ids->count() === 1
            ? FiwareScope::with('tenant')->find($scope_ids->first())
            : null;

        if (!$scope_model || !$scope_model->tenant) {
            response()->json(['error' => 'dashboard scope could not be resolved'], 400)->throwResponse();
        }

        return $scope_model;
    }

    public function redirect_to_context_link(Request $request, $any = null, ?string $body = null)
    {
        # now, send the request to the context link
        $context_link_url = config('services.aether-link.time-series');

        $request_url = $context_link_url . $any;

        $body = $body ?? $request->getContent();

        # Aether-link's FastAPI requires an explicit application/json content
        # type to parse the body as a list. Without it newer pydantic versions
        # treat the body as a raw string and reject it with "Input should be a
        # valid list".
        $response = Http::timeout(180)
            ->withHeaders([
                'Content-Type' => 'application/json',
                'Accept'       => 'application/json',
            ])
            ->send(
                $request->method(),
                $request_url,
                [
                    'body' => $body
                ]
            );

        if ($response->status() != 200) {
            return response($response->body(), $response->status());
        }

        # if i dont do this, it returns txt, even though i set the headers
        # to application/json
        $json_body = json_decode($response->body(), true);

        return response($json_body, $response->status());
    }

    public function is_admin()
    {
        return Auth::user()->can(AppPermission::ADMINISTRATION_VISUALIZER_READ->value);
    }


    public function authenticated_timeseries_request(Request $request)
    {
        if (!$this->is_admin()) {
            $this->authorize_request($request);
        }

        return $this->redirect_to_context_link($request, null);
    }

    public function unauthenticated_timeseries_request(Request $request, string $slug)
    {
        $request_body = $this->authorize_request_for_slug($request, $slug);

        return $this->redirect_to_context_link($request, null, json_encode($request_body));
    }
}
