<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    // Use device_manager connection
    protected $connection = 'device_manager';

    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('device_certificates', function (Blueprint $table) {
            $table->uuid()->primary();
            $table->string('name');
            $table->string('description')->nullable();
            $table->text('key');
            $table->text('cert');
            $table->integer('user_id');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('device_certificates');
    }
};
