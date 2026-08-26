<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\MorphTo;
use Illuminate\Support\Facades\DB;

class DeviceFile extends AuditableModel
{
    use HasFactory;

    protected $table = 'device_files';

    protected $fillable = [
        'name',
        'description',
        'device_code',
        'fw_version',
        'path',
        'extension',
        'downloadable',
        'resource_type',
        'resource_id',
    ];

    /**
     * Attribute to append when serializing
     */
    protected $appends = ['device_codes'];

    /**
     * Get device codes from pivot table as a HasMany relationship.
     */
    public function deviceTypePivots(): HasMany
    {
        return $this->hasMany(DeviceFileDeviceType::class, 'device_file_id');
    }

    /**
     * Get device codes as array from pivot table.
     */
    public function getDeviceCodesAttribute(): array
    {
        // Use loaded relation if available, otherwise query
        if ($this->relationLoaded('deviceTypePivots')) {
            return $this->deviceTypePivots->pluck('device_code')->toArray();
        }

        return DB::table('device_file_device_type')
            ->where('device_file_id', $this->id)
            ->pluck('device_code')
            ->toArray();
    }

    /**
     * Legacy: Get single device type (for backwards compatibility).
     */
    public function deviceType()
    {
        return $this->belongsTo(DeviceType::class, 'device_code', 'code');
    }

    public function resource(): MorphTo
    {
        return $this->morphTo();
    }

    /**
     * Sync device codes to pivot table.
     */
    public function syncDeviceCodes(array $deviceCodes): void
    {
        // Delete existing entries
        DB::table('device_file_device_type')
            ->where('device_file_id', $this->id)
            ->delete();

        // Insert new entries
        $now = now();
        $inserts = array_map(function ($code) use ($now) {
            return [
                'device_file_id' => $this->id,
                'device_code' => $code,
                'created_at' => $now,
                'updated_at' => $now,
            ];
        }, $deviceCodes);

        if (!empty($inserts)) {
            DB::table('device_file_device_type')->insert($inserts);
        }
    }
}
