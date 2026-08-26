<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up()
    {
        Schema::create('mqtt_users', function (Blueprint $table) {
            $table->id(); 
            $table->string('username', 100);
            $table->text('password_hash'); 
            $table->text('password_encrypted')->nullable(); 
            $table->string('password_salt', 32)->nullable();
            $table->boolean('is_admin')->default(false);
            $table->boolean('is_active')->default(true);
            $table->timestamps(); 
        });

        // Add indexes for performance
        Schema::table('mqtt_users', function (Blueprint $table) {
            $table->index('username', 'idx_mqtt_users_username');
            $table->index('is_active', 'idx_mqtt_users_active');
        });
    }

    public function down()
    {
        Schema::dropIfExists('mqtt_users');
    }
};
