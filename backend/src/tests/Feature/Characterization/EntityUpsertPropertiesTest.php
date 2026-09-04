<?php

namespace Tests\Feature\Characterization;

use App\Authorization\AppPermission;
use App\Enums\UserStatus;
use App\Models\Entity;
use App\Models\EntityGroup;
use App\Models\Organization;
use App\Models\Realtime\EntityProperty;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Http\Client\Request as ClientRequest;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * CHARACTERIZATION TESTS — EntityController::upsertProperties.
 *
 * upsertProperties is the highest-NPath method in the codebase (190 464 paths, ~1 180-line
 * controller). They are a safety net BEFORE the god-controller refactor, and describe what the
 * endpoint does TODAY — including behaviour that is arguably wrong (each such case is called out
 * in a comment). They are not a specification: if
 * the refactor deliberately changes one of these behaviours, the assertion is updated in the same
 * commit, on purpose, and the change is visible in review. Silent drift is what they prevent.
 *
 * They drive the real HTTP route (PATCH /api/V1/entities/{id}/properties) rather than the
 * controller object, so they keep working if the method is extracted into a service or an action
 * class — which is precisely the refactor they are meant to protect.
 *
 * The only thing faked is the outbound call to aether-link (the Context Broker gateway), which
 * AetherLinkHelper performs through the Http facade. Faking it lets the tests assert the exact
 * NGSI-LD payload that goes on the wire, which is where most of the branching ends up.
 *
 * The context broker contract, from AetherLinkHelper::updateOnContextBroker:
 *   - it is a BATCH endpoint that always answers 207;
 *   - "updated" is true only when the response is 207 AND its `errors` array is empty;
 *   - any other status, or a transport exception, means not updated.
 *
 * @see \App\Http\V1\Controllers\EntityController::upsertProperties
 */
class EntityUpsertPropertiesTest extends TestCase
{
    use DatabaseTransactions;

    /** Entity properties live in the separate realtime database. */
    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private const AETHER_UPDATE_URL = '*/api/v1/context-broker/entities/update';

    private User $admin;
    private Entity $entity;

    /**
     * Http::fake() ACCUMULATES stubs and the first matching one wins, so a default registered in
     * setUp() would shadow any per-test override. The default is therefore registered lazily, just
     * before the request, and only if the test did not already install its own.
     */
    private bool $brokerFaked = false;

    protected function setUp(): void
    {
        parent::setUp();

        $this->admin = $this->makeUser([AppPermission::APPLICATION_ADMIN]);
        $this->entity = $this->makeEntity();
    }

    // ----------------------------------------------------------------- guard clauses

    public function test_an_empty_payload_is_rejected_before_anything_else_happens(): void
    {
        $response = $this->patchProperties([]);

        $response->assertStatus(400);
        $this->assertSame('No properties to update', $response->getContent());

        // The guard runs before Entity::findOrFail, so nothing is looked up or sent.
        Http::assertNothingSent();
    }

    public function test_an_unknown_entity_is_a_404(): void
    {
        $this->patchProperties(['temperature' => 21.5], 999999999)->assertNotFound();

        Http::assertNothingSent();
    }

    public function test_a_user_without_the_update_permission_is_refused(): void
    {
        $outsider = $this->makeUser([AppPermission::DATA_SOURCES_READ]);

        $this->actingAs($outsider)
            ->patchJson("/api/V1/entities/{$this->entity->id}/properties", ['temperature' => 21.5])
            ->assertForbidden();

        Http::assertNothingSent();
    }

    // ----------------------------------------------------------------- NGSI-LD shaping

    public function test_a_simple_value_is_wrapped_as_an_ngsi_ld_property(): void
    {
        $this->patchProperties(['temperature' => 21.5])->assertOk();

        $this->assertSentAttributes([
            'temperature' => ['type' => 'Property', 'value' => 21.5],
        ]);
    }

    public function test_a_value_already_in_ngsi_ld_form_is_passed_through(): void
    {
        // "already NGSI-LD" is detected as: is_array AND has both 'value' and 'type'.
        $this->patchProperties([
            'status' => ['value' => 'open', 'type' => 'Property'],
        ])->assertOk();

        $this->assertSentAttributes([
            'status' => ['type' => 'Property', 'value' => 'open'],
        ]);
    }

