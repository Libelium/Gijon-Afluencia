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
        // delete send_type column 
        Schema::table('custom_datamodels', function (Blueprint $table) {
            $table->dropColumn('send_type');
        });

        //  add, min, max and internal columns 
        Schema::table('custom_datamodels', function (Blueprint $table) {
            $table->integer('min')->nullable();
            $table->integer('max')->nullable();
            $table->boolean('internal')->default(false);
            $table->string('firmware_version')->nullable();
        });

    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('custom_datamodels', function (Blueprint $table) {
            $table->string('send_type')->nullable();
        });

        Schema::table('custom_datamodels', function (Blueprint $table) {
            $table->dropColumn('min');
            $table->dropColumn('max');
            $table->dropColumn('internal');
            $table->dropColumn('firmware_version');
        });
    }
};
