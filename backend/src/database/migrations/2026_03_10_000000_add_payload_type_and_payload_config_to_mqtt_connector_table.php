<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('mqtt_connector', function (Blueprint $table) {
            Schema::table('mqtt_connector', function (Blueprint $table) {
                $table->string('payload_type')->default('key_value');
            });

            DB::table('mqtt_connector')->update(['payload_type' => 'legacy']);

            $table->renameColumn('messageTemplate', 'payload_config');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('mqtt_connector', function (Blueprint $table) {
            $table->dropColumn('payload_type');
            $table->renameColumn('payload_config', 'messageTemplate');
        });
    }
};
