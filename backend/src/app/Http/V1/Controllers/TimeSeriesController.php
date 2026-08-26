<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Models\Dashboard;
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
            $entity_ids = $sub_request['device_ids'];
            $options = $sub_request['options'];
            if (!$options) {
                response()->json(['error' => 'options not provided, tenant and scope are needed'], 400);
            }

            $tenant = $options['tenant'];
            $scope = $options['scope'];

            if (!$tenant || !$scope) {
                response()->json(['error' => 'tenant and scope are needed'], 400);
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

            if (count($entity_ids) == 0) {
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
            response()->json(['error' => 'model type not supported'], 400);
        }

        foreach ($request_body as $sub_request) {
            $entity_ids = $sub_request['device_ids'];
            $options = $sub_request['options'];
            if (!$options) {
                response()->json(['error' => 'options not provided, tenant and scope are needed'], 400);
            }

            $tenant = $options['tenant'];
            $scope = $options['scope'];

            if (!$tenant || !$scope) {
                response()->json(['error' => 'tenant and scope are needed'], 400);
            }

            $tenant_model = FiwareTenant::where('name', $tenant)->first();

            $scope_model = FiwareScope::where('fiware_scopes.name', $scope)
                ->where('fiware_scopes.fiware_tenant_id', $tenant_model->id)
                ->first();

            if (!$scope_model) {
                response()->json(['error' => 'scope not found'], 404)->throwResponse();
            }

            foreach ($entity_ids as $entity_id) {
                $allowed = false;

                foreach ($allowed_urns as $urn) {
                    # check if includes
                    if (str_contains($entity_id, $urn)) {
                        $allowed = true;
                        break;
                    }
                }

                if (!$allowed) {
                    response()->json(['message' => 'You are not allowed to read the entity ' . $entity_id], 403)->throwResponse();
                }
            }
        }
    }

    public function authorize_request(Request $request)
    {
        # check if the user has access to all the requested entities
        $request_body = json_decode($request->getContent(), true);

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

    public function authorize_request_for_slug(Request $request, string $slug)
    {

        $dashboard = Dashboard::where('slug', $slug)->first();
        $allowed_urns = $dashboard->entities_urn();

        # check if the user has access to all the requested entities
        $request_body = json_decode($request->getContent(), true);

        foreach ($request_body as $sub_request) {
            $entity_ids = $sub_request['device_ids'];

            foreach ($entity_ids as $entity_id) {
                $allowed = false;

                foreach ($allowed_urns as $urn) {
                    # check if includes
                    if (str_contains($entity_id, $urn)) {
                        $allowed = true;
                        break;
                    }
                }

                if (!$allowed) {
                    response()->json(['message' => 'You are not allowed to read the entity ' . $entity_id], 403)->throwResponse();
                }
            }
        }
    }

    public function redirect_to_context_link(Request $request, $any = null)
    {
        # now, send the request to the context link
        $context_link_url = config('services.aether-link.time-series');

        $request_url = $context_link_url . $any;

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
                    'body' => $request->getContent()
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
        $this->authorize_request_for_slug($request, $slug);

        return $this->redirect_to_context_link($request, null);
    }
}
