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
        Schema::table('fiware_type_subscriptions', function (Blueprint $table) {
            $table->dropColumn('name');
            $table->dropColumn('libelium_type');
            $table->string('tenant')->default('platform');
            $table->string('scope')->default('/');
            $table->renameColumn('fiware_type', 'datamodel');
            $table->dropUnique(['fiware_type']);
        });


        // rename table fiware_type_subscriptions to datamodel_subscriptions
        Schema::rename('fiware_type_subscriptions', 'datamodel_subscriptions');

        Schema::table('datamodel_subscriptions', function (Blueprint $table) {
            $table->unique(['datamodel', 'tenant', 'scope']);
        });

        Schema::table('preferencables', function (Blueprint $table) {
            $table->dropColumn('entity_type');
            $table->dropColumn('entity_id');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {

        Schema::table('datamodel_subscriptions', function (Blueprint $table) {
            $table->dropUnique(['datamodel', 'tenant', 'scope']);
        });

        Schema::rename('datamodel_subscriptions', 'fiware_type_subscriptions');

        Schema::table('fiware_type_subscriptions', function (Blueprint $table) {
            $table->string('name')->nullable();
            $table->boolean('libelium_type')->default(false);
            $table->dropColumn('tenant');
            $table->dropColumn('scope');
            $table->renameColumn('datamodel', 'fiware_type');
            $table->unique(['fiware_type']);
        });

        Schema::table('preferencables', function (Blueprint $table) {
            $table->string('entity_type')->nullable();
            $table->string('entity_id')->nullable();
        });
    }
};
