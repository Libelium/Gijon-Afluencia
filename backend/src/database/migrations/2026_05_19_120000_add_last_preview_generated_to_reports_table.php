<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     *
     * Track the moment the on-demand preview PDF was last regenerated.
     * Distinct from `last_generated` (which captures the scheduled periodic
     * cron) — the report editor needs an authoritative "preview is fresh"
     * timestamp to drive the regenerate-and-poll UI without HEAD-probing
     * Storage on every tick.
     */
    public function up(): void
    {
        Schema::table('reports', function (Blueprint $table) {
            $table->timestamp('last_preview_generated_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('reports', function (Blueprint $table) {
            $table->dropColumn('last_preview_generated_at');
        });
    }
};
