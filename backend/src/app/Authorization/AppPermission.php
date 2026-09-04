<?php

namespace App\Authorization;

/**
 * Class AppPermission, this class contains the
 * application action permissions.
 * WARNING: be careful, all this values must be stored in the database too,
 * for that you have the seeder PermissionsSyncSeeder.php, which will read this enum
 * @package App\Models\Authorization
 */
enum AppPermission: string
{
    // ----------------
    // ROLES
    case ROLES_READ = 'roles.read';
    case ROLES_UPDATE = 'roles.update';

        // ----------------
        // ORGANIZATIONS
    case ORGANIZATIONS_READ = 'organizations.read';
    case ORGANIZATIONS_UPDATE = 'organizations.update';

        // ----------------
        // DATA SOURCES
    case DATA_SOURCES_READ = 'data_sources.read';
        //     DATA SOURCES - DEVICES
        //     DATA SOURCES - ENTITIES
    case DATA_SOURCES_ENTITIES_UPDATE = 'data_sources.entities.update';
    case DATA_SOURCES_ENTITIES_UPLOAD_DATA = 'data_sources.entities.upload_data';
    case DATA_SOURCES_ENTITIES_DECRYPT_READ = 'data_sources.entities.decrypt.read';

        // ----------------
        // ANALYTICS MODULE
    case ANALYTICS_READ = 'analytics.read';

        //      DASHBOARDS
    case DASHBOARDS_READ = 'dashboards.read';
    case DASHBOARDS_UPDATE = 'dashboards.update';

