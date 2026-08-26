<?php

namespace App\Http\V1\Requests\Entities;

use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Contracts\Validation\Validator;

class UpdateEntityRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     *
     * @return bool
     */
    public function authorize()
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array<string, mixed>
     */
    public function rules()
    {
        return [
            "name" => "nullable|string",
            "description" => "nullable|string",
            "geolocation" => "nullable|array:type,coordinates",
            "geolocation.type" => "required_with:geolocation|in:Point,LineString,Polygon,MultiPoint,MultiLineString,MultiPolygon,GeometryCollection",
            "geolocation.coordinates" => "required_with:geolocation|array",
            "timestamp" => "nullable|string",
            "units" => "nullable|string",
        ];
    }

    /**
     * Get custom attributes for validator errors.
     * Override validated() to include all request data, not just validated fields.
     *
     * @return array
     */
    public function validated($key = null, $default = null)
    {
        // Get the validated fields from parent
        $validated = parent::validated($key, $default);

        // Merge with all other fields that aren't in the rules
        // This allows dynamic entity attributes to be passed through
        $allData = $this->all();

        return array_merge($allData, $validated);
    }
}
