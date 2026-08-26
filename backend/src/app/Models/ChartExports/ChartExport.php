<?php

namespace App\Models\ChartExports;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use App\Models\Actions\Action;
use App\Traits\Searchable;

class ChartExport extends Model implements Limitable
{
    use Searchable;

    protected static array $searchable = ['name', 'description'];

    protected $fillable = [
        'name',
        'description',
        'panel_id',
        'dashboard_id',
        'user_id',
        'format',
        'image_width',
        'image_height',
        'period',
        'date_range',
    ];

    protected $casts = [
        'period' => 'array',
        'date_range' => 'array',
    ];

    public function panel()
    {
        return $this->belongsTo(\App\Models\Panel::class);
    }

    public function dashboard()
    {
        return $this->belongsTo(\App\Models\Dashboard::class);
    }

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function generations()
    {
        return $this->hasMany(ChartExportGeneration::class);
    }

    public function actions()
    {
        return $this->belongsToMany(Action::class, 'chart_export_has_actions')->with('actionable');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
