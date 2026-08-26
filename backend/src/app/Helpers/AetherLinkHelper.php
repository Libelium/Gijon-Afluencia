<?php

namespace App\Helpers;

use Exception;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Http\client\Exception\HttpException;

class AetherLinkHelper
{

    public static function toNgsiNullIfNull($value)
    {
        if ($value === null) {
            return [
                "@type" => "@json",
                "@value" => null
            ];
        }

        return $value;
    }

    /**
     * Sends a request to the context link to update the entity requested attributes.
     * 
     * - $attributes is an associative array of the form:
     *    [ 
     *      "attrName" => {
     *         "type" => "Property|Relationship|Command",
     *        "value" => "attrValue"
     *      }
     *     ...
     *   ]
     * 
     * It doesnt matter if the attribute already exists or not, it will be created, 
     * so be careful with that, and check before if the call is correct
     */
    public static function updateOnContextBroker(string $urn, string $tenant, string $scope, array $attributes): array
    {

        if (count($attributes) == 0) {
            return [
                "updated" => true,
                "response" => "No attributes to update",
                "status" => 200,
            ];
        }

        $requestEntityBodyToAether = [
            "id" => $urn,
            "attributes" => [],
        ];

        // some attributes have some special types, so we need to check them
        // WARNING: this will be a problem in the future, you have been warned
        if (array_key_exists("location", $attributes)) {
            $geolocation = $attributes["location"];
            $geolocationValue = $geolocation["value"];
            if ($geolocationValue === null) {
                $attributes["location"] = [
                    "type" => "Property",
                    "value" => [
                        "coordinates" => [0, 0],
                        "type" => "Point"
                    ]
                ];
            }
        }

        foreach ($attributes as $attrName => $attrContent) {
            $attrValue = $attrContent["value"];
            $attrType = $attrContent["type"];
            if ($attrType === null) {
                continue;
            }
            $attrTimestamp = $attrContent["timestamp"] ?? null;
            $attribute = [
                "type" => $attrType,
                "value" => AetherLinkHelper::toNgsiNullIfNull($attrValue),
            ];
            if ($attrTimestamp !== null) {
                $attribute["timestamp"] = $attrTimestamp;
            }
            $requestEntityBodyToAether["attributes"][$attrName] = $attribute;
        }

        $requestBodyToAether = ["entities" => [$requestEntityBodyToAether]];

        # now, send the request to the context link
        $context_link_url = config('services.aether-link.entity.update');

        $headers = [
            "Accept" => "application/json",
            "Content-Type" => "application/json",
            "tenant" => $tenant,
            "scope" => $scope,
        ];

        try {
            $response = Http::withHeaders($headers)
                ->send(
                    'POST',
                    $context_link_url,
                    [
                        'body' => json_encode($requestBodyToAether)
                    ]
                );

            # this request always returns 207, even if it fails
            # because it is a batch request
            $updated = false;
            $errors = [];
            if ($response->status() != 207) {
                $updated = false;
            } else {
                $responseBody = $response->json();
                $errors = $responseBody["errors"];
                $updated = !$errors || count($errors) == 0;
            }

            return [
                "updated" => $updated,
                "response" => $response->json(),
                "status" => $response->status(),
            ];
        } catch (\Exception $e) {

            return [
                "updated" => false,
                "response" => $e->getMessage(),
                "status" => 500,
            ];
        }
    }


    /**
     * Deletes a specific attribute from an entity in the Context Broker.
     *
     * @param string $urn The URN of the entity
     * @param string $tenant The tenant name
     * @param string $scope The scope name
     * @param string $attributeName The name of the attribute to delete
     * @return array Returns an array with 'deleted', 'response', and 'status' keys
     */
    public static function deleteAttributeOnContextBroker(string $urn, string $tenant, string $scope, string $attributeName): array
    {
        $baseUrl = config('services.aether-link.entity.delete-attribute');
        $encodedUrn = urlencode($urn);
        $encodedAttrName = urlencode($attributeName);
        $url = "{$baseUrl}/{$encodedUrn}/attrs/{$encodedAttrName}";

        $headers = [
            "Accept" => "application/json",
            "Content-Type" => "application/json",
            "tenant" => $tenant,
            "scope" => $scope,
        ];

        try {
            $response = Http::withHeaders($headers)->delete($url);

            $deleted = $response->status() >= 200 && $response->status() < 300;

            return [
                "deleted" => $deleted,
                "response" => $response->json(),
                "status" => $response->status(),
            ];
        } catch (\Exception $e) {
            return [
                "deleted" => false,
                "response" => $e->getMessage(),
                "status" => 500,
            ];
        }
    }

    public static function getTypeSubscriptions(string $tenant, string $scope): array
    {
        try {
            $url = config('services.aether-link.subscription-types');
            $response = Http::withHeaders([
                'tenant' => $tenant,
                'scope' => $scope,
            ])->get($url);

            if ($response->status() != 200) {
                Log::error('Error getting type subscriptions', [
                    'status' => $response->status(),
                    'body' => $response->body(),
                ]);
                return [];
            }

            return $response->json();
        } catch (\Exception $e) {
            Log::error('Exception getting type subscriptions: ' . $e->getMessage());
            return [];
        }
    }

