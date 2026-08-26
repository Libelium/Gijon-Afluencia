<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TemplateDashboardGroups extends AuditableModel
{
    protected $table = 'template_dashboard_groups';

    protected $fillable = [
        'template_dashboard_id',
        'group_id',
    ];

    protected $hidden = [];

    public function template_dashboard()
    {
        return $this->belongsTo(\App\Models\TemplateDashboard::class);
    }

    public function group()
    {
        return $this->belongsTo(\App\Models\EntityGroup::class);
    }
}
