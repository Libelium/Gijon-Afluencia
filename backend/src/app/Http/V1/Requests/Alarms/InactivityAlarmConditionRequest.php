<?php

namespace App\Http\V1\Requests\Alarms;

use App\Http\V1\Requests\FormRequest;

class InactivityAlarmConditionRequest extends FormRequest
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
            'entityId' => 'required|integer',
            'measure' => 'nullable|string',
            'timeoutS' => 'required|integer'
        ];
    }

    public function toModel()
    {
        return [
            'entity_id' => $this->input('entityId'),
            'measure' => $this->input('measure'),
            'timeout_s' => $this->input('timeoutS')
        ];
    }
}
