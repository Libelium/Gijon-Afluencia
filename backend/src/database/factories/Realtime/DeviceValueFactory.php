<?php

namespace Database\Factories\Realtime;

use Illuminate\Database\Eloquent\Factories\Factory;
use App\Models\Realtime\DeviceValue;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\Realtime\DeviceValue>
 */
class DeviceValueFactory extends Factory
{

    protected $model = DeviceValue::class;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {

        $serial = $this->faker->uuid;

        return [
            "urn" => "urn:ngsi-ld:Device:" . $serial,
            "value" => "{}",
        ];
    }

    public function urn($urn)
    {
        return $this->state(function (array $attributes) use ($urn) {
            return [
                "urn" => $urn,
            ];
        });
    }

    public function value($value)
    {
        return $this->state(function (array $attributes) use ($value) {
            return [
                "value" => $value,
            ];
        });
    }

}
