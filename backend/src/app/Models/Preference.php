<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Preference extends AuditableModel
{
    protected $table = 'preferences';
    protected $fillable = [
        'id',
        'name',
        'default_value'
    ];

    public $timestamps = false;
}
