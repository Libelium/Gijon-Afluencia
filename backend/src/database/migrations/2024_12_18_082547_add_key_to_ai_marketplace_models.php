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
        Schema::table('ai_marketplace_models', function (Blueprint $table) {
            $table->string('key')->nullable();
            $table->string('input_type')->nullable();
            $table->text('output_types')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('ai_marketplace_models', function (Blueprint $table) {
            $table->dropColumn('key');
            $table->dropColumn('input_type');
            $table->dropColumn('output_types');
        });
    }
};
