<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class PanelResource extends JsonResource
{
    /**
     * Disable wrapping of the resource.
     *
     * @var bool
     */
    public static $wrap = null;

    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'title' => $this->title,
            'chart' => self::normalizeChart($this->chart),
            'dashboard_id' => $this->dashboard_id,
            'relativeTime' => $this->relative_time,
            'dateRange' => isset($this->date_range) ? $this->date_range : null,
            'series' => isset($this->series) ? SerieResource::collection($this->series) : [],
            'annotations' => $this->annotations,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,
        ];
    }

    /**
     * Force `chart.config.popup.entityDashboards` (the entity -> linked-dashboard map used by
     * Map / Radial Heatmap markers) to be serialized as a JSON object.
     *
     * The chart is cast to an array, so json_decode turns numeric entity-id keys (e.g. "1000")
     * into integer keys. Laravel's JsonResource serialization then runs array_values() on any
     * nested array whose keys are all numeric, collapsing { "1000": 752 } into [ 752 ] and losing
     * the mapping. Casting the node to an object keeps the keys intact regardless of their type
     * (numeric entity id or string urn), so marker links resolve every way they can be authored.
     */
    private static function normalizeChart($chart)
    {
        if (!is_array($chart)) {
            return $chart;
        }

        if (isset($chart['config']['popup']['entityDashboards']) && is_array($chart['config']['popup']['entityDashboards'])) {
            $chart['config']['popup']['entityDashboards'] = (object) $chart['config']['popup']['entityDashboards'];
        }

        // Group charts embed child panels (each with their own chart) under config.panels.
        if (isset($chart['config']['panels']) && is_array($chart['config']['panels'])) {
            $chart['config']['panels'] = array_map(function ($panel) {
                if (is_array($panel) && isset($panel['chart'])) {
                    $panel['chart'] = self::normalizeChart($panel['chart']);
                }

                return $panel;
            }, $chart['config']['panels']);
        }

        return $chart;
    }
}
