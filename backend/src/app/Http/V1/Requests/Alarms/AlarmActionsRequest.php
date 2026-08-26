<?php

namespace App\Http\V1\Requests\Alarms;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Validator;

class AlarmActionsRequest extends FormRequest
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
            'alarm_ids' => 'nullable|array',
            'alarm_ids.*' => 'required|integer',
            'actions' => 'nullable|array',
            'actions.*.name' => 'nullable|string',
            'actions.*.type' => 'required|string|in:email,push,http_push,telegram,whatsapp,sms,entity_command',
            'actions.*.commands' => 'nullable|array',
            'actions.*.alarm_trigger' => 'required|string|in:up,down',
        ];
    }

    /**
     * Configure the validator instance.
     *
     * @param  \Illuminate\Validation\Validator  $validator
     * @return void
     */
    public function withValidator(Validator $validator)
    {
        $validator->after(function ($validator) {
            $actions = $this->input('actions', []);
            foreach ($actions as $key => $action) {
                $type = $action['type'] ?? null;
                // Custom validation for 'destination' based on 'type'
                // 'destination' field comes as 'to' for email
                if ($type === 'email' && !is_array($action['to'] ?? null)) {
                    $validator->errors()->add("actions.$key.to", 'The destination must be an array when type is email.');
                }
                // Destination in push type is not checked, as it uses the current session's user id
                if ($type === 'email' && !is_string($action['subject'] ?? null)) {
                    $validator->errors()->add("actions.$key.subject", 'The subject must be a string when type is email.');
                } elseif ($type === 'email' && !is_string($action['body'] ?? null)) {
                    $validator->errors()->add("actions.$key.body", 'The content must be a string when type is email.');
                } elseif ($type === 'push' && !is_string($action['title'] ?? null)) {
                    $validator->errors()->add("actions.$key.title", 'The title must be a string when type is push.');
                } elseif ($type === 'push' && !is_array($action['content'] ?? null)) {
                    $validator->errors()->add("actions.$key.content", 'The content must be an array when type is push.');
                } elseif ($type === 'telegram' && !is_string($action['message'] ?? null)) {
                    $validator->errors()->add("actions.$key.message", 'The message must be a string when type is telegram.');
                } elseif ($type === 'whatsapp' && !is_string($action['phone'] ?? null)) {
                    $validator->errors()->add("actions.$key.phone", 'The phone must be a string when type is whatsapp.');
                } elseif ($type === 'whatsapp' && !preg_match('/^\+[1-9]\d{7,14}$/', $action['phone'] ?? '')) {
                    $validator->errors()->add("actions.$key.phone", 'The phone must be a valid E.164 number (e.g. +34600000000).');
                } elseif ($type === 'whatsapp' && !is_string($action['message'] ?? null)) {
                    $validator->errors()->add("actions.$key.message", 'The message must be a string when type is whatsapp.');
                } elseif ($type === 'sms' && !is_string($action['phone'] ?? null)) {
                    $validator->errors()->add("actions.$key.phone", 'The phone must be a string when type is sms.');
                } elseif ($type === 'sms' && !preg_match('/^\+[1-9]\d{7,14}$/', $action['phone'] ?? '')) {
                    $validator->errors()->add("actions.$key.phone", 'The phone must be a valid E.164 number (e.g. +34600000000).');
                } elseif ($type === 'sms' && !is_string($action['message'] ?? null)) {
                    $validator->errors()->add("actions.$key.message", 'The message must be a string when type is sms.');
                } elseif ($type === 'entity_command' && !is_array($action['commands'] ?? null)) {
                    $validator->errors()->add("actions.$key.commands", 'commands must be an array when type is entity_command.');
                }
            }
        });
    }
}
