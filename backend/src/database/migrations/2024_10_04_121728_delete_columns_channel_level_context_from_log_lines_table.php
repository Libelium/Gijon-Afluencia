<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('log_lines', function (Blueprint $table) {
            $table->dropColumn('channel');
            $table->dropColumn('level');
            $table->dropColumn('context');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('log_lines', function (Blueprint $table) {
            $table->string('channel');
            $table->string('level');
            $table->json('context');
        });
    }
};