        //          DASHBOARD CUSTOM
    case DASHBOARDS_CUSTOM_READ = 'dashboards.custom.read';
        //          DASHBOARD CHARTS
    case DASHBOARDS_ECHARTS_LINE_READ = 'dashboards.echarts_line.read';
    case DASHBOARDS_ECHARTS_LINE_POINTS_READ = 'dashboards.echarts_line_points.read';
    case DASHBOARDS_ECHARTS_STACKED_AREA_READ = 'dashboards.echarts_stacked_area.read';
    case DASHBOARDS_ECHARTS_BAR_READ = 'dashboards.echarts_bar.read';
    case DASHBOARDS_ECHARTS_BAR_STACKED_READ = 'dashboards.echarts_bar_stacked.read';
    case DASHBOARDS_ECHARTS_BAR_RACE_READ = 'dashboards.echarts_bar_race.read';
    case DASHBOARDS_ECHARTS_BATTERY_READ = 'dashboards.echarts_battery.read';
    case DASHBOARDS_ECHARTS_BOXPLOT_READ = 'dashboards.echarts_boxplot.read';
    case DASHBOARDS_ECHARTS_GAUGE_READ = 'dashboards.echarts_gauge.read';
    case DASHBOARDS_ECHARTS_LABELED_GAUGE_READ = 'dashboards.echarts_labeled_gauge.read';
    case DASHBOARDS_ECHARTS_SCATTER_2D_READ = 'dashboards.echarts_scatter_2d.read';
    case DASHBOARDS_ECHARTS_SCATTER_3D_READ = 'dashboards.echarts_scatter_3d.read';
    case DASHBOARDS_ECHARTS_HEATMAP_CALENDAR_READ = 'dashboards.echarts_heatmap_calendar.read';
    case DASHBOARDS_ECHARTS_SCATTER_CALENDAR_READ = 'dashboards.echarts_scatter_calendar.read';
    case DASHBOARDS_ECHARTS_HEATMAP_GRAPH_READ = 'dashboards.echarts_heatmap_graph.read';
    case DASHBOARDS_ECHARTS_MONTHLY_HEATMAP_GRAPH_READ = 'dashboards.echarts_monthly_heatmap_graph.read';
    case DASHBOARDS_ECHARTS_SCATTER_HISTOGRAM_READ = 'dashboards.echarts_scatter_histogram.read';
    case DASHBOARDS_ECHARTS_CANDLESTICK_READ = 'dashboards.echarts_candlestick.read';
    case DASHBOARDS_ECHARTS_CATEGORY_BAR_READ = 'dashboards.echarts_category_bar.read';
    case DASHBOARDS_ECHARTS_VERTICAL_CATEGORY_BAR_READ = 'dashboards.echarts_vertical_category_bar.read';
    case DASHBOARDS_ECHARTS_HISTOGRAM_READ = 'dashboards.echarts_histogram.read';
    case DASHBOARDS_ECHARTS_PIE_READ = 'dashboards.echarts_pie.read';
    case DASHBOARDS_ECHARTS_DONUT_READ = 'dashboards.echarts_donut.read';
    case DASHBOARDS_ECHARTS_STEP_LINE_READ = 'dashboards.echarts_step_line.read';
    case DASHBOARDS_ECHARTS_WIND_ROSE_READ = 'dashboards.echarts_wind_rose.read';
    case DASHBOARDS_ECHARTS_RADAR_READ = 'dashboards.echarts_radar.read';
    case DASHBOARDS_CUSTOM_TILE_READ = 'dashboards.custom_tile.read';
    case DASHBOARDS_CUSTOM_ICON_TILE_READ = 'dashboards.custom_icon_tile.read';
    case DASHBOARDS_CUSTOM_ICON_READ = 'dashboards.custom_icon.read';
    case DASHBOARDS_CUSTOM_TEXT_TILE_READ = 'dashboards.custom_text_tile.read';
    case DASHBOARDS_CUSTOM_TABLE_READ = 'dashboards.custom_table.read';
    case DASHBOARDS_CUSTOM_MAP_READ = 'dashboards.custom_map.read';
    case DASHBOARDS_CUSTOM_HEATMAP_READ = 'dashboards.custom_heatmap.read';
    case DASHBOARDS_CUSTOM_RADIAL_HEATMAP_READ = 'dashboards.custom_radial_heatmap.read';
    case DASHBOARDS_CUSTOM_PLAN_READ = 'dashboards.custom_plan.read';
    case DASHBOARDS_CUSTOM_TEXT_READ = 'dashboards.custom_text.read';
    case DASHBOARDS_CUSTOM_DTI_TABLE_READ = 'dashboards.custom_dti_table.read';
    case DASHBOARDS_CUSTOM_OGC_WMS_READ = 'dashboards.custom_ogc_wms.read';
    case DASHBOARDS_ECHARTS_PIE_ROSE_READ = 'dashboards.echarts_pie_rose.read';
    case DASHBOARDS_CUSTOM_SELECTOR_READ = 'dashboards.custom_selector.read';
    case DASHBOARDS_CUSTOM_GROUP_READ = 'dashboards.custom_group.read';
    case DASHBOARDS_CUSTOM_CESIUM_VIEWER_READ = 'dashboards.custom_cesium_viewer.read';

        //          DASHBOARD TEMPLATES
    case DASHBOARDS_TEMPLATES_READ = 'dashboards.template.read';
        //          DASHBOARD TEMPLATES - CROWD MONITORING
    case DASHBOARDS_TEMPLATES_CM_READ = 'dashboards.templates_cm.read';
    case DASHBOARDS_TEMPLATES_CM_SIMPLE_READ = 'dashboards.templates_cm_simple.read';

        //      CHART EXPORTS

        // ----------------
        // ALARMS
    case ALARMS_READ = 'alarms.read';
    case ALARMS_UPDATE = 'alarms.update';

        // ----------------
        // OUT CONNECTORS
    case OUT_CONNECTORS_READ = 'out_connectors.read';
    case OUT_CONNECTORS_UPDATE = 'out_connectors.update';

        // ----------------
        // IN CONNECTORS
    case IN_CONNECTORS_READ = 'in_connectors.read';
    case IN_CONNECTORS_UPDATE = 'in_connectors.update';

