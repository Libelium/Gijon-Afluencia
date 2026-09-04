<?php

namespace App\Services\Entities;

/**
 * Reads a file of entities and turns it into creation payloads. It accepts a GeoJSON
 * FeatureCollection, a list of objects or a single object, and depends on neither HTTP
 * nor the database.
 */
class EntityFileImportService
{
    /**
     * Parse entities from JSON/GeoJSON file data.
     *
     * @param array $data
     * @return array
     */
    public function parseEntitiesFromFile(array $data): array
    {
        $entities = [];

        // Check if it's a GeoJSON FeatureCollection
        if (isset($data['type']) && $data['type'] === 'FeatureCollection' && isset($data['features'])) {
            foreach ($data['features'] as $feature) {
                $entity = $this->parseGeoJSONFeature($feature);
                if ($entity) {
                    $entities[] = $entity;
                }
            }
        }
        // Check if it's an array of entities
        elseif (is_array($data) && !isset($data['type'])) {
            foreach ($data as $item) {
                $entity = $this->parseEntityObject($item);
                if ($entity) {
                    $entities[] = $entity;
                }
            }
        }
        // Single entity object
        elseif (isset($data['id']) || isset($data['entity_id'])) {
            $entity = $this->parseEntityObject($data);
            if ($entity) {
                $entities[] = $entity;
            }
        }

        return $entities;
    }

    /**
     * Parse a GeoJSON feature into an entity.
     *
     * @param array $feature
     * @return array|null
     */
    private function parseGeoJSONFeature(array $feature): ?array
    {
        if (!isset($feature['properties']['entity_id'])) {
            return null;
        }

        $entityId = $feature['properties']['entity_id'];
        $entityDatamodel = $this->extractDatamodelFromUrn($entityId);

        // Build attributes from properties (excluding entity_id and timestamp)
        $attributes = [];
        foreach ($feature['properties'] as $key => $value) {
            if ($key === 'entity_id' || $key === 'timestamp') {
                continue;
            }

            $attributes[$key] = [
                'type' => 'Property',
                'value' => $value,
            ];
        }

        // Add location from geometry if present
        if (isset($feature['geometry'])) {
            $attributes['location'] = [
                'type' => 'Property',
                'value' => $feature['geometry'],
            ];
        }

        return [
            'id' => $entityId,
            'type' => $entityDatamodel,
            'attributes' => !empty($attributes) ? $attributes : null,
        ];
    }

    /**
     * Parse a regular entity object.
     *
     * @param array $item
     * @return array|null
     */
    private function parseEntityObject(array $item): ?array
    {
        $entityId = $item['id'] ?? $item['entity_id'] ?? null;
        if (!$entityId) {
            return null;
        }

        $entityDatamodel = $item['type'] ?? $this->extractDatamodelFromUrn($entityId);

        // Build attributes from remaining properties
        $attributes = [];
        $excludedKeys = ['id', 'entity_id', 'type'];

        foreach ($item as $key => $value) {
            if (in_array($key, $excludedKeys)) {
                continue;
            }

            // Check if value is already in NGSI-LD format
            if (is_array($value) && isset($value['type']) && isset($value['value'])) {
                // Force type to Property (Context Broker doesn't accept GeoProperty)
                $value['type'] = 'Property';
                $attributes[$key] = $value;
            } else {
                $attributes[$key] = [
                    'type' => 'Property',
                    'value' => $value,
                ];
            }
        }

        return [
            'id' => $entityId,
            'type' => $entityDatamodel,
            'attributes' => !empty($attributes) ? $attributes : null,
        ];
    }

    /**
     * Extract the entity type from a URN.
     * e.g., urn:ngsi-ld:TouristDestination:TD1011 -> TouristDestination
     *
     * @param string $urn
     * @return string
     */
    private function extractDatamodelFromUrn(string $urn): string
    {
        $parts = explode(':', $urn);
        if (count($parts) >= 3) {
            return $parts[2];
        }
        return 'Unknown';
    }
}
