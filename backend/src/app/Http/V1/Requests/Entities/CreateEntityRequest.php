<?php

namespace App\Http\V1\Requests\Entities;

use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Contracts\Validation\Validator;
use App\Authorization\AppPermission;
use App\Models\Entity;

class CreateEntityRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     *
     * @return bool
     */
    public function authorize()
    {
        // Admin-managed datamodels (e.g. OperatorsTeam) require incidents.admin; see Entity.
        $types = array_column((array) $this->input('entities', []), 'type');
        if (array_filter($types, fn ($type) => Entity::requiresIncidentsAdmin($type))) {
            return (bool) $this->user()?->can(AppPermission::INCIDENTS_ADMIN->value);
        }

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
