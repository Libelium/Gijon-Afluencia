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
        Schema::create('mapping_schemas', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->jsonb('map');
            $table->timestamps();
        });

        Schema::create('sentilo_out_connector', function (Blueprint $table) {
            $table->id();
            $table->jsonb('sensor_id_template');
            $table->text('identity_key');
            $table->string('url', 2048);
            $table->timestamps();
        });

        // add unique index to connector_has_models
        Schema::table('out_connectors_has_models', function (Blueprint $table) {
            $table->unique(['out_connector_id', 'model_id', 'model_type'], 'out_connector_model_unique');
            $table->index(['out_connector_id', 'model_type'], 'out_connector_model_index');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('mapping_schemas');
        Schema::dropIfExists('sentilo_out_connector');

        Schema::table('out_connectors_has_models', function (Blueprint $table) {
            $table->dropUnique('out_connector_model_unique');
            $table->dropIndex('out_connector_model_index');
        });
    }
};
