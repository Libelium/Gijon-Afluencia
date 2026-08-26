<?php

namespace App\Models;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;
use App\Models\Reports\ReportCustomBlock;
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
        'preview_image',
        'view_mode',
        'hidden',
    ];

    protected $hidden = [];

    protected $appends = ['previewImage'];

    protected $casts = [
        'layout' => 'array',
        'view_mode' => 'boolean',
        'hidden' => 'boolean',
    ];

    /**
     * Get the preview image in camelCase format.
     */
    public function getPreviewImageAttribute(): ?string
    {
        return $this->attributes['preview_image'] ?? null;
    }

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function panels()
    {
        return $this->hasMany(\App\Models\Panel::class);
    }

    public function tags()
    {
        return $this->belongsToMany(\App\Models\Tag::class, 'dashboard_tag');
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

    public function custom_blocks()
    {
        return $this->morphMany(ReportCustomBlock::class, 'custom_blockable');
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
