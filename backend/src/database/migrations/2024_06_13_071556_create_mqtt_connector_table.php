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
        Schema::create('mqtt_connector', function (Blueprint $table) {
            $table->id();
            $table->string('ipAddress');
            $table->integer('port');
            $table->string('username')->nullable();
            $table->string('password')->nullable();
            $table->string('clientId')->nullable();
            $table->string('sslCert')->nullable();
            $table->boolean('ssl');
            $table->jsonb('topicTemplate');
            $table->jsonb('payload_config');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('mqtt_connector');
    }
};
