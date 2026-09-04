<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppResourcePermission;
use App\Models\Dashboard;

use App\Http\V1\Resources\DashboardResource;
use App\Http\V1\Controllers\Controller;
use App\Models\Entity;
use App\Repositories\DashboardRepository;
use App\Repositories\OrganizationRepository;
use App\Repositories\ResourcePermissionRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use App\Http\V1\Resources\DefaultPaginationResource;
use App\Http\V1\Resources\DeviceFullResource;
use App\Models\Device;
use App\Models\EntityGroup;
use App\Models\User;
use App\Repositories\EntityRepository;
use Illuminate\Support\Facades\Log;
use App\Repositories\PreferenceRepository;
use App\Models\Panel;
use App\Models\Serie;
use App\Repositories\PanelRepository;
use App\Repositories\SerieRepository;
use App\Repositories\AnnotationRepository;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Validator;

class DashboardController extends Controller
{
    // Dashboard apiResource
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
                        types: $autoSelectDatamodels,
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
            $this->applyContentToDashboard($dashboard, $request->all(), []);
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
                $this->applyContentToDashboard($dashboard, $spec, $keyToId);
                $createdIds[] = $dashboard->id;
            }
        });

        $created = array_map(function ($id) {
            $d = Dashboard::find($id);

            return ['id' => $d->id, 'name' => $d->name, 'slug' => $d->slug, 'hidden' => (bool) $d->hidden];
        }, $createdIds);

        return response()->json(['data' => $created], 201);
    }

    /**
     * Reconcile a custom dashboard's panels, series and layout from a plain content array
     * (name/description/timezone/dateRange/hidden/layout/panels), resolving "@key" dashboard
     * references in chart configs against $keyToId. Assumes it runs inside a DB transaction.
     */
    private function applyContentToDashboard(Dashboard $dashboard, array $data, array $keyToId = []): void
    {
        $panelsData = $data['panels'] ?? [];

        $keptIds = [];
        // Maps a client-provided (possibly temporary/string) panel id to the real id
        // assigned on creation, so the grid layout can be rewired to the new panels.
        $idMap = [];
        // Real ids of panels created in this request — the only auto-placement candidates.
        $createdIds = [];
        // Ids embedded as group children: they render inside their parent group, so they
        // must never be auto-placed as top-level grid items.
        $childPanelIds = [];

        foreach ($panelsData as $panelData) {
            $panelData['dashboard_id'] = $dashboard->id;
            $panelData['series'] = $panelData['series'] ?? [];
            $panelData['annotations'] = $panelData['annotations'] ?? [];

            // Resolve "@key" cross-dashboard references inside the chart config.
            if (isset($panelData['chart'])) {
                $panelData['chart'] = self::remapDashboardRefs($panelData['chart'], $keyToId);
            }

            foreach ($panelData['chart']['config']['panels'] ?? [] as $childPanel) {
                if (isset($childPanel['id'])) {
                    $childPanelIds[] = (string) $childPanel['id'];
                }
            }

            $providedId = $panelData['id'] ?? null;

            Validator::make($panelData, [
                'id' => 'nullable',
                'title' => 'nullable|string|max:255',
                'chart' => 'required|array',
                'chart.title' => 'required|string|max:255|min:3',
                'chart.type' => 'required|string|max:255|min:3',
                'series' => 'array',
                'annotations' => 'array',
                'relativeTime' => 'nullable|boolean',
                'dateRange' => 'nullable|array',
            ])->validate();

            $isExisting = is_numeric($providedId) && $providedId > 0
                && Panel::where('id', $providedId)->where('dashboard_id', $dashboard->id)->exists();

            if ($isExisting) {
                // Updating an existing panel: drop serie ids that don't belong to THIS panel,
                // otherwise SerieRepository would update another panel's serie (resolved by
                // global id, unscoped).
                $ownSerieIds = Serie::where('panel_id', $providedId)->pluck('id')->map(fn ($sid) => (string) $sid)->all();
                $panelData['series'] = array_map(function ($serie) use ($ownSerieIds) {
                    if (isset($serie['id']) && !in_array((string) $serie['id'], $ownSerieIds, true))
                        unset($serie['id']);

                    return $serie;
                }, $panelData['series']);
            } else {
                // Creating a new panel: drop ALL serie ids so its series are created fresh.
                $panelData['series'] = array_map([self::class, 'stripSerieIds'], $panelData['series']);
            }

            $panelRequest = new Request();
            $panelRequest->merge($panelData);

            PanelRepository::validatePanel($panelRequest);

            if ($isExisting) {
                $panel = PanelRepository::update($panelRequest, $providedId);
            } else {
                $panel = PanelRepository::store($panelRequest);
                $createdIds[] = (string) $panel->id;
                if (!is_null($providedId) && $providedId !== '') {
                    $idMap[(string) $providedId] = (string) $panel->id;
                }
            }

            $keptIds[] = $panel->id;
        }

        // Delete panels no longer present in the payload (group children stay: they are
        // top-level rows included in the payload, so they remain in $keptIds).
        $dashboard->panels()->whereNotIn('id', $keptIds)->delete();

        // --- Layout reconciliation: rewire created-panel ids, drop dangling items, and
        // auto-place freshly created panels the layout does not position yet.
        $layout = $data['layout'] ?? $dashboard->layout;
        if (!is_array($layout)) {
            $layout = [];
        }

        $keptStr = array_map('strval', $keptIds);
        $childPanelIds = array_map(fn ($cid) => $idMap[$cid] ?? $cid, $childPanelIds);
        $placeable = array_values(array_filter(
            $createdIds,
            fn ($pid) => !in_array($pid, $childPanelIds, true)
        ));

        foreach ($layout as $breakpoint => &$items) {
            if (!is_array($items)) {
                continue;
            }
            $items = array_map(function ($item) use ($idMap) {
                if (isset($item['i']) && isset($idMap[(string) $item['i']])) {
                    $item['i'] = $idMap[(string) $item['i']];
                }
                return $item;
            }, $items);
            $items = array_values(array_filter(
                $items,
                fn ($item) => isset($item['i']) && in_array((string) $item['i'], $keptStr, true)
            ));
        }
        unset($items);

        if (!isset($layout['lg']) || !is_array($layout['lg'])) {
            $layout['lg'] = [];
        }
        foreach (['lg', 'md', 'sm', 'xs', 'xxs'] as $breakpoint) {
            if (!isset($layout[$breakpoint]) || !is_array($layout[$breakpoint])) {
                continue;
            }
            $items = $layout[$breakpoint];
            $present = array_map(fn ($item) => (string) ($item['i'] ?? ''), $items);
            foreach ($placeable as $pid) {
                if (in_array($pid, $present, true)) {
                    continue;
                }
                $maxY = 0;
                foreach ($items as $item) {
                    $bottom = ($item['y'] ?? 0) + ($item['h'] ?? 0);
                    if ($bottom > $maxY) {
                        $maxY = $bottom;
                    }
                }
                $items[] = ['i' => $pid, 'x' => 0, 'y' => $maxY, 'w' => 12, 'h' => 10, 'static' => true];
                $present[] = $pid;
            }
            $layout[$breakpoint] = $items;
        }

        $dashboard->update([
            'name' => $data['name'] ?? $dashboard->name,
            'description' => $data['description'] ?? $dashboard->description,
            'timezone' => $data['timezone'] ?? $dashboard->timezone,
            'layout' => $layout,
            'date_range' => array_key_exists('dateRange', $data) && $data['dateRange'] !== null
                ? json_encode($data['dateRange'])
                : $dashboard->date_range,
            'hidden' => array_key_exists('hidden', $data) ? (bool) $data['hidden'] : $dashboard->hidden,
        ]);
    }

    /**
     * Recursively replace "@key" string values with the real dashboard id from $keyToId.
     * Used to resolve cross-dashboard references (entityDashboards, Link dashboardId, …)
     * inside a chart config when creating a batch of dashboards at once.
     */
    private static function remapDashboardRefs($node, array $keyToId)
    {
        if (is_array($node)) {
            $out = [];
            foreach ($node as $k => $v) {
                $out[$k] = self::remapDashboardRefs($v, $keyToId);
            }

            return $out;
        }

        if (is_string($node) && strlen($node) > 1 && $node[0] === '@') {
            $key = substr($node, 1);
            if (array_key_exists($key, $keyToId)) {
                return $keyToId[$key];
            }
        }

        return $node;
    }

    /**
     * Remove serie ids (recursively for multidimensional dimensions) so the series are
     * created fresh on a newly created panel rather than updating foreign series by id.
     */
    private static function stripSerieIds(array $serie): array
    {
        unset($serie['id']);

        if (isset($serie['dimensions']) && is_array($serie['dimensions'])) {
            $serie['dimensions'] = array_map([self::class, 'stripSerieIds'], $serie['dimensions']);
        }

        return $serie;
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

    public function setTemplateType(Request $request, $id)
    {
        $request->validate([
            'template_type' => 'required|string|max:255|min:3',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if ($dashboard->template) {
            return response()->json([
                'message' => 'Dashboard already has a template',
            ], 400);
        } else {
            $dashboard->template()->create([
                'template_type' => $request->template_type,
            ]);
        }

        return response()->json($dashboard, 200);
    }

    public function setTemplateConfig(Request $request, $id)
    {
        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template()->update([
            'config' => $request->config,
            'template_type' => $dashboard->template->template_type,
        ]);

        return response()->json($dashboard, 200);
    }

    public function setTemplateEntities(Request $request, $id)
    {
        $request->validate([
            'entities' => 'required|array',
            'entities.*' => 'required|numeric',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->entities()->delete();

        foreach ($request->entities as $entity) {

            $this->authorize('read', Entity::find($entity));
            $dashboard->template->entities()->create([
                'entity_id' => $entity,
            ]);
        }
    }

    public function setTemplateDevices(Request $request, $id)
    {
        $request->validate([
            'devices' => 'required|array',
            'devices.*' => 'required|numeric',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->devices()->delete();

        foreach ($request->devices as $device) {

            $this->authorize('read', Device::find($device));
            $dashboard->template->devices()->create([
                'device_id' => $device,
            ]);
        }

        $newDevices = $dashboard->template->devices()->with('device')->get();

        $newDevices = $newDevices->pluck('device');

        return DeviceFullResource::collection($newDevices);
    }

    public function setTemplateGroups(Request $request, $id)
    {
        $request->validate([
            'groups' => 'required|array',
            'groups.*' => 'required|numeric',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->groups()->delete();

        foreach ($request->groups as $group) {

            $this->authorize('read', EntityGroup::find($group));
            $dashboard->template->groups()->create([
                'group_id' => $group,
            ]);
        }
    }

    public function setTemplateRegulation(Request $request, $id)
    {
        if ($request->input('regulation_id') < 0) {
            $request->merge(['regulation_id' => null]);
        }

        $request->validate([
            'regulation_id' => 'nullable|exists:regulations,id',
        ]);

        $dashboard = Dashboard::select('id', 'type')->with('template')->findOrFail($id);

        $this->authorize('update', $dashboard);

        if ($dashboard->type != 'Template') {
            return response()->json([
                'message' => 'Dashboard is not a template',
            ], 400);
        }

        if (!$dashboard->template) {
            return response()->json([
                'message' => 'Dashboard does not have a template',
            ], 400);
        }

        $dashboard->template->regulation_id = $request->regulation_id;
        $dashboard->template->save();

        return response()->json($dashboard, 200);
    }
}
