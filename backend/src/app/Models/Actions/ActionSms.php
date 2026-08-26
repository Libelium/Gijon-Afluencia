<?php

namespace App\Models\Actions;

use App\Models\AuditableModel;

class ActionSms extends AuditableModel
{
    protected $table = 'action_sms';

    protected $fillable = [
        'phone',
        'message',
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
