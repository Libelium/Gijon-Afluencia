<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppResourcePermission;
use App\Models\Dashboard;

use App\Http\V1\Resources\DashboardResource;
use App\Http\V1\Controllers\Controller;
use App\Repositories\DashboardRepository;
use App\Repositories\OrganizationRepository;
use App\Repositories\ResourcePermissionRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Models\User;
use App\DataObjects\EntityQueryFilters;
use App\Repositories\EntityRepository;
use Illuminate\Support\Facades\Log;
use App\Repositories\PreferenceRepository;
use App\Repositories\AnnotationRepository;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Validator;
use App\Services\Dashboards\DashboardContentService;

class DashboardController extends Controller
{
    // Dashboard apiResource
    public function __construct(private readonly DashboardContentService $dashboardContent)
    {
    }

    public function index(Request $request)
    {
        $request->validate([
            'pagination' => 'boolean',
            'page' => 'numeric',
            'perPage' => 'numeric',
            'search' => 'string | nullable',
            'sort' => 'nullable|string|in:dashboards.id,dashboards.name,dashboards.type,dashboards.created_at,dashboards.updated_at,id,name,type,created_at,updated_at',
            'order' => 'nullable|in:asc,desc',
            'filter' => 'string',
            'template_type' => 'array',
            'template_type.*' => 'string',
            'fields' => 'string',
            'hidden' => 'nullable|in:0,1,true,false,all',
        ]);

        $this->authorize('list', Dashboard::class);

        $dashboards = DashboardRepository::paginate($request);

        $result = [
            'count' => $dashboards['count'],
            'rows' => $dashboards['rows'],
            'items' => $dashboards['rows'],
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function indexCustom(Request $request)
    {
        $request->validate([
            'pagination' => 'boolean',
            'page' => 'numeric',
            'perPage' => 'numeric',
            'search' => 'string | nullable',
            'sort' => 'nullable|string|in:dashboards.id,dashboards.name,dashboards.type,dashboards.created_at',
            'order' => 'nullable|in:asc,desc',
            'hidden' => 'nullable|in:0,1,true,false,all',
        ]);

        $this->authorize('list', Dashboard::class);

        $dashboards = DashboardRepository::getCustomDashboards($request);

        $result = [
            'count' => $dashboards['count'],
            'rows' => $dashboards['rows'],
            'items' => $dashboards['rows'],
        ];

        return (new DefaultPaginationResource($result))->response();
    }

    public function store(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255|min:3',
            'description' => 'string|max:255|min:3|nullable',
            'slug' => 'string|max:255|min:3|unique:dashboards|nullable',
            'isPublished' => 'boolean|nullable',
            'type' => 'required|string|max:255|min:3',
            'timezone' => 'required|string|max:255|min:3',
        ]);

        $user = Auth::user();

        $this->authorize('create', Dashboard::class);

        $slug = $this->resolvePublicSlug($request->slug, null);

        $dashboard = Dashboard::create([
            'name' => $request->name,
            'description' => $request->description,
            'slug' => $slug,
            'is_published' => $slug !== null && $request->boolean('isPublished'),
            'type' => $request->type,
            'timezone' => $request->timezone,
            'user_id' => $user->id,
            'layout' => [
                'lg' => [],
                'md' => [],
                'sm' => [],
                'xs' => [],
                'xxs' => [],
            ],
        ]);

        $default_permissions = AppResourcePermission::defaultPermissions();
        $user->giveResourcePermissionsTo($default_permissions, $dashboard, true);

        OrganizationRepository::assignResourceToOrganization($user->organization_id, $dashboard);

        return response()->json($dashboard, 200);
    }

    private function buildDashboardResource(Dashboard $dashboard)
    {
        if ($dashboard->type == 'Template') {
            $template = $dashboard->template()->with('devices.device')->with('entities.entity')->with('regulation')->with('groups.group')->first();
            if ($template) {
                $dashboard->template_type = [
                    'type' => $template->template_type,
                ];

                $autoSelectAll = $template->config['autoSelectAllByDatamodel'] ?? false;
                $autoSelectDatamodels = $template->config['datamodels'] ?? [];

                if ($autoSelectAll && !empty($autoSelectDatamodels)) {
                    $dashboard->entities = EntityRepository::list(
                        Auth::user()->id,
                        'entities.id',
                        'desc',
                        new EntityQueryFilters(types: $autoSelectDatamodels),
                    );
                } else {
                    $dashboard->entities = $template->entities ? $template->entities->pluck('entity') : [];
                }
                $dashboard->devices = $template->devices ? $template->devices->pluck('device') : [];
                $dashboard->regulation = $template->regulation;
                $dashboard->groups = $template->groups ? $template->groups->pluck('group') : [];
                $dashboard->config = $template->config;
            }
        }

        if ($dashboard->type == 'Custom') {
            $dashboard->panels = $dashboard->panels()->with('series.extra_calculated')
                ->with('series.extra_multidimensional')->with('series.extra_measure')->with('annotations')->get();
        }

        return new DashboardResource($dashboard);
    }

