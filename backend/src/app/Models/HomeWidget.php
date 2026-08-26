<?php

namespace App\Models;

class HomeWidget extends AuditableModel
{
    protected $table = 'home_widgets';

    public $timestamps = false;

    protected $fillable = [
        'user_id',
        'home_layout_id',
        'type',
        'config',
    ];

    protected $casts = [
        'config' => 'array',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function homeLayout()
    {
        return $this->belongsTo(HomeLayout::class);
    }
}
