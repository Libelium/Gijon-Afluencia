<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Regulation extends AuditableModel
{
    protected $table = 'regulations';

    protected $fillable = [
        'user_id',
        'name',
        'datamodel',
        'content',
    ];

    protected $hidden = [

    ];

    protected $casts = [
        'user_id' => 'integer',
        'name' => 'string',
        'datamodel' => 'string',
        'content' => 'array',
    ];

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
