<?php

namespace App\Http\V1\Requests;

use Illuminate\Foundation\Http\FormRequest;

class PaginationRequest extends FormRequest
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
            'paginationSize' => 'required|integer',
            'page' => 'required|integer',
            'orderBy' => 'required|string',
            'orderDirection' => 'required|boolean',
            'search' => 'nullable|string',
        ];
    }
}
