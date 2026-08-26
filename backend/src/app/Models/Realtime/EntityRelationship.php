<?php

namespace App\Models\Realtime;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class EntityRelationship extends Model
{

    use HasFactory;

    // primary keys are serial, variable and probe_serial
    public $incrementing = false;

    public $timestamps = false;

    protected $connection = 'pgsql_realtime';

    protected $fillable = [
        'urn',
        'tenant',
        'scope',
        'entity_id',
        'name',
        'value',
        'timestamp',
        'updated_at',
        'created_at'
    ];
}