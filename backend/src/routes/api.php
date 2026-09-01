<?php

use Illuminate\Support\Facades\Route;

use App\Http\V1\Controllers\AlarmActionController;
use App\Http\V1\Controllers\AlarmConditionController;
use App\Http\V1\Controllers\AlarmController;
use App\Http\V1\Controllers\DashboardController;
use App\Http\V1\Controllers\DeviceController;
use App\Http\V1\Controllers\EntityController;
use App\Http\V1\Controllers\EntityGroupController;
use App\Http\V1\Controllers\FiwareTenantScopeController;
use App\Http\V1\Controllers\HelpController;
use App\Http\V1\Controllers\HomeLayoutController;
use App\Http\V1\Controllers\HomeWidgetController;
use App\Http\V1\Controllers\InactivityAlarmConditionController;
use App\Http\V1\Controllers\LogsController;
use App\Http\V1\Controllers\OrganizationController;
use App\Http\V1\Controllers\PanelController;
use App\Http\V1\Controllers\PermissionController;
use App\Http\V1\Controllers\PhoneVerificationController;
use App\Http\V1\Controllers\Realtime\RealtimeDeviceController;
use App\Http\V1\Controllers\Realtime\RealtimeEntityController;
use App\Http\V1\Controllers\Realtime\UserNotificationController;
use App\Http\V1\Controllers\RegulationController;
use App\Http\V1\Controllers\ResetPasswordController;
use App\Http\V1\Controllers\TagController;
use App\Http\V1\Controllers\TelegramController;
use App\Http\V1\Controllers\TimeSeriesController;
use App\Http\V1\Controllers\UserController;
use App\Http\V1\Controllers\UserPreferencesController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "api" middleware group. Make something great!
|
*/

/**
 * Route for system health check
 */
Route::get('/hchk', function () {
    return response('OK', 200);
});

/**
 * Internal routes for the APISIX gateway.
 *
 * They stay outside `auth:api` because the gateway calls them while it is still deciding
 * whether to admit a request. They are NOT public: PermissionController authenticates every
 * call with the shared X-Gateway-Secret header (config `services.api-gateway.secret`) and
 * fails closed when that secret is not configured.
 */
Route::prefix('internal')->group(function () {
    Route::post('check-write-permission', [PermissionController::class, 'checkWritePermission']);
    Route::post('check-fiware-write-permission', [PermissionController::class, 'checkFiwareWritePermission']);
});

Route::middleware('auth:api')->group(function () {
    Route::prefix('help')->group(function () {
        Route::post('search', [HelpController::class, 'searchContent']);
        Route::get('changelog', [HelpController::class, 'getChangelogIndex']);
        Route::get('changelog/{version}', [HelpController::class, 'getChangelog']);
        Route::get('index', [HelpController::class, 'getFolderIndex']);
        Route::get('content/{folder}/{filepath}', [HelpController::class, 'getFileContent'])->where('filepath', '(.*)');
        // Same URL as before, now behind auth:api: documentation images are part of the
        // documentation, and the documentation is only served to authenticated users.
        Route::get('image/{folder}/{filepath}', [HelpController::class, 'getImage'])->where('filepath', '(.*)');
    });
});

