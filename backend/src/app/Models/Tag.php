<?php

namespace App\Models;

class Tag extends AuditableModel
{
    protected $table = 'tags';

    protected $fillable = [
        'name',
        'color',
        'organization_id',
    ];

    public function organization()
    {
        return $this->belongsTo(Organization::class);
    }

    public function dashboards()
    {
        return $this->belongsToMany(Dashboard::class, 'dashboard_tag');
    }
}
