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
        Schema::create('mqtt_acls', function (Blueprint $table) {
            $table->id(); 
            $table->foreignId('user_id')
                  ->constrained('mqtt_users')
                  ->onDelete('cascade');
            $table->string('topic', 500);
            $table->unsignedTinyInteger('rw')->default(1); // 1=read, 2=write, 3=read+write
            $table->timestamps(); 
        });

        // Add indexes for performance
        Schema::table('mqtt_acls', function (Blueprint $table) {
            $table->index('user_id', 'idx_mqtt_acls_user_id');
            $table->index('topic', 'idx_mqtt_acls_topic');
        });
    }

    public function down()
    {
        Schema::dropIfExists('mqtt_acls');
    }
};