Route::prefix("V1")->group(function () {
    //Documentation
    Route::get('documentation/{lang}', [HelpController::class, 'downloadDocumentation']);

    //Api login
    Route::post('login', [UserController::class, 'login'])->middleware('throttle:10,1');
    Route::post('refresh-token', [UserController::class, 'refreshKcToken'])->middleware('throttle:10,1');

    //Password recovery (Trottle: 10 attempts per minute)
    Route::post('password/recovery', [ResetPasswordController::class, 'resetLink'])->middleware('throttle:10,1');
    Route::post('password/change', [ResetPasswordController::class, 'changePassword']);

    //time series for public dashboards
    Route::post('public/timeseries/{slug}', [TimeSeriesController::class, 'unauthenticated_timeseries_request']);
    Route::get('public/dashboards/{slug}', [DashboardController::class, 'getPublicDashboard']);

    Route::prefix('publicOrganizations')->group(function () {
        Route::prefix('{id}/preferences')->group(function () {
            Route::get('', [OrganizationController::class, 'getPreferencesByOrganizationId']);
            Route::get('/{preferenceName}', [OrganizationController::class, 'getPreferenceByOrganizationId']);
            Route::get('/{preferenceName}/image', [OrganizationController::class, 'getPreferenceImageByOrganizationId']);
        });
    });

    Route::middleware('auth:api')->group(function () {

        // Api logout
        Route::post('logout', [UserController::class, 'logout'])->middleware('auth:api');

        // Manually change the password of a logged user
        Route::put('password/change', [ResetPasswordController::class, 'updatePassword']);

        // tenants and scopes
        Route::prefix('fiwareTenants')->group(function () {
            Route::get('', [FiwareTenantScopeController::class, 'getTenants']);
            Route::get('{id}', [FiwareTenantScopeController::class, 'getTenant']);
            Route::get('{id}/scopes', [FiwareTenantScopeController::class, 'getTenantScopes']);
        });

        Route::prefix('fiwareScopes')->group(function () {
            Route::get('', [FiwareTenantScopeController::class, 'getScopes']);
            Route::get('services', [FiwareTenantScopeController::class, 'getTenantScopeServices']);
            Route::get('services/{organizationId}', [FiwareTenantScopeController::class, 'getTenantScopeServicesOrganization']);
            Route::get('{id}/tenant', [FiwareTenantScopeController::class, 'getScopeTenant']);
        });

        // User resource
        Route::prefix('user')->group(function () {
            Route::prefix('{id}/preferences')->group(function () {
                Route::get('', [UserPreferencesController::class, 'getPreferences']);
                Route::get('/{preferenceName}', [UserPreferencesController::class, 'getPreference']);
                Route::put('/{preferenceName}', [UserPreferencesController::class, 'updatePreference']);
            });

        });

        Route::apiResource('user', UserController::class, ['only' => ['show', 'update']]);

        // This overwrites the default route for the index method to get the user with the logged user's id
        Route::get('user', [UserController::class, 'getUser']);

        Route::prefix('organizations')->group(function () {
            Route::prefix('{id}/preferences')->group(function () {
                Route::get('', [OrganizationController::class, 'getPreferences']);
                Route::get('/{preferenceName}', [OrganizationController::class, 'getPreference']);
                Route::put('/{preferenceName}', [OrganizationController::class, 'updatePreference']);
                Route::delete('/{preferenceName}', [OrganizationController::class, 'deletePreference']);
            });
        });

        Route::apiResource('organizations', OrganizationController::class, ['only' => ['show']]);

        Route::prefix('entities')->group(function () {
            Route::get('fromDevice/{id}', [EntityController::class, 'getEntitiesFromDeviceId']);
            Route::post('paginate', [EntityController::class, 'paginate']);
            Route::post('datamodels/paginate', [EntityController::class, 'paginateDatamodels']);
            Route::post('list', [EntityController::class, 'listAll']);
            Route::post('sendCommands', [EntityController::class, 'sendCommandsBulk']);
            Route::patch('{id}/properties', [EntityController::class, 'upsertProperties']);
            Route::delete('{id}/properties/{attributeName}', [EntityController::class, 'deleteProperty']);
            Route::post('{id}/sendCommands', [EntityController::class, 'sendCommands']);
            Route::post('/getEntityIdTenantScope', [EntityController::class, 'getEntityIdTenantScope']);
            Route::post('getLastDataTimestamps', [EntityController::class, 'getLastDataTimestamps']);
            Route::post('uploadData',  [EntityController::class, 'uploadDataToEntity']);
            Route::post('storeFromFile', [EntityController::class, 'storeFromFile']);
            Route::post('healthchecks/paginate', [EntityController::class, 'paginateHealthchecks']);
            Route::post('commands/paginate', [EntityController::class, 'paginateEntitiesWithCommands']);
            Route::post('by-ids-for-alarm-action', [EntityController::class, 'entitiesForAlarmActionByIds']);
        });
        Route::apiResource('entities', EntityController::class)->only(['show', 'store']);

        // Devices: only what the entity list/view, the map and the alarms module need.
        Route::prefix('devices')->group(function () {
            Route::post('paginate', [DeviceController::class, 'paginate']);
            Route::get('{id}/entities', [DeviceController::class, 'getEntities']);
            Route::post('by-entity-ids', [DeviceController::class, 'devicesByEntityIds']);
        });

        Route::apiResource('devices', DeviceController::class)->only(['show']);

        // Dashboard resource
        Route::post('dashboards/setTemplateType/{id}', [DashboardController::class, 'setTemplateType']);
        Route::post('dashboards/setTemplateConfig/{id}', [DashboardController::class, 'setTemplateConfig']);
        Route::post('dashboards/setTemplateEntities/{id}', [DashboardController::class, 'setTemplateEntities']);
        Route::post('dashboards/setTemplateDevices/{id}', [DashboardController::class, 'setTemplateDevices']);
        Route::post('dashboards/setTemplateGroups/{id}', [DashboardController::class, 'setTemplateGroups']);
        Route::post('dashboards/setTemplateRegulation/{id}', [DashboardController::class, 'setTemplateRegulation']);
        Route::post('dashboards/paginate', [DashboardController::class, 'index']);
        Route::post('dashboards/custom', [DashboardController::class, 'indexCustom']);
        Route::post('dashboards/images/{id}', [DashboardController::class, 'setImage']);
        Route::get('dashboards/images/{id}', [DashboardController::class, 'getImage']);
        Route::get('dashboards/uploaded-images', [DashboardController::class, 'getUploadedImages']);
        Route::get('dashboards/uploaded-images/{filename}', [DashboardController::class, 'getUploadedImage']);
        Route::post('dashboards/from-json', [DashboardController::class, 'createFromJson']);
        Route::post('dashboards/{id}/from-json', [DashboardController::class, 'updateFromJson']);
        Route::apiResource('dashboards', DashboardController::class, ['except' => ['index']]);

        // Tags resource
        Route::get('tags', [TagController::class, 'index']);
        Route::post('tags', [TagController::class, 'store']);
        Route::patch('tags', [TagController::class, 'modificationsInBatch']);
        Route::put('tags/{id}', [TagController::class, 'update']);
        Route::delete('tags/{id}', [TagController::class, 'destroy']);

        // Panel resource
        Route::post('panels/images/{id}', [PanelController::class, 'setImage']);
        Route::get('panels/images/{id}', [PanelController::class, 'getImage']);
        Route::apiResource('panels', PanelController::class);

        // Notifications
        Route::prefix('realtime/notifications')->group(function () {
            Route::get('', [UserNotificationController::class, 'getData']);
            Route::post('readAll', [UserNotificationController::class, 'readAll']);
            Route::get('countData', [UserNotificationController::class, 'countData']);
            Route::put('updateRead/{id}', [UserNotificationController::class, 'updateRead']);
            Route::delete('deleteNotification/{id}', [UserNotificationController::class, 'deleteNotification']);
        });

        // Logs
        Route::prefix('logs')->group(function () {
            Route::post('paginate', [LogsController::class, 'paginate']);
        });

        // Time series
        Route::post('timeseries', [TimeSeriesController::class, 'authenticated_timeseries_request']);

        // Realtime data
        Route::prefix('realtime/entities')->group(function () {
            Route::post('', [RealtimeEntityController::class, 'getEntitiesRequest']);
            Route::post('sorted', [RealtimeEntityController::class, 'getLastDataTimeEntitiesRequest']);
            Route::post('sortedBulk', [RealtimeEntityController::class, 'getLastDataTimeEntitiesRequestBulk']);
            Route::get('measures/available', [RealtimeEntityController::class, 'getAvailableMeasuresRequest']);
            Route::get('{urn}', [RealtimeEntityController::class, 'getEntityRequest']);
            Route::get('timeLastData/{urn}', [RealtimeEntityController::class, 'getLastDataRequest']);
            Route::post('timeLastData', [RealtimeEntityController::class, 'getLastDataRequestBulk']);
        });

        Route::prefix('realtime/devices')->name('realtime.devices.')->group(function () {
            Route::get('/{id}', [RealtimeDeviceController::class, 'getDeviceDataRequest']);
        });

        // Regulations (used by the dashboard templates)
        Route::post('regulations/paginate', [RegulationController::class, 'paginate']);
        Route::apiResource('regulations', RegulationController::class)->except(['index']);

        // Alarms
        Route::post('alarms/paginate', [AlarmController::class, 'paginate']);
        Route::apiResource('alarms', AlarmController::class)->except(['index']);

        // Alarm conditions
        Route::apiResource('alarms/{alarmId}/conditions', AlarmConditionController::class);
        Route::post('alarms/{alarmId}/conditions/bulkUpdateCreate', [AlarmConditionController::class, 'bulkUpdate']);

        // Inactivity alarm conditions
        Route::apiResource('alarms/{alarmId}/inactivityConditions', InactivityAlarmConditionController::class);
        Route::post('alarms/{alarmId}/inactivityConditions/bulkUpdateCreate', [InactivityAlarmConditionController::class, 'bulkUpdate']);

        // Alarm notification channels
        Route::prefix('phone')->group(function () {
            // Rate limited like login / refresh-token: the confirmation code is 6 digits and
            // valid for 10 minutes. The controller additionally locks out after a handful of
            // wrong guesses per user + phone number.
            Route::post('verify/send',    [PhoneVerificationController::class, 'send'])->middleware('throttle:5,1');
            Route::post('verify/confirm', [PhoneVerificationController::class, 'confirm'])->middleware('throttle:10,1');
        });

        Route::prefix('telegram')->group(function () {
            Route::get('config', [TelegramController::class, 'config']);
            Route::post('connect', [TelegramController::class, 'connect']);
            Route::get('status', [TelegramController::class, 'status']);
            Route::delete('disconnect', [TelegramController::class, 'disconnect']);
        });

        // Alarm actions
        Route::apiResource('alarms/{alarmId}/actions', AlarmActionController::class)->only(['index', 'destroy']);
        Route::post('alarms/{alarmId}/actions/bulkUpdateCreate', [AlarmActionController::class, 'bulkUpdate']);
        Route::post('alarms/actions', [AlarmActionController::class, 'store']);
        Route::get('alarms/actions/channels', [AlarmActionController::class, 'channels']);

        //Groups
        Route::post('groups/paginate', [EntityGroupController::class, 'paginate']);
        Route::patch('groups/{id}/status', [EntityGroupController::class, 'updateStatus']);
        Route::apiResource('groups', EntityGroupController::class, ['except' => ['index']]);

        // Home Layouts
        Route::post('home-layouts/create-default', [HomeLayoutController::class, 'createDefaultLayout']);
        Route::apiResource('home-layouts', HomeLayoutController::class, ['except' => ['update']]);
        Route::patch('home-layouts/{id}', [HomeLayoutController::class, 'update']);

        // Home Widgets
        Route::post('home-layouts/{layoutId}/widgets/paginate', [HomeWidgetController::class, 'paginate']);
        Route::post('home-layouts/{layoutId}/widgets', [HomeWidgetController::class, 'store']);
        Route::post('home-layouts/{layoutId}/widgets/batch', [HomeWidgetController::class, 'batchStore']);
        Route::put('home-layouts/{layoutId}/widgets/batch', [HomeWidgetController::class, 'batchUpdate']);
        Route::delete('home-layouts/{layoutId}/widgets/batch', [HomeWidgetController::class, 'batchDestroy']);
        Route::patch('home-widgets/{id}', [HomeWidgetController::class, 'update']);
        Route::delete('home-widgets/{id}', [HomeWidgetController::class, 'destroy']);
    });
});