    public function test_a_relationship_type_survives_the_round_trip(): void
    {
        $this->patchProperties([
            'refDevice' => ['value' => 'urn:ngsi-ld:Device:1', 'type' => 'Relationship'],
        ])->assertOk();

        $this->assertSentAttributes([
            'refDevice' => ['type' => 'Relationship', 'value' => 'urn:ngsi-ld:Device:1'],
        ]);
    }

    /**
     * An array that does NOT carry both 'value' and 'type' is treated as a plain value and wrapped,
     * array and all. Worth pinning: it means a caller who sends {"value": 1} without "type" gets a
     * nested value, not the property they expected.
     */
    public function test_an_array_missing_type_is_wrapped_rather_than_passed_through(): void
    {
        $this->patchProperties(['payload' => ['value' => 1]])->assertOk();

        $this->assertSentAttributes([
            'payload' => ['type' => 'Property', 'value' => ['value' => 1]],
        ]);
    }

    // ----------------------------------------------------------------- timestamps

    public function test_the_global_timestamp_is_applied_to_wrapped_attributes_only(): void
    {
        $this->patchProperties([
            'temperature' => 21.5,
            'status'      => ['value' => 'open', 'type' => 'Property'],
            'timestamp'   => '2026-01-01T00:00:00Z',
        ])->assertOk();

        $sent = $this->sentAttributes();

        // The wrapped attribute inherits the global timestamp...
        $this->assertSame('2026-01-01T00:00:00Z', $sent['temperature']['timestamp'] ?? null);
        // ...the one that arrived already in NGSI-LD form does NOT.
        $this->assertArrayNotHasKey('timestamp', $sent['status']);
        // And the global timestamp is never itself sent as an attribute.
        $this->assertArrayNotHasKey('timestamp', $sent);
    }

    public function test_a_per_attribute_timestamp_is_preserved(): void
    {
        $this->patchProperties([
            'temperature' => ['value' => 21.5, 'type' => 'Property', 'timestamp' => '2026-02-02T00:00:00Z'],
            'timestamp'   => '2026-01-01T00:00:00Z',
        ])->assertOk();

        $sent = $this->sentAttributes();
        $this->assertSame('2026-02-02T00:00:00Z', $sent['temperature']['timestamp']);
    }

    public function test_without_a_global_timestamp_wrapped_attributes_carry_none(): void
    {
        $this->patchProperties(['temperature' => 21.5])->assertOk();

        $this->assertArrayNotHasKey('timestamp', $this->sentAttributes()['temperature']);
    }

    // ----------------------------------------------------------------- geolocation

    public function test_geolocation_is_renamed_to_location_on_the_wire(): void
    {
        $point = ['type' => 'Point', 'coordinates' => [-5.66, 43.53]];

        $this->patchProperties(['geolocation' => $point])->assertOk();

        $sent = $this->sentAttributes();
        $this->assertArrayHasKey('location', $sent, 'geolocation must be sent as "location".');
        $this->assertArrayNotHasKey('geolocation', $sent);
        $this->assertSame($point, $sent['location']['value']);
    }

    /**
     * The response echoes the ORIGINAL request, so the caller sees "geolocation" back even though
     * "location" is what was stored. Pinned because it is a real asymmetry in the API contract.
     */
    public function test_the_response_echoes_the_unmodified_request(): void
    {
        $point = ['type' => 'Point', 'coordinates' => [-5.66, 43.53]];

        $response = $this->patchProperties(['geolocation' => $point, 'timestamp' => '2026-01-01T00:00:00Z']);

        $response->assertOk();
        $response->assertJson([
            'geolocation' => $point,
            'timestamp'   => '2026-01-01T00:00:00Z',
        ]);
        $this->assertArrayNotHasKey('location', $response->json());
    }

    /**
     * DEFECT, pinned as-is.
     *
     * UpdateEntityRequest declares `geolocation` as "nullable|array:type,coordinates", so
     * {"geolocation": null} passes validation. The controller then hands that null straight to
     *
     *     private function handleSmartSpotLocationUpdate(Entity $entity, array $geolocationValue)
     *
     * whose second parameter is a non-nullable array, so PHP raises
     *   TypeError: Argument #2 ($geolocationValue) must be of type array, null given
     * and the caller gets a 500 instead of a validation error or a cleared location.
     *
     * The consequence is that AetherLinkHelper::updateOnContextBroker's dedicated null-location
     * branch — the one that rewrites a null location to Point(0,0) — is UNREACHABLE through this
     * endpoint. Whoever fixes this should decide which of the two behaviours is intended
     * (reject the null, or clear the location) and change this test deliberately.
     *
     * Asserting 500 is not an endorsement; it records where the code is today so the refactor
     * cannot silently change it in a third direction.
     */
    public function test_a_null_geolocation_currently_causes_a_500(): void
    {
        $this->patchProperties(['geolocation' => null])->assertStatus(500);

        // The request dies before the broker is contacted.
        Http::assertNothingSent();
    }

