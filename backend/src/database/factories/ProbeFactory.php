<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;
use App\Models\Probe;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\User>
 */
class ProbeFactory extends Factory
{

    protected $model = Probe::class;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            "serial" => $this->faker->uuid,
            "model" => $this->faker->name,
            "struct_def_id" => 1,
            "name" => $this->faker->name,
            "user_id" => 1,
            "order_id" => 1,
        ];
    }

    public function belongsTo($user_id) 
    {
        return $this->state(function (array $attributes) use ($user_id) {
            return [
                "user_id" => $user_id,
            ];
        });
    }
}
