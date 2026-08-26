<?php

namespace App\Http\V1\Requests\Alarms;

use Illuminate\Foundation\Http\FormRequest;

class AlarmConditionRequest extends FormRequest
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
            'entity_id' => 'required|integer',
            'measure' => 'required|string',
            'condition' => 'required|string|in:gt,lt,eq,ne,ge,le,between,not_between',
            'threshold' => 'required|array',
            'period' => 'nullable|array',
        ];
    }
}