    public function show($id)
    {
        $dashboard = Dashboard::findOrFail($id);

        $this->authorize('read', $dashboard);

        if (!$dashboard) {
            return response()->json([
                'message' => 'Dashboard not found',
            ], 404);
        }

        return $this->buildDashboardResource($dashboard)->response()->setStatusCode(200);
    }

    /**
     * Public slug with enough entropy not to be guessable from the name. An already issued slug
     * is kept when the request repeats it (or its suffix-less base) so shared links stay valid.
     */
    private function resolvePublicSlug(?string $requested, ?string $current): ?string
    {
        if ($requested === null || $requested === '') {
            return null;
        }

        $base = Str::substr(Str::slug($requested), 0, 240);

        if ($current !== null && ($current === $requested
            || preg_match('/^' . preg_quote($base, '/') . '-[a-z0-9]{12}$/', $current) === 1)) {
            return $current;
        }

        return $base . '-' . Str::lower(Str::random(12));
    }

    public function getPublicDashboard($slug)
    {
        // 404 and not 403 when it is not published: a 403 would confirm the slug exists.
        $dashboard = Dashboard::publishedBySlug($slug);

        if (!$dashboard) {
            return response()->json([
                'message' => 'Dashboard not found',
            ], 404);
        }

        $userId = $dashboard->user_id;

        $user = User::find($userId);

        if (!$user) {
            return response()->json([
                'message' => 'User not found',
            ], 404);
        }

        // public_view_icon
        $lightIcon = PreferenceRepository::getUserPreference($user, 'themeLightIcon');

        $dashboard->public_view_icon = $lightIcon;

        // public_view_dark_icon
        $darkIcon = PreferenceRepository::getUserPreference($user, 'themeDarkIcon');

        $dashboard->public_view_dark_icon = $darkIcon;

        // Creator's resolved preferences (user -> organization -> default) so the
        // public view can render with the creator's theme, language and skin mode.
        $creatorPreferenceNames = [
            'language',
            'displayskinMode',
            'lightThemePrimaryColor',
            'lightThemeLightPrimaryColor',
            'lightThemeSecondaryColor',
            'darkThemePrimaryColor',
            'darkThemeLightPrimaryColor',
            'darkThemeSecondaryColor',
        ];

        $creatorPreferences = [];
        foreach ($creatorPreferenceNames as $preferenceName) {
            $creatorPreferences[$preferenceName] = PreferenceRepository::getUserPreference($user, $preferenceName);
        }

        $dashboard->creator_preferences = $creatorPreferences;

        return response($this->buildDashboardResource($dashboard), 200);
    }

    public function update(Request $request, $id)
    {
        $request->validate([
            'name' => 'string|max:255|min:3',
            'description' => 'string|max:255|min:3|nullable',
            'slug' => [
                'string',
                'max:255',
                'min:3',
                Rule::unique('dashboards')->ignore($id),
                'nullable'
            ],
            'isPublished' => 'boolean|nullable',
            'type' => 'string|max:255|min:3',
            'timezone' => 'string|max:255|min:3',
            'layout.*' => 'array|nullable',
            'dateRange' => 'array|nullable',
            'viewMode' => 'boolean|nullable',
            'hidden' => 'boolean|nullable',
        ]);

        $dashboard = Dashboard::findOrFail($id);

        $this->authorize('update', $dashboard);

        // Partial update: a request carrying neither slug nor isPublished (the front-end PUT
        // sends only name and description) must not unpublish the dashboard.
        $slug = $request->has('slug')
            ? $this->resolvePublicSlug($request->slug, $dashboard->slug)
            : $dashboard->slug;

        $dashboard->update([
            'name' => $request->name ?? $dashboard->name,
            'description' => $request->description ?? $dashboard->description,
            'slug' => $slug,
            'is_published' => $slug !== null
                && ($request->has('isPublished') ? $request->boolean('isPublished') : $dashboard->is_published),
            'type' => $request->type ?? $dashboard->type,
            'timezone' => $request->timezone ?? $dashboard->timezone,
            'layout' => $request->layout ?? $dashboard->layout,
            'date_range' => $request->dateRange ?? $dashboard->date_range,
            'view_mode' => $request->viewMode ?? $dashboard->view_mode,
            'hidden' => $request->has('hidden') ? (bool) $request->hidden : $dashboard->hidden,
        ]);

        return response()->json($dashboard, 200);
    }

