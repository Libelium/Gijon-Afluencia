<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class MqttAcl extends AuditableModel
{
    use HasFactory;

    public const READ_ONLY = 1;
    public const WRITE_ONLY = 2;
    public const READ_WRITE = 3;

    protected $table = 'mqtt_acls';

    protected $fillable = [
        'user_id',
        'topic',
        'rw',
    ];

    protected $casts = [
        'user_id' => 'integer',
        'rw' => 'integer',
        'created_at' => 'datetime',
    ];

    // Relationships
    public function user()
    {
        return $this->belongsTo(MqttUser::class, 'user_id');
    }
}
