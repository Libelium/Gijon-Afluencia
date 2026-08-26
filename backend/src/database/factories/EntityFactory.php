<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;
use App\Models\Entity;
use App\Models\EntityType;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\Entity>
 */
class EntityFactory extends Factory
{

    protected $model = Entity::class;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        $serial = $this->faker->uuid;
        return [
            'name' => $this->faker->name,
            'description' => $this->faker->text,
            'serial' => $serial,
            'urn' => 'urn:ngsi-ld:Device:'.$serial,
            'entity_type_id' => 1,
            'subscribed_until' => now()->addDays(180),
            'geolocation' => $this->geopointAround(41.665109, -0.885176)
        ];
    }

    // Generates a semi-random geopoint around a given latitude and longitude
    public function geopointAround($latitude, $longitude)
    {
        # random number between - 0.002 and 0.002
        $latitude_offset = $this->faker->randomFloat(6, -0.002, 0.002);
        $longitude_offset = $this->faker->randomFloat(6, -0.002, 0.002);
        $true_latitude = $latitude + $latitude_offset;
        $true_longitude = $longitude + $longitude_offset;
        return 'POINT('.$true_longitude.' '.$true_latitude.')';
    }


    public function belongsTo($user)
    {
        return $this->afterCreating(function (Entity $device) use ($user) {
            $user->entitiesOwned()->attach(
                $device->id,
                [
                    'status' => 'owner',
                    'created_at' => now(),
                    'updated_at' => now(),
                ]
            );
        });
    }

    /************************
    * Entity types
    *************************/
    private function getEntityType($code)
    {
        $record = EntityType::where('code', $code)->firstOrFail();
        return $record->id;
    }

    public function smartParking()
    {
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('parking'),
            ];
        });
    }

    public function airQualityStation()
    {
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('aqs'),
            ];
        });
    }

    public function one(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('one'),
            ];
        });
    }

    public function smartSpot(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('smsp'),
            ];
        });
    }

    public function magneticSensor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('ws301'),
            ];
        });
    }

    public function IndoorAmbienceMonitor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('am103'),
            ];
        });
    }

    public function pirAndLightSensor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('ws202'),
            ];
        });
    }

    public function soundLevelSensor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('ws302'),
            ];
        });
    }

    public function outdoorEnvironmentMonitoring(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('em500_co2'),
            ];
        });
    }

    public function residentialGasDetector(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('gs101'),
            ];
        });
    }

    public function iotMagnetSwitchSensor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('em300_mcs'),
            ];
        });
    }

    public function iotSpotLeakSensor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('em300_sld'),
            ];
        });
    }

    public function iotTemperatureHumiditySensor(){
        return $this->state(function (array $attributes) {
            return [
                'entity_type_id' => $this->getEntityType('em300_th'),
            ];
        });
    }
}
