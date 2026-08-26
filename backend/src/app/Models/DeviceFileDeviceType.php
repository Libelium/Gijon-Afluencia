<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DeviceFileDeviceType extends Model
{
    protected $table = 'device_file_device_type';

    protected $fillable = [
        'device_file_id',
        'device_code',
    ];

    /**
     * Get the device file that owns this pivot entry.
     */
    public function deviceFile(): BelongsTo
    {
        return $this->belongsTo(DeviceFile::class, 'device_file_id');
    }
}
