<?php

namespace App\Models\Actions;

use App\Models\User;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class ActionPush extends AuditableModel
{
    protected $table = 'action_push';

    protected $fillable = [
        'destination_user_id',
        'title',
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

    public function setContentAttribute(array $value)
    {
        $this->attributes['content'] = json_encode($value);
    }

    public function getContentAttribute($value)
    {
        return json_decode($value, true);
    }

    public function destination()
    {
        return $this->belongsTo(User::class, 'destination_user_id');
    }
}
