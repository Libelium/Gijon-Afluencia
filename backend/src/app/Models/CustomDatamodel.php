<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CustomDatamodel extends AuditableModel
{

    public static $DIMENSIONLESS_UNIT = 'dimensionless';

    protected $fillable = [
        'resource_type',
        'resource_id',
        'command',
        'name',
        'description',
        'operations',
        'data_types',
        'units',
        'tab',
        'datamodels',
        'min',
        'max',
        'internal',
        'firmware_version',
        'template',
    ];

    public function deviceType()
    {
        return $this->hasOne(DeviceType::class);
    }

    public function customDatamodelMappings()
    {
        return $this->hasMany(CustomDatamodelMapping::class, 'custom_datamodel_id');
    }

    public function resource()
    {
        return $this->morphTo();
    }
}