        // ----------------
        // ADMINISTRATION
    case ADMINISTRATION_READ = 'administration.read';
    case ADMINISTRATION_MOSQUITTO_USERS_READ = 'administration.mosquitto_users.read';
    case ADMINISTRATION_IMPERSONATION_READ = 'administration.impersonation.read';
    case ADMINISTRATION_APIKEYS_READ = 'administration.apikeys.read';
    case ADMINISTRATION_FIWARE_SUBSCRIPTIONS_READ = 'administration.fiware_subscriptions.read';
    case ADMINISTRATION_FIWARE_SUBSCRIPTIONS_UPDATE = 'administration.fiware_subscriptions.update';
    case ADMINISTRATION_FIWARE_TENANTS_READ = 'administration.fiware_tenants.read';
    case ADMINISTRATION_FIWARE_TENANTS_UPDATE = 'administration.fiware_tenants.update';
    case ADMINISTRATION_RESOURCE_LIMITS_READ = 'administration.resource_limits.read';
    case ADMINISTRATION_RESOURCE_LIMITS_UPDATE = 'administration.resource_limits.update';
    case ADMINISTRATION_DEVICE_FILES_READ = 'administration.device_files.read';
    case ADMINISTRATION_DEVICE_FILES_UPDATE = 'administration.device_files.update';
    case ADMINISTRATION_VISUALIZER_READ = 'administration.visualizer.read';
    case ADMINISTRATION_VISUALIZER_UPDATE = 'administration.visualizer.update';
    case ADMINISTRATION_HEALTHCHECKS_READ = 'administration.healthchecks.read';

        // ----------------
        // PERSONALIZATION
    case PERSONALIZATION_UPDATE = 'personalization.update';

        // ----------------
        // QC
    case APPLICATION_ADMIN = 'application.admin';

        // ----------------
        // BOOTSTRAP
    case BOOTSTRAP_READ = 'bootstrap.read';
    case BOOTSTRAP_UPDATE = 'bootstrap.update';

        // ----------------
        // PAYMENTS

        // ----------------
        // DLM
    case DLM_IMPORTATION_READ = 'dlm.importation.read';
    case DLM_IMPORTATION_UPDATE = 'dlm.importation.update';


        // BACKGROUND JOBS
    case BACKGROUND_JOBS_READ = 'background_jobs.read';

