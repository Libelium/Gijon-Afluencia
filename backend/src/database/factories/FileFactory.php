<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;
use App\Models\File;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\User>
 */
class FileFactory extends Factory
{

    protected $model = File::class;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            "name" => $this->faker->name,
            "description" => $this->faker->text,
            "path" => "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "filable_type" => "App\Models\EntityType",
            "filable_id" => 1,
            "type" => "file",
            "downloadable" => true,
            "uuid" => $this->faker->uuid
        ];
    }

    public function forEntityType($device_type_id)
    {
        return $this->state(function (array $attributes) use ($device_type_id) {
            return [
                "filable_type" => "App\Models\EntityType",
                "filable_id" => $device_type_id,
            ];
        });
    }
}
