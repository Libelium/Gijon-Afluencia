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
            $table->string('resource_type')->nullable();
            $table->integer('resource_id')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('log_lines', function (Blueprint $table) {
            $table->dropColumn('resource_type');
            $table->dropColumn('resource_id');
        });
    }
};
