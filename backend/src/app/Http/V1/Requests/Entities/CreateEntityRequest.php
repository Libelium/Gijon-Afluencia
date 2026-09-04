<?php

namespace App\Http\V1\Requests\Entities;

use Illuminate\Http\Exceptions\HttpResponseException;
use App\Http\V1\Requests\FormRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Contracts\Validation\Validator;

class CreateEntityRequest extends FormRequest
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
            "entities" => "required|array",
            "entities.*.id" => "required|string",
            "entities.*.type" => "required|string",
            "entities.*.attributes" => "nullable|array",
            "entities.*.attributes.*.type" => "required_with:entities.*.attributes.*|string",
            "entities.*.attributes.*.value" => "required_with:entities.*.attributes.*",
        ];
    }
}
