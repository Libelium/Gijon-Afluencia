<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Facades\DB;

class TelegramUserChat extends Model
{
    protected $table = 'telegram_user_private_chats';

    protected $fillable = [
        'user_id',
        'chat_id',
        'name',
    ];

    protected $casts = [
        'chat_id' => 'integer',
    ];

    private static function pgKey(): string
    {
        return config('encryption.generic_key');
    }

    public function setNameAttribute(?string $value): void
    {
        if ($value === null) {
            $this->attributes['name'] = null;
            return;
        }

        $result = DB::selectOne(
            "SELECT pgp_sym_encrypt(?, ?) AS enc",
            [$value, self::pgKey()]
        );

        $this->attributes['name'] = $result->enc;
    }

    public function getNameAttribute($value): ?string
    {
        if ($value === null) {
            return null;
        }

        try {
            $result = DB::selectOne(
                "SELECT pgp_sym_decrypt(?, ?) AS dec",
                [$value, self::pgKey()]
            );
            return $result->dec;
        } catch (\Exception) {
            return null;
        }
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
