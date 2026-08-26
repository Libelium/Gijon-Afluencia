<?php

namespace App\Models\Actions;

use App\Models\AuditableModel;

class ActionTelegram extends AuditableModel
{
    protected $table = 'action_telegram';

    protected $fillable = [
        'chat_id',
        'message',
    ];

    protected $casts = [
        'chat_id' => 'integer',
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
