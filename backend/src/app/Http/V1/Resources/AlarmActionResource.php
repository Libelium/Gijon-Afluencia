<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class AlarmActionResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $actionContent = [];
        if ($this->action->actionable_type === 'action_email') {
            $actionContent = [
                'to' => $this->action->actionable->destination,
                'subject' => $this->action->actionable->subject,
                'body' => $this->action->actionable->content
            ];
        } elseif ($this->action->actionable_type === 'action_http_push') {
            $actionContent = [
                'url_template' => $this->action->actionable->url_template,
                'method' => $this->action->actionable->method,
                'authorization' => $this->action->actionable->authorization
            ];
        } elseif ($this->action->actionable_type === 'action_telegram') {
            $actionContent = [
                'chat_id' => $this->action->actionable->chat_id,
                'message' => $this->action->actionable->message,
            ];
        } elseif ($this->action->actionable_type === 'action_whatsapp') {
            $actionContent = [
                'phone'   => $this->action->actionable->phone,
                'message' => $this->action->actionable->message,
            ];
        } elseif ($this->action->actionable_type === 'action_sms') {
            $actionContent = [
                'phone'   => $this->action->actionable->phone,
                'message' => $this->action->actionable->message,
            ];
        }
        elseif ($this->action->actionable_type === 'action_entity_command') {
            $actionContent = [
                'commands' => $this->action->actionable->commands,
                'meta'     => $this->action->actionable->meta,
            ];
        }

        $actionTypes = [
            'action_email'    => 'email',
            'action_http_push' => 'http_push',
            'action_telegram' => 'telegram',
            'action_whatsapp' => 'whatsapp',
            'action_sms'      => 'sms',
            'action_entity_command' => 'entity_command',
        ];

        return [
            'type' => $this->type,
            'action_id' => $this->action->id,
            'actionable_content' => $actionContent,
            'actionable_type' => $actionTypes[$this->action->actionable_type],
            'actionable_id' => $this->action->actionable->id
        ];
    }
}
