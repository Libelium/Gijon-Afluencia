<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AccessAttempt extends AuditableModel
{
    protected $table = 'access_attempts';

    protected $fillable = [
        'email',
        'ip',
        'success'
    ];

    public function setEmailAttribute($value)
    {
        $this->attributes['email'] = strtolower($value);
    }
}
