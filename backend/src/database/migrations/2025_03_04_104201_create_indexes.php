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
        // ALARMS
        Schema::table('alarm_has_actions', function (Blueprint $table) {
            $table->index(["alarm_id", "action_id"]);
        });

        Schema::table('alarm_conditions', function (Blueprint $table) {
            $table->index(["alarm_id", "entity_id", "measure"]);
        });

        Schema::table('inactivity_alarm_conditions', function (Blueprint $table) {
            $table->index(["alarm_id", "entity_id", "measure"]);
        });


        // DASHBOARDS
        Schema::table('annotations', function (Blueprint $table) {
            $table->index(['panel_id']);
        });

        Schema::table('calculated_series', function (Blueprint $table) {
            $table->index(['serie_id']);
        });

        Schema::table('measure_series', function (Blueprint $table) {
            $table->index(['serie_id', 'entity_id']);
        });

        Schema::table('multidimensional_series', function (Blueprint $table) {
            $table->index(['serie_id', 'dimension_serie_id']);
        });

        Schema::table('panels', function (Blueprint $table) {
            $table->index(['dashboard_id']);
        });

        Schema::table('series', function (Blueprint $table) {
            $table->index(['panel_id']);
        });

        Schema::table('template_dashboard_entities', function (Blueprint $table) {
            $table->index(['template_dashboard_id', 'entity_id']);
        });

        Schema::table('template_dashboard_groups', function (Blueprint $table) {
            $table->index(['template_dashboard_id', 'group_id']);
        });


        // API KEYS
        Schema::table('api_keys', function (Blueprint $table) {
            $table->index(['user_id', 'key']);
        });


        // OUT CONNECTORS
        Schema::table('out_connectors_has_models', function (Blueprint $table) {
            $table->index(['out_connector_id', 'model_type', 'model_id']);
        });


        // CUSTOM DATAMODELS
        Schema::table('custom_datamodels', function (Blueprint $table) {
            $table->index(['command', 'firmware_version']);
        });

        Schema::table('custom_datamodel_mappings', function (Blueprint $table) {
            $table->index(['custom_datamodel_id']);
        });


        // DEVICES
        Schema::table('device_entity', function (Blueprint $table) {
            $table->index(['device_id', 'entity_id']);
        });

        Schema::table('devices', function (Blueprint $table) {
            $table->index(['serial', 'name']);
        });


        // ENTITIES
        Schema::table('entities', function (Blueprint $table) {
            $table->index(['fiware_scope_id']);
        });


        // ORGANIZATIONS
        Schema::table('organization_has_resource', function (Blueprint $table) {
            $table->index(['organization_id', 'resource_type', 'resource_id']);
        });


        // LOGS
        Schema::table('log_lines', function (Blueprint $table) {
            $table->index(["datetime", "resource_type", "resource_id"]);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // ALARMS
        Schema::table('alarm_has_actions', function (Blueprint $table) {
            $table->dropIndex(['alarm_id', 'action_id']);
        });

        Schema::table('alarm_conditions', function (Blueprint $table) {
            $table->dropIndex(['alarm_id', 'entity_id', 'measure']);
        });

        Schema::table('inactivity_alarm_conditions', function (Blueprint $table) {
            $table->dropIndex(['alarm_id', 'entity_id', 'measure']);
        });

        // DASHBOARDS
        Schema::table('annotations', function (Blueprint $table) {
            $table->dropIndex(['panel_id']);
        });

        Schema::table('calculated_series', function (Blueprint $table) {
            $table->dropIndex(['serie_id']);
        });

        Schema::table('measure_series', function (Blueprint $table) {
            $table->dropIndex(['serie_id', 'entity_id']);
        });

        Schema::table('multidimensional_series', function (Blueprint $table) {
            $table->dropIndex(['serie_id', 'dimension_serie_id']);
        });

        Schema::table('panels', function (Blueprint $table) {
            $table->dropIndex(['dashboard_id']);
        });

        Schema::table('series', function (Blueprint $table) {
            $table->dropIndex(['panel_id']);
        });

        Schema::table('template_dashboard_entities', function (Blueprint $table) {
            $table->dropIndex(['template_dashboard_id', 'entity_id']);
        });

        Schema::table('template_dashboard_groups', function (Blueprint $table) {
            $table->dropIndex(['template_dashboard_id', 'group_id']);
        });

        // API KEYS
        Schema::table('api_keys', function (Blueprint $table) {
            $table->dropIndex(['user_id', 'key']);
        });

        // OUT CONNECTORS
        Schema::table('out_connectors_has_models', function (Blueprint $table) {
            $table->dropIndex(['out_connector_id', 'model_type', 'model_id']);
        });

        // CUSTOM DATAMODELS
        Schema::table('custom_datamodels', function (Blueprint $table) {
            $table->dropIndex(['command', 'firmware_version']);
        });

        Schema::table('custom_datamodel_mappings', function (Blueprint $table) {
            $table->dropIndex(['custom_datamodel_id']);
        });

        // DEVICES
        Schema::table('device_entity', function (Blueprint $table) {
            $table->dropIndex(['device_id', 'entity_id']);
        });

        Schema::table('devices', function (Blueprint $table) {
            $table->dropIndex(['serial', 'name']);
        });

        // ENTITIES
        Schema::table('entities', function (Blueprint $table) {
            $table->dropIndex(['fiware_scope_id']);
        });

        // ORGANIZATIONS
        Schema::table('organization_has_resource', function (Blueprint $table) {
            $table->dropIndex(['organization_id', 'resource_type', 'resource_id']);
        });

        // LOGS
        Schema::table('log_lines', function (Blueprint $table) {
            $table->dropIndex(['datetime', 'resource_type', 'resource_id']);
        });
    }
};
