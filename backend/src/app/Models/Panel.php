<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Panel extends AuditableModel
{
    protected $table = 'panels';

    protected $fillable = [
        'title',
        'chart',
        'dashboard_id',
        'relative_time',
        'date_range',
    ];

    protected $hidden = [];

    protected $casts = [
        'chart' => 'array',
        'date_range' => 'array',
    ];

    public function dashboard()
    {
        return $this->belongsTo(\App\Models\Dashboard::class);
    }

    public function series()
    {
        return $this->hasMany(\App\Models\Serie::class);
    }

    public function annotations()
    {
        return $this->hasMany(\App\Models\Annotation::class);
    }
}
