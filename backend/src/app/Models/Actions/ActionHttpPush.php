<?php

namespace App\Models\Actions;

use App\Models\User;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class ActionHttpPush extends AuditableModel
{
    protected $table = 'action_http_push';

    protected $fillable = [
        'url_template',
        'method',
        'authorization',
    ];

    protected $casts = [
        'url_template' => 'array'
    ];

    public function getMorphClass()
    {
        return $this->table;
    }

    public function action()
    {
        return $this->morphMany(Action::class, 'actionable');
    }
}
