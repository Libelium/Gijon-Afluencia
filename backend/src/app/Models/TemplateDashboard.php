<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TemplateDashboard extends AuditableModel
{
    protected $table = 'template_dashboards';

    protected $fillable = [
        'dashboard_id',
        'template_type',
        'template_id',
        'config',
    ];

    protected $casts = [
        'config' => 'array',
    ];

    protected $hidden = [];

    public function dashboard()
    {
        return $this->belongsTo(\App\Models\Dashboard::class);
    }

    public function entities()
    {
        return $this->hasMany(\App\Models\TemplateDashboardEntities::class);
    }

    public function devices()
    {
        return $this->hasMany(\App\Models\TemplateDashboardDevices::class);
    }

    public function groups()
    {
        return $this->hasMany(\App\Models\TemplateDashboardGroups::class);
    }

    public function regulation()
    {
        return $this->belongsTo(\App\Models\Regulation::class);
    }


}
