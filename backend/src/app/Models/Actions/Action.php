<?php

namespace App\Models\Actions;

use App\Models\User;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class Action extends AuditableModel
{
    protected $fillable = [
        'name',
        'user_id',
        'actionable_id',
        'actionable_type',
    ];

    public function actionable()
    {
        return $this->morphTo();
    }

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function actionEmail()
    {
        return $this->hasOne(ActionEmail::class, 'id', 'actionable_id');
    }

    public function actionEntityCommand()
    {
        return $this->hasOne(ActionEntityCommand::class, 'id', 'actionable_id');
    }

    public function alarmHasAction()
    {
        return $this->hasOne(AlarmHasAction::class);
    }
}
