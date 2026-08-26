<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use App\Models\Authorization\ModelHasResourcePermission;

class Organization extends AuditableModel
{
    protected $table = 'organizations';

    public $timestamps = true;

    protected $fillable = [
        'id',
        'name',
        'admin',
        'bp_id',
    ];

    public function adminUser()
    {
        return $this->belongsTo(\App\Models\User::class, 'admin');
    }

    public function users()
    {
        return $this->hasMany(\App\Models\User::class);
    }

    public function preferences()
    {
        return $this->belongsToMany(\App\Models\Preference::class, 'organization_preference')
            ->withPivot('value');
    }

}
