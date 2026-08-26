<?php

namespace App\Models\Authorization;

use Illuminate\Database\Eloquent\Model;

class ResourcePermission extends Model
{
    protected $primaryKey = 'id';

    protected $fillable = [
        'name',
    ];
}