<?php

namespace App\Models;

use App\Contracts\Limitable;

class HomeLayout extends AuditableModel implements Limitable
{
    protected $table = 'home_layouts';

    public $timestamps = false;

    protected $fillable = [
        'user_id',
        'name',
        'layout',
        'responsive_layout',
    ];

    protected $casts = [
        'layout' => 'array',
        'responsive_layout' => 'array',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function widgets()
    {
        return $this->hasMany(HomeWidget::class);
    }
}
