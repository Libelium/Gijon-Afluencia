<?php

namespace App\Models\Actions;

use App\Models\AuditableModel;

class ActionWhatsapp extends AuditableModel
{
    protected $table = 'action_whatsapp';

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