    // ----------------------------------------------------------------- broker failure handling

    public function test_a_broker_error_list_is_returned_verbatim_with_its_status(): void
    {
        $this->fakeContextBroker(207, ['errors' => [['detail' => 'attribute rejected']], 'success' => []]);

        $response = $this->patchProperties(['temperature' => 21.5]);

        // 207 with a non-empty `errors` array means NOT updated, and the controller replays the
        // broker's own body and status back to the caller.
        $response->assertStatus(207);
        $response->assertJson(['errors' => [['detail' => 'attribute rejected']]]);
    }

    public function test_a_non_207_broker_status_is_passed_through(): void
    {
        $this->fakeContextBroker(502, ['message' => 'bad gateway']);

        $this->patchProperties(['temperature' => 21.5])->assertStatus(502);
    }

    /**
     * A transport failure is swallowed by AetherLinkHelper and reported as 500 with the exception
     * message as the body.
     */
    public function test_a_transport_failure_becomes_a_500(): void
    {
        $this->fakeContextBrokerTransportFailure('connection refused');

        $this->patchProperties(['temperature' => 21.5])->assertStatus(500);
    }

    // ----------------------------------------------------------------- unitCode side effect

    public function test_a_unit_code_updates_the_stored_property_units(): void
    {
        $this->makeStoredProperty('temperature', '20', 'CEL');

        $this->patchProperties([
            'temperature' => ['value' => 21.5, 'type' => 'Property', 'unitCode' => 'KEL'],
        ])->assertOk();

        $this->assertSame('KEL', $this->storedUnits('temperature'));
    }

    public function test_an_attribute_without_a_unit_code_leaves_the_units_alone(): void
    {
        $this->makeStoredProperty('temperature', '20', 'CEL');

        $this->patchProperties(['temperature' => 21.5])->assertOk();

        $this->assertSame('CEL', $this->storedUnits('temperature'));
    }

    /**
     * The units write is scoped by entity_id AND name, so another entity's identically named
     * property is untouched.
     */
    public function test_the_units_update_does_not_leak_to_another_entity(): void
    {
        $other = $this->makeEntity();
        $this->makeStoredProperty('temperature', '20', 'CEL');
        $this->makeStoredProperty('temperature', '20', 'CEL', $other);

        $this->patchProperties([
            'temperature' => ['value' => 21.5, 'type' => 'Property', 'unitCode' => 'KEL'],
        ])->assertOk();

        $this->assertSame('KEL', $this->storedUnits('temperature'));
        $this->assertSame('CEL', $this->storedUnits('temperature', $other));
    }

    // ----------------------------------------------------------------- Incident / AssetIntervention

    public function test_an_incident_status_cannot_be_changed_from_inside_an_asset_intervention(): void
    {
        $incident = $this->makeEntity('Incident');
        $this->putInAssetIntervention($incident);

        $response = $this->patchProperties(['status' => 'closed'], $incident->id);

        $response->assertStatus(422);
        $this->assertSame('Incident status is governed by its AssetIntervention', $response->getContent());
        Http::assertNothingSent();
    }

    public function test_an_incident_outside_an_intervention_can_change_status(): void
    {
        $incident = $this->makeEntity('Incident');

        $this->patchProperties(['status' => 'closed'], $incident->id)->assertOk();

        $this->assertSentAttributes(['status' => ['type' => 'Property', 'value' => 'closed']]);
    }

    /**
     * The intervention guard is keyed on the `status` attribute only: any other attribute of an
     * incident inside an intervention updates normally.
     */
    public function test_a_non_status_attribute_of_a_governed_incident_is_still_updatable(): void
    {
        $incident = $this->makeEntity('Incident');
        $this->putInAssetIntervention($incident);

        $this->patchProperties(['description' => 'still editable'], $incident->id)->assertOk();
    }

