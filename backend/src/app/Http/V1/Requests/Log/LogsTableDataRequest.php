<?php

namespace App\Http\V1\Requests\Log;

use App\Http\V1\Requests\FormRequest;

class LogsTableDataRequest extends FormRequest
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
            'paginationSize' => 'integer',
            'page' => 'integer',
            'orderBy' => 'string',
            'orderDirection' => 'boolean',
            'devices' => 'integer|nullable',
            'connector' => 'nullable|integer',
            'message' => 'nullable|string',
            'type' => 'string',
            'level' => 'nullable|string',
            'start_date' => 'nullable|date',
            'end_date' => 'nullable|date',
            'resource_type' => 'nullable|string',
            'resource_id' => 'nullable|array',
            'resource_id.*' => 'integer',
        ];
    }
}
