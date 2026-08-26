<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {

        // STEP 1: ENTITIES TABLE
        // update entities table
        Schema::table('entities', function (Blueprint $table) {
            // delete columns
            // we only keep URN
            $table->dropColumn('name');
            $table->dropColumn('description');
            $table->dropColumn('serial');
            $table->dropColumn('entity_type_id');
            $table->dropColumn('subscribed_until');
            $table->dropColumn('product_id');
            $table->dropColumn('autorenewal');
            $table->dropColumn('metadata');
            $table->dropColumn('geolocation');
            $table->dropColumn('timezone');

            // add columns
            $table->string('datamodel')->default('Device');
            $table->string('tenant')->default('platform');
            $table->string('scope')->default('/');
        });

        // STEP 2: DEVICE TYPES TABLE
        // refactor entity_types table
        Schema::rename('entity_types', 'device_types');
        // remove column datamodel
        Schema::table('device_types', function (Blueprint $table) {
            $table->dropColumn('datamodel');
        });

        // STEP 3: DEVICES TABLE
        // create devices table
        Schema::create('devices', function (Blueprint $table) {
            $table->id();
            $table->foreignId('device_type_id')->references('id')->on('device_types')->onDelete('cascade');
            $table->string("serial");
            $table->string("name");
            $table->string("description")->nullable();
            $table->timestamp('subscribed_until')->nullable();
            $table->jsonb('properties')->nullable();
            $table->timestamps();
        });

        // STEP 4: DEVICE ENTITY TABLE
        Schema::create('device_entity', function (Blueprint $table) {
            $table->id();
            $table->foreignId('device_id')->references('id')->on('devices')->onDelete('cascade');
            $table->foreignId('entity_id')->references('id')->on('entities')->onDelete('cascade');
            $table->timestamps();
        });

        // STEP 5: DEVICE USER TABLE
        Schema::dropIfExists('entity_user');
        Schema::create('device_user', function (Blueprint $table) {
            $table->id();
            $table->foreignId('device_id')->references('id')->on('devices')->onDelete('cascade');
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->string('status')->nullable();
            $table->timestamps();
        });

        // STEP 6: User entity permissions
        Schema::create('user_entity_permissions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->string('tenant');
            $table->string('scope');
            $table->string('type');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('user_entity_permissions');

        Schema::dropIfExists('device_entity');

        Schema::table('entities', function (Blueprint $table) {
            // add columns
            $table->string('name')->nullable();
            $table->string('description')->nullable();
            $table->string('serial')->nullable();
            $table->unsignedBigInteger('entity_type_id')->nullable();
            $table->timestamp('subscribed_until')->nullable();
            $table->unsignedBigInteger('product_id')->nullable();
            $table->boolean('autorenewal')->default(false);
            $table->json('metadata')->nullable();
            $table->point('geolocation')->nullable();
            $table->string('timezone')->nullable();

            // delete columns
            $table->dropColumn('datamodel');
            $table->dropColumn('tenant');
            $table->dropColumn('scope');
        });

        Schema::dropIfExists('device_user');
        Schema::create('entity_user', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->foreignId('entity_id')->references('id')->on('entities')->onDelete('cascade');
            $table->string('status')->nullable();
            $table->timestamps();
        });

        Schema::dropIfExists('devices');

        Schema::rename('device_types', 'entity_types');
        Schema::table('entity_types', function (Blueprint $table) {
            $table->string('datamodel')->default('Device');
        });
    }
};
