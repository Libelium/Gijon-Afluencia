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
    // `id` is deliberately NOT fillable: letting a request set the primary key through a
    // mass assignment lets a caller overwrite or impersonate an existing row.
    protected $fillable = ['name', 'category', 'brand', 'code', 'fiware_properties'];

    // Relations
    public function devices()
    {
        return $this->hasMany(\App\Models\Device::class);
    }
}
