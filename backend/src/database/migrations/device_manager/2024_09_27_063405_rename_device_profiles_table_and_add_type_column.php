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
        //Rename device_profiles table to has_profiles
        Schema::rename('device_profiles', 'has_profiles');
        // Add type column to has_profiles table
        Schema::table('has_profiles', function (Blueprint $table) {
            $table->string('type')->nullable();
        });
        // Rename device_serial column to serial
        Schema::table('has_profiles', function (Blueprint $table) {
            $table->renameColumn('device_serial', 'serial');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        //Redo the changes
        Schema::table('has_profiles', function (Blueprint $table) {
            $table->dropColumn('type');
        });
        Schema::table('has_profiles', function (Blueprint $table) {
            $table->renameColumn('serial', 'device_serial');
        });
        Schema::rename('has_profiles', 'device_profiles');
    }
};
