<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class ApiKey extends AuditableModel
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'key',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
