<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class DeviceType extends AuditableModel
{
    protected $table = 'device_types';

    protected $casts = [
        'fiware_properties' => 'array',
    ];

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = ['id', 'name', 'category', 'brand', 'code', 'fiware_properties'];

    // Relations
    public function devices()
    {
        return $this->hasMany(\App\Models\Device::class);
    }
}
