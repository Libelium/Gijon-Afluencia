<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Mobile push registry: one row per app install that opted in.
 *
 * Deliberately NOT named after `devices` — that family (devices, device_user, device_profiles…) is
 * IoT hardware on the device_manager connection.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('push_notification_tokens', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained('users')->cascadeOnDelete();
            // 'ios' | 'android' — the device OS, which is how the dispatcher picks its adapter.
            $table->string('platform', 16);
            // APNs tokens are 64 hex chars, FCM ones ~160-200, and neither vendor documents a
            // maximum. 2048 stays under Postgres' ~2704-byte btree index limit.
            $table->string('token', 2048)->unique();
            // White-label bundle id. For APNs it IS the `apns-topic`.
            $table->string('bundle_id')->nullable();
            // Per-device hint only; the authoritative language is the account preference.
            $table->string('locale', 16)->nullable();
            $table->timestamp('last_seen_at')->nullable();
            $table->timestamps();

            $table->index(['user_id', 'platform']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('push_notification_tokens');
    }
};
