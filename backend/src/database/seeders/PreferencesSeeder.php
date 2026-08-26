<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
//Models
use App\Models\Preference;

class PreferencesSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $preferences = [
            [
                'name' => 'displayskinMode',
                'default_value' => 'light',
            ],
            [
                'name' => 'language',
                'default_value' => 'en',
            ],
            [
                'name' => 'numberFormat',
                'default_value' => 'en-EN',
            ],
            [
                'name' => 'datetimeFormat',
                'default_value' => 'en-EN',
            ],
            [
                'name' => 'homeDashboard',
                'default_value' => null,
            ],
            [
                'name' => 'maps',
                'default_value' => 'google',
            ],
            [
                'name' => 'numRecordsCharts',
                'default_value' => '250',
            ],
            [
                'name' => 'timeZone',
                'default_value' => 'GMT',
            ],
            [
                'name' => 'devicesDefaultView',
                'default_value' => 'list',
            ],
            [
                'name' => 'subscriptionAutoSync',
                'default_value' => 'true',
            ],
            [
                'name' => 'themeLightIcon',
                'default_value' => null,
            ],
            [
                'name' => 'themeDarkIcon',
                'default_value' => null,
            ],
            [
                'name' => 'themeLoginIcon',
                'default_value' => null,
            ],
            [
                'name' => 'themeSkin',
                'default_value' => null,
            ],
            [
                'name' => 'themeClass',
                'default_value' => null,
            ],
            [
                'name' => 'themePrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'themeContentWidth',
                'default_value' => null,
            ],
            [
                'name' => 'themeNavbarType',
                'default_value' => null,
            ],
            [
                'name' => 'themeFooterType',
                'default_value' => null,
            ],
            [
                'name' => 'themeCustomFooter',
                'default_value' => null,
            ],
            [
                'name' => 'mainScope',
                'default_value' => null,
            ],
            [
                'name' => 'platformDataScope',
                'default_value' => null,
            ],
            [
                'name' => 'accessLogEnabled',
                'default_value' => 'true'
            ],
            [
                'name' => 'maxAccessAttempts',
                'default_value' => '5'
            ],
            [
                'name' => 'activeMFA',
                'default_value' => 'false'
            ],
            [
                'name' => 'activeLayoutId',
                'default_value' => null,
            ],
            [
                'name' => 'themeSecondaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'darkThemeSecondaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'lightThemeSecondaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'lightThemePrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'darkThemePrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'darkThemeLightPrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'lightThemeLightPrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'themeLightPrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'themeLightPrimaryColor',
                'default_value' => null,
            ],
            [
                'name' => 'devicesListCustomColumns',
                'default_value' => null,
            ],
            [
                'name' => 'exportDeviceProperties',
                'default_value' => 'false',
            ],
            [

                'name' => 'incidentClosurePolicy',
                'default_value' => 'auto',
            ],
            [
                'name' => 'criticalAlertConfig',
                'default_value' => '{"push":true,"pushMessage":"A critical (P1) incident has been reported and requires immediate attention.","email":false,"emails":[]}',
            ]
        ];

        foreach ($preferences as $preference) {
            $preferenceModel = Preference::firstOrCreate([
                'name' => $preference['name'],
            ]);

            if ($preferenceModel->wasRecentlyCreated) {
                $preferenceModel->created_at = now();
            }

            $preferenceModel->default_value = $preference['default_value'];
            $preferenceModel->updated_at = now();

            $preferenceModel->save();
        }
    }
}
