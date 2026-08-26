<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;


class EntityHealthcheck extends AuditableModel
{
    use HasFactory;

    protected $table = 'entity_properties';
    protected $connection = 'pgsql_realtime';
    protected $primaryKey = 'urn';
    public $incrementing = false;

    /*
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'urn',
        'device_id',
        'serial',
        'device_type',
        'firmware_version',
        'overall_status',
        'reason',
        'battery_status',
        'signal_status',
        'send_frequency_status',
        'battery_reason',
        'signal_reason',
        'send_frequency_reason',
    ];


    protected $casts = [
        'overall_status' => 'integer',
        'battery_status' => 'integer',
        'signal_status' => 'integer',
        'send_frequency_status' => 'integer',
    ];
}
