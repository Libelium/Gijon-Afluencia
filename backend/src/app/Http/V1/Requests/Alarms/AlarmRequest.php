<?php

namespace App\Http\V1\Requests\Alarms;

use App\Http\V1\Requests\FormRequest;

class AlarmRequest extends FormRequest
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
            'name' => 'required|string',
            'type' => 'required|string|in:basic,inactivity',
            'function' => 'required|string|in:AND,OR,XOR',
            'up' => 'required|boolean',
            'disabled' => 'required|boolean',
            'entity_group_id' => 'nullable|integer',
            'conditions' => 'required|array',
            'conditions.*.entityId' => 'nullable|integer',
            'conditions.*.measure' => 'string',
            'conditions.*.condition' => 'string|in:gt,lt,eq,ne,ge,le,between,not_between',
            'conditions.*.threshold' => 'array',
            'conditions.*.period' => 'nullable|array',
            'conditions.*.timeoutS' => 'integer',
        ];
    }
}
