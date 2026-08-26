<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
//Models
use App\Models\MqttUser;

/**
 * Seeds the MQTT broker administrator.
 *
 * The credential is never stored in the repository: it is supplied through the
 * environment (MQTT_ADMIN_*). When it is not configured the seeder is a no-op,
 * so a fresh install can be migrated and seeded before the broker exists.
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
        $username = env('MQTT_ADMIN_USERNAME');
        $passwordHash = env('MQTT_ADMIN_PASSWORD_HASH');
        $passwordEncrypted = env('MQTT_ADMIN_PASSWORD_ENCRYPTED');
        $passwordSalt = env('MQTT_ADMIN_PASSWORD_SALT');

        if (!$username || !$passwordHash || !$passwordEncrypted || !$passwordSalt) {
            $this->command?->warn('MQTT_ADMIN_* not configured, skipping the MQTT administrator.');

            return;
        }

        MqttUser::updateOrCreate(
            ['username' => $username],
            [
                'username' => $username,
                'password_hash' => $passwordHash,
                'password_encrypted' => $passwordEncrypted,
                'password_salt' => $passwordSalt,
                'is_admin' => true,
                'is_active' => true,
                'organization_id' => null,
            ]
        );
    }
}
