<?php

namespace App\Services\Dashboards;

use App\Models\Dashboard;
use App\Models\Panel;
use App\Models\Serie;
use App\Repositories\PanelRepository;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

/**
 * Applies a JSON content payload to a custom dashboard, in three sequential phases:
 * panels, grid layout and the dashboard's own attributes.
 */
class DashboardContentService
{
    /**
     * Reconcile a custom dashboard's panels, series and layout from a plain content array
     * (name/description/timezone/dateRange/hidden/layout/panels), resolving "@key" dashboard
     * references in chart configs against $keyToId. Assumes it runs inside a DB transaction.
     */
    public function apply(Dashboard $dashboard, array $data, array $keyToId = []): void
    {
        $panels = $this->syncPanels($dashboard, $data['panels'] ?? [], $keyToId);

        $layout = $this->reconcileLayout(
            $dashboard,
            $data['layout'] ?? null,
            $panels['keptIds'],
            $panels['idMap'],
            $panels['createdIds'],
            $panels['childPanelIds'],
        );

        $this->updateAttributes($dashboard, $data, $layout);
    }

    /**
     * Create, update and delete the dashboard's panels to match the payload.
     *
     * @return array{keptIds: int[], idMap: array<string,string>, createdIds: string[], childPanelIds: string[]}
     */
    private function syncPanels(Dashboard $dashboard, array $panelsData, array $keyToId): array
    {
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

        return [
            'keptIds' => $keptIds,
            'idMap' => $idMap,
            'createdIds' => $createdIds,
            'childPanelIds' => $childPanelIds,
        ];
    }

    /**
     * Rewire the grid layout to the panels that now exist: map the ids assigned on
     * creation, drop items whose panel is gone, and place the new ones at the bottom.
     */
    private function reconcileLayout(
        Dashboard $dashboard,
        array|null $requestedLayout,
        array $keptIds,
        array $idMap,
        array $createdIds,
        array $childPanelIds
    ): array {
        // Delete panels no longer present in the payload (group children stay: they are
        // top-level rows included in the payload, so they remain in $keptIds).
        $dashboard->panels()->whereNotIn('id', $keptIds)->delete();

        // --- Layout reconciliation: rewire created-panel ids, drop dangling items, and
        // auto-place freshly created panels the layout does not position yet.
        $layout = $requestedLayout ?? $dashboard->layout;
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

        return $layout;
    }

    /** Apply the dashboard's own attributes, leaving untouched whatever the payload omits. */
    private function updateAttributes(Dashboard $dashboard, array $data, array $layout): void
    {
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
}
