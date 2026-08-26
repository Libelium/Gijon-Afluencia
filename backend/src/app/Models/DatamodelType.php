<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class DatamodelType extends AuditableModel
{
    use HasFactory;

    protected $table = 'datamodel_types';

    protected $fillable = [
        'name',
    ];
}
