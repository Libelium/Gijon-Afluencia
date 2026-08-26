<?php

namespace App\Models\Actions;

use App\Models\AuditableModel;

class ActionEntityCommand extends AuditableModel
{
    protected $table = 'action_entity_command';

    protected $fillable = [
        'commands',
        'meta',
    ];

    protected $casts = [
        'commands' => 'array',
        'meta'     => 'array',
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