    /**
     * The guard is also keyed on the datamodel: an entity in an AssetIntervention group that is
     * not an Incident is not governed by it.
     */
    public function test_the_intervention_guard_only_applies_to_incidents(): void
    {
        $device = $this->makeEntity('Device');
        $this->putInAssetIntervention($device);

        $this->patchProperties(['status' => 'closed'], $device->id)->assertOk();
    }

    // ----------------------------------------------------------------- helpers

    private function patchProperties(array $payload, ?int $entityId = null)
    {
        if (!$this->brokerFaked) {
            $this->fakeContextBroker();
        }

        $id = $entityId ?? $this->entity->id;

        return $this->actingAs($this->admin)->patchJson("/api/V1/entities/{$id}/properties", $payload);
    }

    /** Fake the context broker. Default: a 207 batch response with no errors, i.e. success. */
    private function fakeContextBroker(int $status = 207, ?array $body = null): void
    {
        $this->brokerFaked = true;

        Http::fake([
            self::AETHER_UPDATE_URL => Http::response($body ?? ['errors' => [], 'success' => []], $status),
        ]);
    }

    /** Install a stub that throws, to characterise a transport failure. */
    private function fakeContextBrokerTransportFailure(string $message): void
    {
        $this->brokerFaked = true;

        Http::fake([self::AETHER_UPDATE_URL => fn () => throw new \RuntimeException($message)]);
    }

    /** The `attributes` map of the single entity in the batch that was actually sent. */
    private function sentAttributes(): array
    {
        $attributes = null;

        Http::assertSent(function (ClientRequest $request) use (&$attributes) {
            if (!str_contains($request->url(), '/context-broker/entities/update')) {
                return false;
            }
            $body = json_decode($request->body(), true);
            $attributes = $body['entities'][0]['attributes'] ?? [];

            return true;
        });

        $this->assertIsArray($attributes, 'No update request reached the context broker.');

        return $attributes;
    }

    private function assertSentAttributes(array $expected): void
    {
        $this->assertSame($expected, $this->sentAttributes());
    }

    private function makeUser(array $permissions): User
    {
        // organizations.admin is NOT NULL and references a user, so the user must exist first.
        $user = User::create([
            'name'               => '[TEST] User',
            'email'              => 'user.' . Str::random(8) . '@characterization.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . Str::random(8),
        ]);

        $org = Organization::create(['name' => '[TEST] Org ' . Str::random(6), 'admin' => $user->id]);

        $user->organization_id = $org->id;
        $user->save();

        $user->givePermissionTo(array_map(fn (AppPermission $p) => $p->value, $permissions));

        return $user;
    }

    private function makeEntity(string $datamodel = 'Device'): Entity
    {
        return Entity::create([
            'urn'       => 'urn:ngsi-ld:' . $datamodel . ':' . Str::random(10),
            'datamodel' => $datamodel,
            'tenant'    => 'platform',
            'scope'     => '/',
        ]);
    }

    private function putInAssetIntervention(Entity $entity): EntityGroup
    {
        // chk_linked_entity_columns requires entity_id and type to be both NULL or both set, so a
        // typed group must point at a linked entity.
        $group = EntityGroup::create([
            'name'      => '[TEST] Intervention',
            'user_id'   => $this->admin->id,
            'type'      => 'AssetIntervention',
            'entity_id' => $this->makeEntity('AssetIntervention')->id,
        ]);

        $group->entities()->attach($entity->id);

        return $group;
    }

    private function makeStoredProperty(string $name, string $value, string $units, ?Entity $entity = null): void
    {
        $entity ??= $this->entity;

        EntityProperty::create([
            'urn'       => $entity->urn,
            'tenant'    => $entity->tenant,
            'scope'     => $entity->scope,
            'entity_id' => $entity->id,
            'name'      => $name,
            'value'     => $value,
            'units'     => $units,
            // NOT NULL in the realtime schema.
            'timestamp' => '2026-01-01 00:00:00',
        ]);
    }

    private function storedUnits(string $name, ?Entity $entity = null): ?string
    {
        $entity ??= $this->entity;

        return DB::connection('pgsql_realtime')
            ->table('entity_properties')
            ->where('entity_id', $entity->id)
            ->where('name', $name)
            ->value('units');
    }
}
