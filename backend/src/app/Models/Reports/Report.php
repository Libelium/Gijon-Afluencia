<?php

namespace App\Models\Reports;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use App\Models\Actions\Action;
use App\Traits\Searchable;

class Report extends Model implements Limitable
{
    use Searchable;

    protected static array $searchable = ['name', 'description'];

    protected $fillable = [
        'user_id',
        'folder_id',
        'report_doc_config_id',
        'period',
        'name',
        'description',
        'priority',
        'last_generated',
    ];

    protected $casts = [
        'period' => 'array',
        'last_generated' => 'datetime',
        'last_preview_generated_at' => 'datetime',
    ];

    public function config()
    {
      return $this->belongsTo(ReportDocConfig::class, 'report_doc_config_id');
    }

    public function blocks()
    {
        return $this->hasMany(ReportCustomBlock::class);
    }

    public function generations()
    {
        return $this->hasMany(ReportGeneration::class);
    }

    public function latestGeneration()
    {
        return $this->hasOne(ReportGeneration::class)->latestOfMany();
    }

    public function actions()
    {
        return $this->belongsToMany(Action::class, 'report_has_actions')->with('actionable');
    }

    public function folder()
    {
        return $this->belongsTo(\App\Models\Folder::class);
    }

    public function tags()
    {
        return $this->belongsToMany(\App\Models\Tag::class, 'report_tag');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}