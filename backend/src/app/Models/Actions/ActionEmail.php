<?php

namespace App\Models\Actions;

use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class ActionEmail extends AuditableModel
{
    protected $table = 'action_email';

    protected $fillable = [
        'destination',
        'subject',
        'content',
    ];

    public function getMorphClass()
    {
        return $this->table;
    }

    public function action()
    {
        return $this->morphMany(Action::class, 'actionable');
    }

    public function setDestinationAttribute(array $value)
    {
        $this->attributes['destination'] = join('#', $value);
    }

    public function getDestinationAttribute($value)
    {
        return explode('#', $value);
    }
}
