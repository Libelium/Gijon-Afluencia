<?php

namespace App\Http\V1\Requests\OutConnectors;

use App\Http\V1\Requests\FormRequest;
use App\Models\OutConnectors\MqttConnector;
use Illuminate\Validation\ValidationException;

class MqttConnectorRequest extends FormRequest
{
    // What the queues-consumer can build: payload builders and topic template variables.
    // Sent periodically with every reading of the linked models in one message.
    public const SNAPSHOT_PAYLOAD_TYPES = ['occupancy_readings', 'flow_readings', 'device_inventory'];
    public const PAYLOAD_TYPES = ['legacy', 'normalized', 'key_value', ...self::SNAPSHOT_PAYLOAD_TYPES];
    public const TOPIC_VARIABLES = ['urn', 'tenant', 'scope'];
    // A snapshot carries many items: {id} sends one message per item, each to its own subtopic.
    public const SNAPSHOT_TOPIC_VARIABLES = ['id'];
    // legacy sends one message per attribute, so its topic can also carry the measure.
    public const LEGACY_TOPIC_VARIABLES = ['urn', 'tenant', 'scope', 'measure'];
    public const LEGACY_PAYLOAD_KEYS = ['timestamp', 'value', 'urn', 'tenant', 'scope', 'measure', 'unit'];

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
            'name' => 'required|string|max:255',
            'use_readable_names' => 'boolean',
            // Host name or IP only: no scheme, path or credentials.
            'ipAddress' => ['required', 'string', 'max:255', 'regex:/^[A-Za-z0-9.\-:\[\]]+$/'],
            'port' => 'required|integer|between:1,65535',
            'username' => 'nullable|string|max:255',
            'password' => 'nullable|string|max:255',
            'clientId' => 'nullable|string|max:255',
            'ssl' => 'required|boolean',
            'sslCert' => 'nullable|string|max:65535',
            // Client certificate and key (PEM), for brokers that authenticate by certificate.
            'clientCert' => ['nullable', 'string', 'max:65535', 'regex:/-----BEGIN CERTIFICATE-----/'],
            'clientKey' => ['nullable', 'string', 'max:65535', 'regex:/-----BEGIN ([A-Z]+ )?PRIVATE KEY-----/'],
            'topicTemplate' => 'required|array|min:1',
            'topicTemplate.*.type' => 'required|string',
            'topicTemplate.*.value' => 'required|string|max:255',
            'payload_type' => 'required|string|in:' . implode(',', self::PAYLOAD_TYPES),
            // Only legacy: [{key, value, active}], renames and filters the fields of each message.
            'payload_config' => 'nullable|array|prohibited_unless:payload_type,legacy',
            'payload_config.*.key' => 'required|string|in:' . implode(',', self::LEGACY_PAYLOAD_KEYS),
            'payload_config.*.value' => 'required|string|max:255',
            'payload_config.*.active' => 'required|boolean',
        ];
    }

    public function withValidator($validator)
    {
        $validator->after(function ($validator) {
            if (($this->filled('clientCert') || $this->filled('clientKey')) && !$this->boolean('ssl')) {
                $validator->errors()->add('clientCert', 'A client certificate needs the TLS connection');
            }
            if ($this->filled('clientKey') && !$this->filled('clientCert')) {
                $validator->errors()->add('clientCert', 'The client key needs its certificate');
            }

            $payloadType = $this->input('payload_type');
            $allowed = match (true) {
                $payloadType === 'legacy' => self::LEGACY_TOPIC_VARIABLES,
                in_array($payloadType, self::SNAPSHOT_PAYLOAD_TYPES, true) => self::SNAPSHOT_TOPIC_VARIABLES,
                default => self::TOPIC_VARIABLES,
            };

            foreach ((array) $this->input('topicTemplate', []) as $i => $part) {
                if (($part['type'] ?? null) === 'variable'
                    && !in_array($part['value'] ?? null, $allowed, true)) {
                    $validator->errors()->add(
                        "topicTemplate.$i.value",
                        'Allowed variables: ' . implode(', ', $allowed)
                    );
                }
            }
        });
    }

    /**
     * Fields stored in the mqtt_connector table.
     */
    public function connectorData(): array
    {
        return [
            'ipAddress' => $this->input('ipAddress'),
            'port' => $this->input('port'),
            'username' => $this->input('username'),
            'clientId' => $this->input('clientId'),
            'ssl' => $this->boolean('ssl'),
            'sslCert' => $this->input('sslCert'),
            'topicTemplate' => $this->input('topicTemplate'),
            'payload_type' => $this->input('payload_type'),
            // NOT NULL column; only legacy takes a configuration.
            'payload_config' => $this->input('payload_config') ?? [],
        ];
    }

    /**
     * Client certificate and key to store. The API never returns the key, so on update an
     * empty key keeps the current one; an empty certificate removes both.
     *
     * @throws ValidationException when there is a certificate and no key, new or stored.
     */
    public function clientCertificateData(?MqttConnector $current = null): array
    {
        $certificate = $this->filled('clientCert') ? trim($this->input('clientCert')) : null;
        if ($certificate === null) {
            return ['clientCert' => null, 'clientKey' => null];
        }

        $key = $this->filled('clientKey') ? trim($this->input('clientKey')) : $current?->clientKey;
        if (!$key) {
            throw ValidationException::withMessages([
                'clientKey' => 'The client certificate needs its private key',
            ]);
        }

        return ['clientCert' => $certificate, 'clientKey' => $key];
    }
}
