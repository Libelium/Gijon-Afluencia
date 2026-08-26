<?php

namespace App\Http\V1\Requests\Alarms;

use Illuminate\Foundation\Http\FormRequest;

class UpdateAlarmConditionRequest extends FormRequest
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
            'entity_id' => 'nullable|integer',
            'measure' => 'nullable|string',
            'condition' => 'nullable|string|in:gt,lt,eq,ne,ge,le,between,not_between',
            'threshold' => 'nullable|array',
            'period' => 'nullable|array',
        ];
    }
}
