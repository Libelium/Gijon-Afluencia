<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * A mobile push delivery address. One row per app install that opted in.
 *
 * `token` is unique on its own, NOT per user: a handset can change hands and the OS returns the SAME
 * token, so registration must REASSIGN the row rather than insert a second one — otherwise the
 * previous owner keeps receiving notifications on a phone that is no longer theirs.
 *
 * Plain Model rather than AuditableModel on purpose: auditing would copy every raw device token (a
 * delivery credential) and add a row on every app launch.
 */
class PushNotificationToken extends Model
{
    public const PLATFORM_IOS = 'ios';
    public const PLATFORM_ANDROID = 'android';

    protected $table = 'push_notification_tokens';

    protected $fillable = [
        'user_id',
        'platform',
        'token',
        'bundle_id',
        'locale',
        'last_seen_at',
    ];

    protected $casts = [
        'last_seen_at' => 'datetime',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(\App\Models\User::class);
    }
}
