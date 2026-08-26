<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;


return new class extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        DB::connection($this->connection)->statement('CREATE EXTENSION IF NOT EXISTS postgis;');

        Schema::create('entities', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('urn');
            $table->string('serial');
            $table->string('description')->nullable();
            $table->foreignId('entity_type_id')->constrained();
            $table->timestamp('subscribed_until')->nullable();
            $table->integer('product_id')->nullable();
            $table->boolean('autorenewal')->default(false);
            $table->jsonb('metadata')->nullable();
            $table->point('geolocation')->nullable();
            $table->string('timezone')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('entities');
    }
};
