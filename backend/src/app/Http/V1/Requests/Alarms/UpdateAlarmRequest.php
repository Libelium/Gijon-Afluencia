<?php

namespace App\Http\V1\Requests\Alarms;

use Illuminate\Foundation\Http\FormRequest;

class UpdateAlarmRequest extends AlarmRequest
{
    /**
     * Get the validation rules that apply to the request.
     *
     * @return array<string, mixed>
     */
    public function rules()
    {
        return [
            'name' => 'string',
            'type' => 'string',
            'function' => 'string|in:AND,OR,XOR',
            'up' => 'boolean',
            'disabled' => 'boolean',
        ];
    }
}
