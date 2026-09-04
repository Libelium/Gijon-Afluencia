<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
//Models
use App\Models\MqttUser;

/**
 * Seeds the MQTT broker administrator.
 *
 * The credential is never stored in the repository: only its hash is supplied, through the
 * environment (MQTT_ADMIN_*, read through config/mqtt.php). When it is not configured the
 * seeder is a no-op, so a fresh install can be migrated and seeded before the broker exists.
 */
class MqttUserSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $username = config('mqtt.admin.username');
        $passwordHash = config('mqtt.admin.password_hash');

        if (!$username || !$passwordHash) {
            $this->command?->warn('MQTT_ADMIN_* not configured, skipping the MQTT administrator.');

            return;
        }

        MqttUser::updateOrCreate(
            ['username' => $username],
            [
                'username' => $username,
                'password_hash' => $passwordHash,
                'is_admin' => true,
                'is_active' => true,
                'organization_id' => null,
            ]
        );
    }
}