    /**
     * Replace a custom dashboard's panels, series and layout from a single JSON
     * description (the format produced by the front-end generateJSON()).
     *
     * Panels carrying an existing id are updated in place, panels without an id
     * (or with a negative/temporary id) are created, and panels missing from the
     * payload are deleted. Layout item ids referencing temporary panel ids are
     * remapped to the real ids assigned on creation. Everything runs in a single
     * transaction so a validation error leaves the dashboard untouched.
     */
    public function updateFromJson(Request $request, $id)
    {
        $dashboard = Dashboard::findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type !== 'Custom') {
            return response()->json([
                'message' => 'Only custom dashboards can be updated from JSON',
            ], 422);
        }

        $request->validate([
            'name' => 'string|max:255|min:3|nullable',
            'description' => 'string|max:255|nullable',
            'timezone' => 'string|max:255|min:3|nullable',
            'layout' => 'array|nullable',
            'dateRange' => 'array|nullable',
            'hidden' => 'boolean|nullable',
            'panels' => 'present|array',
        ]);

        DB::transaction(function () use ($request, $dashboard) {
            $this->dashboardContent->apply($dashboard, $request->all(), []);
        });

        $dashboard->refresh();

        return $this->buildDashboardResource($dashboard)->response()->setStatusCode(200);
    }

    /**
     * Create one or many custom dashboards from a single JSON document.
     *
     * Accepts either a single dashboard object (same shape as updateFromJson) or
     * `{ "dashboards": [ { "key": "...", ...dashboard }, ... ] }` to create a batch
     * atomically. Inside any chart config, a string value of the form "@<key>" is
     * resolved to the real id of the sibling dashboard created in the same batch whose
     * "key" matches — enabling cross-references (e.g. Map popup.entityDashboards or
     * Link links[].dashboardId) between dashboards that don't exist yet.
     */
    public function createFromJson(Request $request)
    {
        $this->authorize('create', Dashboard::class);

        $specs = $request->has('dashboards') ? $request->input('dashboards') : [$request->all()];

        if (!is_array($specs) || count($specs) === 0) {
            return response()->json(['message' => 'No dashboards to create'], 422);
        }

        foreach ($specs as $spec) {
            Validator::make($spec, [
                'key' => 'nullable',
                'name' => 'required|string|max:255|min:3',
                'description' => 'string|max:255|nullable',
                'timezone' => 'required|string|max:255|min:3',
                'type' => 'nullable|string',
                'hidden' => 'boolean|nullable',
                'layout' => 'array|nullable',
                'dateRange' => 'array|nullable',
                'panels' => 'present|array',
            ])->validate();

            if (isset($spec['type']) && $spec['type'] !== 'Custom') {
                return response()->json([
                    'message' => 'Only custom dashboards can be created from JSON',
                ], 422);
            }
        }

        $user = Auth::user();
        $createdIds = [];

        DB::transaction(function () use ($specs, $user, &$createdIds) {
            $keyToId = [];
            $pairs = [];

            // 1) Create every dashboard shell first so cross-references can resolve.
            foreach ($specs as $spec) {
                $dashboard = Dashboard::create([
                    'name' => $spec['name'],
                    'description' => $spec['description'] ?? null,
                    'type' => 'Custom',
                    'timezone' => $spec['timezone'],
                    'user_id' => $user->id,
                    'layout' => ['lg' => [], 'md' => [], 'sm' => [], 'xs' => [], 'xxs' => []],
                    'hidden' => isset($spec['hidden']) ? (bool) $spec['hidden'] : false,
                ]);

                $user->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $dashboard, true);
                OrganizationRepository::assignResourceToOrganization($user->organization_id, $dashboard);

                if (!empty($spec['key'])) {
                    $keyToId[(string) $spec['key']] = $dashboard->id;
                }
                $pairs[] = [$dashboard, $spec];
            }

            // 2) Apply panels/series/layout, resolving "@key" references to the real ids.
            foreach ($pairs as [$dashboard, $spec]) {
                $this->dashboardContent->apply($dashboard, $spec, $keyToId);
                $createdIds[] = $dashboard->id;
            }
        });

        $created = array_map(function ($id) {
            $d = Dashboard::find($id);

            return ['id' => $d->id, 'name' => $d->name, 'slug' => $d->slug, 'hidden' => (bool) $d->hidden];
        }, $createdIds);

        return response()->json(['data' => $created], 201);
    }


    public function destroy($id)
    {
        $dashboard = Dashboard::findOrFail($id);

        $this->authorize('delete', $dashboard);

        $dashboard->deleteOrFail();

        ResourcePermissionRepository::deleteAllPermissionsForResource($dashboard);
        OrganizationRepository::unassignResourceFromAnyOrganization($dashboard);

        return response()->json(true, 200);
    }

}
