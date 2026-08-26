<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CrowdVisitor extends Model
{
    protected $table = 'crowd_visitors';

    protected $fillable = [
        'visitor_id',
        'visitor_type',
        'user_id',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
