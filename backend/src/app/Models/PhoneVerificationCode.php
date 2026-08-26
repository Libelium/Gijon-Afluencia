<?php

namespace App\Models;

use App\Models\AuditableModel;
use Carbon\Carbon;

class PhoneVerificationCode extends AuditableModel
{
    protected $table = 'phone_verification_codes';

    protected $fillable = [
        'user_id',
        'phone',
        'code',
        'verified',
        'expires_at',
        'sent_at',
    ];

    protected $casts = [
        'verified'   => 'boolean',
        'expires_at' => 'datetime',
        'sent_at'    => 'datetime',
    ];

    public function isExpired(): bool
    {
        return now()->gt($this->expires_at);
    }

    public function isOnCooldown(): bool
    {
        return now()->lt($this->sent_at->addSeconds(60));
    }

    public function cooldownSecondsRemaining(): int
    {
        $remaining = now()->diffInSeconds($this->sent_at->addSeconds(60), false);
        return max(0, (int) $remaining);
    }
}