    public static function addTypeSubscriptions(array $newTypes, string $tenant, string $scope): bool
    {
        $body = [];

        foreach ($newTypes as $type) {
            $body[] = [
                'op' => 'add',
                'value' => $type
            ];
        }
        $aether_link_subscription_types = config('services.aether-link.subscription-types');
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->patch($aether_link_subscription_types, $body);

        // check if response ok
        if ($response->status() != 200) {
            return false;
        }

        return $response->json()['added'] == true;
    }

    public static function removeTypeSubscriptions(array $types, string $tenant, string $scope): bool
    {
        $body = [];

        foreach ($types as $type) {
            $body[] = [
                'op' => 'remove',
                'value' => $type
            ];
        }
        $aether_link_subscription_types = config('services.aether-link.subscription-types');
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->patch($aether_link_subscription_types, $body);

        // check if response ok
        if ($response->status() != 200) {
            return false;
        }

        return $response->json()['deleted'] == true;
    }

    public static function getContextBrokerTypes(string $tenant, string $scope): array
    {
        $url = config('services.aether-link.data-types');
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->get($url);

        if ($response->status() != 200) {
            response()->json([
                'message' => 'Error getting context broker types',
            ], 500)->send();
            return [];
        }

        return $response->json();
    }

    public static function createContextBrokerEntity(string $tenant, string $scope, array $entities): bool
    {

        $url = config('services.aether-link.entity.create');
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->post($url, ['entities' => $entities]);

        if ($response->status() < 200 || $response->status() >= 300) {
            return false;
        }

        return true;
    }

    /**
     * getIotaServices. 
     * 
     * Returns the services available for the given tenant, scope and datamodel.
     *
     * @param  mixed $tenant
     * @param  mixed $scope
     * @param  mixed $datamodel
     * @return array
     */
    public static function getIotaServices(string $tenant, string $scope, string|null $datamodel = null): array
    {
        $url = config('services.aether-link.iota.services');
        if ($datamodel) {
            $url .= "?entity_type=$datamodel";
        }
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->get($url);

        if ($response->status() != 200) {
            response()->json([
                'message' => 'Error getting iota services',
                'status' => $response->status(),
                'body' => $response->body(),
            ], 500)->throwResponse();
        }

        return $response->json();
    }

    public static function provisionDevice(string $tenant, string $scope, $device)
    {
        $url = config('services.aether-link.iota.provision-device');
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->post($url, $device);

        if ($response->status() != 200) {
            response()->json([
                'message' => 'Error provisioning device' . $response->body(),
            ], 500)->throwResponse();
            return [];
        }

        return $response;
    }

    public static function provisionService(string $tenant, string $scope, $service)
    {
        $url = config('services.aether-link.iota.provision-service');
        $response = Http::withHeaders(
            [
                'tenant' => $tenant,
                'scope' => $scope
            ]
        )->post($url, $service);

        if ($response->status() != 200) {
            response()->json([
                'message' => 'Error provisioning service' . $response->body(),
            ], 500)->throwResponse();
            return [];
        }

        return $response;
    }

    public static function deleteEntities(array $entitiesUrn, string $tenant, string $scope)
    {
        $url = config('services.aether-link.entity.delete');

        $headers = [
            "Accept" => "application/json",
            "Content-Type" => "application/json",
            'tenant' => $tenant,
            'scope' => $scope
        ];
        $requestBody = [
            "entities_urn" => $entitiesUrn
        ];
        try {
            $response = Http::withHeaders($headers)->delete($url, $requestBody);
            if ($response->status() != 207) {
                return [
                    "deleted" => false,
                    "response" => $response->json(),
                    "status" => $response->status(),
                ];
            }
        } catch (HttpException $e) {
            return [
                "deleted" => false,
                "response" => $e->getMessage(),
                "status" => 500,
            ];
        }
        return [
            "deleted" => true,
            "response" => $response->json(),
            "status" => $response->status(),
        ];
    }

    public static function deleteDevices(array $devices, string $tenant, string $scope)
    {
        $url = config('services.aether-link.iota.delete-device');

        $headers = [
            "Accept" => "application/json",
            "Content-Type" => "application/json",
            'tenant' => $tenant,
            'scope' => $scope
        ];

        $requestBody = [
            "devices_serials" => $devices
        ];

        try {
            $response = Http::withHeaders($headers)->delete($url, $requestBody);
            if ($response->status() != 200) {
                return [
                    "deleted" => false,
                    "response" => $response->json(),
                    "status" => $response->status(),
                ];
            }
        } catch (HttpException $e) {
            return [
                "deleted" => false,
                "response" => $e->getMessage(),
                "status" => 500,
            ];
        }
        return [
            "deleted" => true,
            "response" => $response->json(),
            "status" => $response->status(),
        ];
    }
}
