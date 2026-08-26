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
        Schema::create('loriot_connector', function (Blueprint $table) {
            $table->id();
            $table->boolean('downlink_active')->default(false);
            $table->string('downlink_url')->nullable();
            $table->string('downlink_token')->nullable();
            $table->string('appid')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('loriot_connector');
    }
};
