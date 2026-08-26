<?php

namespace App\Models\Actions;

use App\Models\Alarm;
use Illuminate\Database\Eloquent\Model;
use App\Models\AuditableModel;

class AlarmHasAction extends AuditableModel
{

    // This table has no id
    public $incrementing = false;

    protected $fillable = [
        'alarm_id',
        'action_id',
        'type',
    ];

    public function alarm()
    {
        return $this->belongsTo(Alarm::class);
    }

    public function action()
    {
        return $this->belongsTo(Action::class);
    }
}
