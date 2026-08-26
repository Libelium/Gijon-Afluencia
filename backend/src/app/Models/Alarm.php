<?php
namespace App\Models;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use App\Traits\Searchable;

class Alarm extends AuditableModel implements Limitable
{
    use Searchable;

    protected static array $searchable = ['name'];
    protected $fillable = [
        'user_id',
        'name',
        'type',
        'function',
        'up',
        'disabled'
    ];

    public function conditions()
    {
        return $this->hasMany(\App\Models\AlarmCondition::class);
    }

    public function inactivityConditions()
    {
        return $this->hasMany(\App\Models\InactivityAlarmCondition::class);
    }

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function hasActions()
    {
        return $this->hasMany(\App\Models\Actions\AlarmHasAction::class);
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
