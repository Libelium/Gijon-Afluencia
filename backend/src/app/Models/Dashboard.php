<?php

namespace App\Models;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;
use App\Traits\Searchable;

class Dashboard extends AuditableModel implements Limitable
{
    use Searchable;

    protected $table = 'dashboards';

    protected static array $searchable = ['name', 'description'];

    protected $fillable = [
        'name',
        'description',
        'slug',
        'type',
        'timezone',
        'user_id',
        'layout',
        'date_range',
        'view_mode',
        'hidden',
        'is_published',
    ];

    protected $hidden = [];

    protected $casts = [
        'layout' => 'array',
        'view_mode' => 'boolean',
        'hidden' => 'boolean',
        'is_published' => 'boolean',
    ];

    // Public access requires the explicit published flag; having a slug is not enough.
    public static function publishedBySlug(string $slug): ?self
    {
        return static::where('slug', $slug)->where('is_published', true)->first();
    }

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function panels()
    {
        return $this->hasMany(\App\Models\Panel::class);
    }

    public function template()
    {
        return $this->hasOne(\App\Models\TemplateDashboard::class);
    }

    public function entities_urn()
    {
        $measure_series_ids = DB::table('dashboards as d')
            ->join('panels as p', 'p.dashboard_id', '=', 'd.id')
            ->join('series as s', 's.panel_id', '=', 'p.id')
            ->join('measure_series as ms', 'ms.serie_id', '=', 's.id')
            ->join('entities as e', 'ms.entity_id', '=', 'e.id')
            ->where('d.id', $this->id)
            ->where('s.type', 'Measure')
            ->select('e.urn')
            ->distinct()
            ->get();

        $measure_series_ids = $measure_series_ids->map(function ($item) {
            return $item->urn;
        });

        $template_ids = DB::table('dashboards as d')
            ->join('template_dashboards as t', 't.dashboard_id', '=', 'd.id')
            ->join('template_dashboard_entities as tde', 'tde.template_dashboard_id', '=', 't.id')
            ->join('entities as e', 'e.id', '=', 'tde.entity_id')
            ->where('d.id', $this->id)
            ->select('e.urn')
            ->distinct()
            ->get();

        $template_entity_group_ids = DB::table('dashboards as d')
            ->join('template_dashboards as t', 't.dashboard_id', '=', 'd.id')
            ->join('template_dashboard_groups as tdg', 'tdg.template_dashboard_id', '=', 't.id')
            ->join('entity_entity_group as eeg', 'eeg.entity_group_id', '=', 'tdg.id')
            ->join('entities as e', 'e.id', '=', 'eeg.entity_id')
            ->where('d.id', $this->id)
            ->select('e.urn')
            ->distinct()
            ->get();

        $template_ids = $template_ids->map(function ($item) {
            return $item->urn;
        });

        $template_entity_group_ids = $template_entity_group_ids->map(function ($item) {
            return $item->urn;
        });

        $result = $measure_series_ids->merge($template_ids);

        $result = $result->merge($template_entity_group_ids);

        return $result;
    }

    // Real FIWARE scope of the dashboard's entities: the public path derives the tenant and
    // scope queried downstream from here instead of trusting the client's.
    public function entities_scope_ids(): \Illuminate\Support\Collection
    {
        $from_series = DB::table('dashboards as d')
            ->join('panels as p', 'p.dashboard_id', '=', 'd.id')
            ->join('series as s', 's.panel_id', '=', 'p.id')
            ->join('measure_series as ms', 'ms.serie_id', '=', 's.id')
            ->join('entities as e', 'ms.entity_id', '=', 'e.id')
            ->where('d.id', $this->id)
            ->where('s.type', 'Measure')
            ->select('e.fiware_scope_id');

        $from_template_entities = DB::table('dashboards as d')
            ->join('template_dashboards as t', 't.dashboard_id', '=', 'd.id')
            ->join('template_dashboard_entities as tde', 'tde.template_dashboard_id', '=', 't.id')
            ->join('entities as e', 'e.id', '=', 'tde.entity_id')
            ->where('d.id', $this->id)
            ->select('e.fiware_scope_id');

        $from_template_groups = DB::table('dashboards as d')
            ->join('template_dashboards as t', 't.dashboard_id', '=', 'd.id')
            ->join('template_dashboard_groups as tdg', 'tdg.template_dashboard_id', '=', 't.id')
            ->join('entity_entity_group as eeg', 'eeg.entity_group_id', '=', 'tdg.id')
            ->join('entities as e', 'e.id', '=', 'eeg.entity_id')
            ->where('d.id', $this->id)
            ->select('e.fiware_scope_id');

        return $from_series
            ->union($from_template_entities)
            ->union($from_template_groups)
            ->pluck('fiware_scope_id')
            ->filter()
            ->unique()
            ->values();
    }

    public function entities_id()
    {
        $measure_series_ids = DB::table('dashboards as d')
            ->join('panels as p', 'p.dashboard_id', '=', 'd.id')
            ->join('series as s', 's.panel_id', '=', 'p.id')
            ->join('measure_series as ms', 'ms.serie_id', '=', 's.id')
            ->join('entities as e', 'ms.entity_id', '=', 'e.id')
            ->where('d.id', $this->id)
            ->where('s.type', 'Measure')
            ->select('e.id')
            ->distinct()
            ->get();

        $measure_series_ids = $measure_series_ids->map(function ($item) {
            return $item->id;
        });

        $template_ids = DB::table('dashboards as d')
            ->join('template_dashboards as t', 't.dashboard_id', '=', 'd.id')
            ->join('template_dashboard_entities as tde', 'tde.template_dashboard_id', '=', 't.id')
            ->join('entities as e', 'e.id', '=', 'tde.entity_id')
            ->where('d.id', $this->id)
            ->select('e.id')
            ->distinct()
            ->get();

        $template_entity_group_ids = DB::table('dashboards as d')
            ->join('template_dashboards as t', 't.dashboard_id', '=', 'd.id')
            ->join('template_dashboard_groups as tdg', 'tdg.template_dashboard_id', '=', 't.id')
            ->join('entity_entity_group as eeg', 'eeg.entity_group_id', '=', 'tdg.id')
            ->join('entities as e', 'e.id', '=', 'eeg.entity_id')
            ->where('d.id', $this->id)
            ->select('e.id')
            ->distinct()
            ->get();

        $template_ids = $template_ids->map(function ($item) {
            return $item->id;
        });

        $template_entity_group_ids = $template_entity_group_ids->map(function ($item) {
            return $item->id;
        });

        $result = $measure_series_ids->merge($template_ids);

        $result = $result->merge($template_entity_group_ids);

        return $result;
    }

    public function getMorphClass()
    {
        return $this->table;
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