    // LINE, BAR, GAUGE, HISTOGRAM, PIE, CUSTOM_TEXT_TILE, CUSTOM_TABLE, SELECTOR
    public static function hiddenPermissions(): array
    {
        $hidden = [
            self::APPLICATION_ADMIN,
            self::DASHBOARDS_ECHARTS_LINE_READ,
            self::DASHBOARDS_ECHARTS_BAR_READ,
            self::DASHBOARDS_ECHARTS_GAUGE_READ,
            self::DASHBOARDS_ECHARTS_HISTOGRAM_READ,
            self::DASHBOARDS_ECHARTS_LINE_POINTS_READ,
            self::DASHBOARDS_ECHARTS_STACKED_AREA_READ,
            self::DASHBOARDS_ECHARTS_BATTERY_READ,
            self::DASHBOARDS_ECHARTS_LABELED_GAUGE_READ,
            self::DASHBOARDS_ECHARTS_SCATTER_2D_READ,
            self::DASHBOARDS_ECHARTS_SCATTER_3D_READ,
            self::DASHBOARDS_ECHARTS_HEATMAP_CALENDAR_READ,
            self::DASHBOARDS_ECHARTS_SCATTER_CALENDAR_READ,
            self::DASHBOARDS_ECHARTS_SCATTER_HISTOGRAM_READ,
            self::DASHBOARDS_ECHARTS_CANDLESTICK_READ,
            self::DASHBOARDS_ECHARTS_CATEGORY_BAR_READ,
            self::DASHBOARDS_ECHARTS_VERTICAL_CATEGORY_BAR_READ,
            self::DASHBOARDS_ECHARTS_BOXPLOT_READ,
            self::DASHBOARDS_CUSTOM_ICON_READ,
            self::DASHBOARDS_CUSTOM_ICON_TILE_READ,
            self::DASHBOARDS_CUSTOM_DTI_TABLE_READ,
            self::DASHBOARDS_CUSTOM_OGC_WMS_READ,
            self::DASHBOARDS_ECHARTS_HISTOGRAM_READ,
            self::DASHBOARDS_ECHARTS_STEP_LINE_READ,
            self::DASHBOARDS_ECHARTS_WIND_ROSE_READ,
            self::DASHBOARDS_ECHARTS_DONUT_READ,
            self::DASHBOARDS_ECHARTS_HEATMAP_GRAPH_READ,
            self::DASHBOARDS_ECHARTS_MONTHLY_HEATMAP_GRAPH_READ,
            self::DASHBOARDS_ECHARTS_BAR_RACE_READ,
            self::DASHBOARDS_ECHARTS_BAR_STACKED_READ,
            self::DASHBOARDS_ECHARTS_PIE_READ,
            self::DASHBOARDS_ECHARTS_PIE_ROSE_READ,
            self::DASHBOARDS_ECHARTS_RADAR_READ,
            self::DASHBOARDS_CUSTOM_TEXT_TILE_READ,
            self::DASHBOARDS_CUSTOM_TABLE_READ,
            self::DASHBOARDS_CUSTOM_SELECTOR_READ,
            self::DASHBOARDS_CUSTOM_GROUP_READ,
            self::DASHBOARDS_CUSTOM_TILE_READ,
            self::DASHBOARDS_CUSTOM_MAP_READ,
            self::DASHBOARDS_CUSTOM_HEATMAP_READ,
            self::DASHBOARDS_CUSTOM_RADIAL_HEATMAP_READ,
            self::DASHBOARDS_CUSTOM_PLAN_READ,
            self::DASHBOARDS_CUSTOM_TEXT_READ,
            self::DASHBOARDS_CUSTOM_READ,
            self::DASHBOARDS_TEMPLATES_READ,
            self::DASHBOARDS_TEMPLATES_CM_READ,
            self::DASHBOARDS_TEMPLATES_CM_SIMPLE_READ,
            // self::DLM_IMPORTATION_READ,
            // self::DLM_IMPORTATION_UPDATE,
        ];

        return $hidden;
    }

    // DATA SOURCES, ANALYTICS->DASHBOARDS, OUT CONNECTORS, FIWARE, ORGANIZATIONS
    public static function hiddenQcAdminPermissions(): array
    {
        return [
            self::DASHBOARDS_TEMPLATES_CM_SIMPLE_READ,
            self::DASHBOARDS_CUSTOM_CESIUM_VIEWER_READ,
            self::ADMINISTRATION_FIWARE_TENANTS_READ,
            self::ADMINISTRATION_FIWARE_TENANTS_UPDATE,
        ];
    }

    public static function qcAdminPermissions(): array
    {
        $cases = self::cases();

        $hiddenForQcAdmin = self::hiddenQcAdminPermissions();

        $hiddenForQcAdminValues = array_map(fn($case) => $case->value, $hiddenForQcAdmin);

        $qcAdminPermissions = [];

        foreach ($cases as $case) {
            if (!in_array($case->value, $hiddenForQcAdminValues)) {
                $qcAdminPermissions[] = $case;
            }
        }

        return $qcAdminPermissions;
    }

    public static function hiddenSuperAdminPermissions(): array
    {
        return [
            self::DASHBOARDS_TEMPLATES_CM_SIMPLE_READ,
            self::DASHBOARDS_CUSTOM_CESIUM_VIEWER_READ,
        ];
    }

    public static function superAdminPermissions(): array
    {
        $cases = self::cases();

        $hiddenForSuperAdmin = self::hiddenSuperAdminPermissions();

        $hiddenForSuperAdminValues = array_map(fn($case) => $case->value, $hiddenForSuperAdmin);

        $superAdminPermissions = [];

        foreach ($cases as $case) {
            if (!in_array($case->value, $hiddenForSuperAdminValues)) {
                $superAdminPermissions[] = $case;
            }
        }

        return $superAdminPermissions;
    }
}
