<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('action_entity_command', function (Blueprint $table) {
            $table->jsonb('meta')->nullable()->after('commands');
        });
    }

    public function down(): void
    {
        Schema::table('action_entity_command', function (Blueprint $table) {
            $table->dropColumn('meta');
        });
    }
};
