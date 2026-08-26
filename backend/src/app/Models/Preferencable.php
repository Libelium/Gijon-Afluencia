<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Preferencable extends AuditableModel
{
    protected $table = 'preferencables';

    public $timestamps = true;

    protected $fillable = [
        'id',
        'user_id',
        'preference_id',
        'value',
    ];

    public function preference()
    {
        return $this->belongsTo(\App\Models\Preference::class);
    }
}
