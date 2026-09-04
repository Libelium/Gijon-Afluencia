<?php

namespace Tests\Feature\Characterization;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Enums\UserStatus;
use App\Models\Dashboard;
use App\Models\Organization;
use App\Models\Panel;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * CHARACTERIZATION TESTS — DashboardContentService::apply.
 *
 * It is the shared engine behind both JSON endpoints:
 *
 *   POST /api/V1/dashboards/from-json        -> createFromJson  (batch, resolves "@key" refs)
 *   POST /api/V1/dashboards/{id}/from-json   -> updateFromJson  (reconciles one dashboard)
 *
 * These tests drive it through those two routes rather than calling it directly: a test bound
 * to the HTTP contract survives the code being reshaped, which is what happened when this
 * logic moved out of the controller.
 *
 * These tests describe what the code does TODAY, sharp edges included. Each surprising behaviour
 * is called out in a comment. They are a regression net, not a specification.
 *
 * The pure helpers this method delegates to (remapDashboardRefs, stripSerieIds) are covered
 * separately and much faster in tests/Unit/Dashboard/DashboardJsonHelpersTest.php.
 *
 * Panels are created with `series: []` throughout, which keeps SerieRepository out of the picture
 * and isolates the panel/layout reconciliation this method is actually responsible for. The
 * serie-id reconciliation branches are listed as NOT covered in the class docblock below.
 *
 * NOT COVERED HERE (deliberate, documented gaps):
 *   - the serie branches: dropping foreign serie ids on an existing panel, and stripping all
 *     serie ids on a new one. They need a valid SerieRepository payload (entity/measure wiring)
 *     which pulls in the IoT schema.
 *   - annotations (AnnotationRepository) — same reason.
 *   - PanelRepository::validatePanel rejection paths.
 *   - concurrent/partial-failure rollback of the wrapping DB::transaction.
 *
 * @see \App\Services\Dashboards\DashboardContentService::apply
 */
class DashboardApplyContentTest extends TestCase
{
    use DatabaseTransactions;

    private User $admin;

    protected function setUp(): void
    {
        parent::setUp();

        $this->admin = $this->makeAdmin();
    }

    // ----------------------------------------------------------------- guards

    public function test_only_custom_dashboards_can_be_updated_from_json(): void
    {
        $dashboard = $this->makeDashboard(['type' => 'Template']);

        $this->update($dashboard, ['panels' => []])
            ->assertStatus(422)
            ->assertJson(['message' => 'Only custom dashboards can be updated from JSON']);
    }

    public function test_the_panels_key_must_be_present(): void
    {
        // 'panels' => 'present|array' — absent is a validation error, empty array is fine.
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, ['name' => 'No panels key'])->assertStatus(422);
    }

    public function test_an_empty_panels_array_is_accepted_and_clears_the_dashboard(): void
    {
        $dashboard = $this->makeDashboard();
        $panel = $this->makePanel($dashboard);

        $this->update($dashboard, ['panels' => []])->assertOk();

        $this->assertDatabaseMissing('panels', ['id' => $panel->id]);
    }

    public function test_creating_from_json_rejects_a_non_custom_type(): void
    {
        $this->create([
            'name' => 'Typed dashboard',
            'timezone' => 'UTC',
            'type' => 'Template',
            'panels' => [],
        ])->assertStatus(422)
          ->assertJson(['message' => 'Only custom dashboards can be created from JSON']);
    }

    public function test_creating_from_json_with_an_empty_batch_is_rejected(): void
    {
        $this->create(['dashboards' => []])
            ->assertStatus(422)
            ->assertJson(['message' => 'No dashboards to create']);
    }

    // ----------------------------------------------------------------- panel reconciliation

    public function test_a_panel_without_an_id_is_created(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, ['panels' => [$this->panelPayload()]])->assertOk();

        $this->assertSame(1, $dashboard->panels()->count());
    }

    public function test_a_panel_with_an_existing_id_is_updated_in_place(): void
    {
        $dashboard = $this->makeDashboard();
        $panel = $this->makePanel($dashboard, 'Before');

        $this->update($dashboard, [
            'panels' => [$this->panelPayload(['id' => $panel->id, 'title' => 'After'])],
        ])->assertOk();

        $this->assertSame(1, $dashboard->panels()->count());
        $this->assertSame('After', $panel->fresh()->title, 'The panel should have been updated, not replaced.');
    }

    public function test_a_panel_missing_from_the_payload_is_deleted(): void
    {
        $dashboard = $this->makeDashboard();
        $kept = $this->makePanel($dashboard, 'Kept');
        $dropped = $this->makePanel($dashboard, 'Dropped');

        $this->update($dashboard, [
            'panels' => [$this->panelPayload(['id' => $kept->id, 'title' => 'Kept'])],
        ])->assertOk();

        $this->assertDatabaseHas('panels', ['id' => $kept->id]);
        $this->assertDatabaseMissing('panels', ['id' => $dropped->id]);
    }

    /**
     * "Existing" is `is_numeric($id) && $id > 0 && the panel belongs to THIS dashboard`. A numeric
     * id that belongs to a different dashboard therefore counts as NEW: a panel is created here and
     * the other dashboard's panel is left untouched. Pinned because it is the guard that stops one
     * dashboard's JSON from stealing another's panels.
     */
    public function test_a_panel_id_from_another_dashboard_creates_a_new_panel(): void
    {
        $mine = $this->makeDashboard();
        $theirs = $this->makeDashboard();
        $foreignPanel = $this->makePanel($theirs, 'Theirs');

        $this->update($mine, [
            'panels' => [$this->panelPayload(['id' => $foreignPanel->id, 'title' => 'Mine now'])],
        ])->assertOk();

        $this->assertSame('Theirs', $foreignPanel->fresh()->title, "Another dashboard's panel was modified.");
        $this->assertSame(1, $mine->panels()->count());
        $this->assertNotSame($foreignPanel->id, $mine->panels()->first()->id);
    }

    /** A negative or zero id is a temporary client-side id, so the panel is created. */
    public function test_a_negative_id_is_treated_as_a_new_panel(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [$this->panelPayload(['id' => -1])],
        ])->assertOk();

        $this->assertSame(1, $dashboard->panels()->count());
        $this->assertGreaterThan(0, $dashboard->panels()->first()->id);
    }

    public function test_a_non_numeric_id_is_treated_as_a_new_panel(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [$this->panelPayload(['id' => 'tmp-a'])],
        ])->assertOk();

        $this->assertSame(1, $dashboard->panels()->count());
    }

    // ----------------------------------------------------------------- layout reconciliation

    public function test_a_temporary_panel_id_is_rewired_in_the_layout(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [$this->panelPayload(['id' => 'tmp-a'])],
            'layout' => ['lg' => [['i' => 'tmp-a', 'x' => 0, 'y' => 0, 'w' => 6, 'h' => 4]]],
        ])->assertOk();

        $realId = (string) $dashboard->panels()->first()->id;
        $layout = $dashboard->fresh()->layout;

        $this->assertSame($realId, $layout['lg'][0]['i'], 'The temporary id was not remapped.');
        // The rest of the grid item is preserved verbatim.
        $this->assertSame(6, $layout['lg'][0]['w']);
        $this->assertSame(4, $layout['lg'][0]['h']);
    }

    public function test_a_layout_item_referencing_a_deleted_panel_is_dropped(): void
    {
        $dashboard = $this->makeDashboard();
        $panel = $this->makePanel($dashboard);

        $this->update($dashboard, [
            'panels' => [],
            'layout' => ['lg' => [['i' => (string) $panel->id, 'x' => 0, 'y' => 0, 'w' => 6, 'h' => 4]]],
        ])->assertOk();

        $this->assertSame([], $dashboard->fresh()->layout['lg']);
    }

    /**
     * A created panel the layout does not position is auto-placed below everything else, full
     * width, and — worth noting — `static: true`, so it cannot be dragged until someone edits it.
     */
    public function test_a_created_panel_absent_from_the_layout_is_auto_placed(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [$this->panelPayload()],
            'layout' => ['lg' => []],
        ])->assertOk();

        $realId = (string) $dashboard->panels()->first()->id;
        $item = $dashboard->fresh()->layout['lg'][0];

        $this->assertSame(
            ['i' => $realId, 'x' => 0, 'y' => 0, 'w' => 12, 'h' => 10, 'static' => true],
            $item
        );
    }

    public function test_auto_placement_stacks_below_the_lowest_existing_item(): void
    {
        $dashboard = $this->makeDashboard();
        $existing = $this->makePanel($dashboard);

        $this->update($dashboard, [
            'panels' => [
                $this->panelPayload(['id' => $existing->id]),
                $this->panelPayload(['title' => 'New one']),
            ],
            // The existing item occupies y=3..3+7=10, so the new panel must land at y=10.
            'layout' => ['lg' => [['i' => (string) $existing->id, 'x' => 0, 'y' => 3, 'w' => 12, 'h' => 7]]],
        ])->assertOk();

        $layout = $dashboard->fresh()->layout['lg'];
        $this->assertCount(2, $layout);
        $this->assertSame(10, $layout[1]['y'], 'The new panel was not stacked below the existing one.');
    }

    /**
     * A panel embedded as a child of a group panel's chart config renders inside its parent, so it
     * must never get its own top-level grid item.
     */
    public function test_a_group_child_panel_is_not_auto_placed(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [
                // The child, carrying a temporary id...
                $this->panelPayload(['id' => 'child-1', 'title' => 'Child']),
                // ...and the group that declares it as a child.
                $this->panelPayload([
                    'id' => 'group-1',
                    'title' => 'Group',
                    'chart' => [
                        'title' => 'Group chart',
                        'type' => 'group',
                        'config' => ['panels' => [['id' => 'child-1']]],
                    ],
                ]),
            ],
            'layout' => ['lg' => []],
        ])->assertOk();

        $this->assertSame(2, $dashboard->panels()->count(), 'Both panels should exist as rows.');

        $layout = $dashboard->fresh()->layout['lg'];
        $this->assertCount(1, $layout, 'Only the group should be auto-placed, not its child.');

        $groupId = (string) $dashboard->panels()->where('title', 'Group')->first()->id;
        $this->assertSame($groupId, $layout[0]['i']);
    }

    /**
     * Sharp edge: `lg` is force-created when missing, but the other four breakpoints are only
     * touched if the payload already declares them. A dashboard whose layout has no `md` key comes
     * back with no `md` key at all.
     */
    public function test_only_the_lg_breakpoint_is_created_when_missing(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [$this->panelPayload()],
            'layout' => [],
        ])->assertOk();

        $layout = $dashboard->fresh()->layout;

        $this->assertArrayHasKey('lg', $layout);
        $this->assertCount(1, $layout['lg'], 'The new panel should be auto-placed into lg.');
        $this->assertArrayNotHasKey('md', $layout);
    }

    public function test_declared_breakpoints_all_receive_the_created_panel(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [$this->panelPayload()],
            'layout' => ['lg' => [], 'md' => [], 'sm' => []],
        ])->assertOk();

        $layout = $dashboard->fresh()->layout;

        foreach (['lg', 'md', 'sm'] as $breakpoint) {
            $this->assertCount(1, $layout[$breakpoint], "{$breakpoint} did not receive the new panel.");
        }
    }

    /** A non-array layout value is coerced to an empty layout rather than blowing up. */
    public function test_a_non_array_layout_is_ignored(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, [
            'panels' => [],
            'layout' => null,
        ])->assertOk();

        // layout => null means `$data['layout'] ?? $dashboard->layout` keeps the current layout.
        $this->assertIsArray($dashboard->fresh()->layout);
    }

    // ----------------------------------------------------------------- scalar field fallbacks

    public function test_omitted_scalar_fields_keep_their_current_value(): void
    {
        $dashboard = $this->makeDashboard([
            'name' => 'Original name',
            'description' => 'Original description',
            'timezone' => 'Europe/Madrid',
        ]);

        $this->update($dashboard, ['panels' => []])->assertOk();

        $fresh = $dashboard->fresh();
        $this->assertSame('Original name', $fresh->name);
        $this->assertSame('Original description', $fresh->description);
        $this->assertSame('Europe/Madrid', $fresh->timezone);
    }

    public function test_supplied_scalar_fields_are_applied(): void
    {
        $dashboard = $this->makeDashboard(['name' => 'Original name']);

        $this->update($dashboard, [
            'panels' => [],
            'name' => 'New name',
            'description' => 'New description',
            'timezone' => 'UTC',
        ])->assertOk();

        $fresh = $dashboard->fresh();
        $this->assertSame('New name', $fresh->name);
        $this->assertSame('New description', $fresh->description);
        $this->assertSame('UTC', $fresh->timezone);
    }

    /**
     * `hidden` uses array_key_exists, so an explicit null becomes FALSE (a (bool) cast of null),
     * unlike name/description which use `??` and keep the old value. Pinned because the two
     * behaviours differ in the same call.
     */
    public function test_an_explicit_null_hidden_becomes_false(): void
    {
        $dashboard = $this->makeDashboard(['hidden' => true]);

        $this->update($dashboard, ['panels' => [], 'hidden' => null])->assertOk();

        $this->assertFalse((bool) $dashboard->fresh()->hidden);
    }

    public function test_hidden_can_be_set_and_cleared(): void
    {
        $dashboard = $this->makeDashboard(['hidden' => false]);

        $this->update($dashboard, ['panels' => [], 'hidden' => true])->assertOk();
        $this->assertTrue((bool) $dashboard->fresh()->hidden);

        $this->update($dashboard, ['panels' => [], 'hidden' => false])->assertOk();
        $this->assertFalse((bool) $dashboard->fresh()->hidden);
    }

    /**
     * `dateRange` is only written when present AND not null; a null leaves the stored value alone.
     * It is stored json_encode'd by this method.
     */
    public function test_a_null_date_range_leaves_the_stored_one_alone(): void
    {
        $dashboard = $this->makeDashboard();

        $this->update($dashboard, ['panels' => [], 'dateRange' => ['from' => 'now-1d', 'to' => 'now']])->assertOk();
        $afterSet = $dashboard->fresh()->date_range;
        $this->assertNotNull($afterSet);

        $this->update($dashboard, ['panels' => [], 'dateRange' => null])->assertOk();
        $this->assertEquals($afterSet, $dashboard->fresh()->date_range, 'A null dateRange must not clear it.');
    }

    // ----------------------------------------------------------------- batch creation + @key refs

    public function test_a_batch_creates_every_dashboard(): void
    {
        $response = $this->create([
            'dashboards' => [
                ['key' => 'air', 'name' => 'Air quality', 'timezone' => 'UTC', 'panels' => []],
                ['key' => 'traffic', 'name' => 'Traffic', 'timezone' => 'UTC', 'panels' => []],
            ],
        ]);

        $response->assertStatus(201);
        $this->assertCount(2, $response->json('data'));

        $this->assertDatabaseHas('dashboards', ['name' => 'Air quality', 'type' => 'Custom']);
        $this->assertDatabaseHas('dashboards', ['name' => 'Traffic', 'type' => 'Custom']);
    }

    /**
     * The point of the batch endpoint: a chart config can reference a sibling dashboard that does
     * not exist yet via "@key", and it is resolved to the real id.
     */
    public function test_an_at_key_reference_resolves_to_a_sibling_dashboards_id(): void
    {
        $response = $this->create([
            'dashboards' => [
                ['key' => 'target', 'name' => 'Target dashboard', 'timezone' => 'UTC', 'panels' => []],
                [
                    'name' => 'Source dashboard',
                    'timezone' => 'UTC',
                    'panels' => [
                        $this->panelPayload([
                            'chart' => [
                                'title' => 'Link chart',
                                'type' => 'link',
                                'config' => ['links' => [['dashboardId' => '@target']]],
                            ],
                        ]),
                    ],
                ],
            ],
        ]);

        $response->assertStatus(201);

        $targetId = Dashboard::where('name', 'Target dashboard')->value('id');
        $source = Dashboard::where('name', 'Source dashboard')->first();
        $chart = $source->panels()->first()->chart;
        $chart = is_string($chart) ? json_decode($chart, true) : $chart;

        $this->assertSame($targetId, $chart['config']['links'][0]['dashboardId']);
    }

    public function test_an_unresolvable_at_key_is_left_as_a_literal(): void
    {
        $response = $this->create([
            'name' => 'Lonely dashboard',
            'timezone' => 'UTC',
            'panels' => [
                $this->panelPayload([
                    'chart' => [
                        'title' => 'Link chart',
                        'type' => 'link',
                        'config' => ['links' => [['dashboardId' => '@nobody']]],
                    ],
                ]),
            ],
        ]);

        $response->assertStatus(201);

        $chart = Dashboard::where('name', 'Lonely dashboard')->first()->panels()->first()->chart;
        $chart = is_string($chart) ? json_decode($chart, true) : $chart;

        $this->assertSame('@nobody', $chart['config']['links'][0]['dashboardId']);
    }

    public function test_a_single_dashboard_object_is_accepted_without_the_dashboards_wrapper(): void
    {
        $this->create([
            'name' => 'Solo dashboard',
            'timezone' => 'UTC',
            'panels' => [$this->panelPayload()],
        ])->assertStatus(201);

        $dashboard = Dashboard::where('name', 'Solo dashboard')->first();
        $this->assertNotNull($dashboard);
        $this->assertSame('Custom', $dashboard->type);
        $this->assertSame(1, $dashboard->panels()->count());
    }

    /** A batch is atomic: one invalid spec rolls the whole thing back. */
    public function test_an_invalid_spec_aborts_the_whole_batch(): void
    {
        $this->create([
            'dashboards' => [
                ['name' => 'Valid one', 'timezone' => 'UTC', 'panels' => []],
                // 'name' is required|min:3 and 'panels' must be present.
                ['name' => 'x', 'timezone' => 'UTC'],
            ],
        ])->assertStatus(422);

        $this->assertDatabaseMissing('dashboards', ['name' => 'Valid one']);
    }

    // ----------------------------------------------------------------- helpers

    private function update(Dashboard $dashboard, array $payload)
    {
        return $this->actingAs($this->admin)
            ->postJson("/api/V1/dashboards/{$dashboard->id}/from-json", $payload);
    }

    private function create(array $payload)
    {
        return $this->actingAs($this->admin)->postJson('/api/V1/dashboards/from-json', $payload);
    }

    /** A minimal panel payload that satisfies the inline Validator and PanelRepository. */
    private function panelPayload(array $overrides = []): array
    {
        return array_merge([
            'title' => 'A panel',
            'chart' => [
                'title' => 'A chart',
                'type'  => 'echarts_line',
            ],
            'series' => [],
            'annotations' => [],
        ], $overrides);
    }

    private function makeAdmin(): User
    {
        // organizations.admin is NOT NULL and points at a user, so the user comes first.
        $user = User::create([
            'name'               => '[TEST] Dashboard admin',
            'email'              => 'dash.' . Str::random(8) . '@characterization.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . Str::random(8),
        ]);

        $org = Organization::create(['name' => '[TEST] Org ' . Str::random(6), 'admin' => $user->id]);
        $user->organization_id = $org->id;
        $user->save();

        // DashboardPolicy does NOT short-circuit on APPLICATION_ADMIN the way EntityPolicy does:
        // create() requires DASHBOARDS_UPDATE + ANALYTICS_READ, and update() additionally requires
        // a per-resource UPDATE grant on the dashboard itself (see makeDashboard()).
        $user->givePermissionTo([
            AppPermission::APPLICATION_ADMIN->value,
            AppPermission::DASHBOARDS_UPDATE->value,
            AppPermission::DASHBOARDS_READ->value,
            AppPermission::ANALYTICS_READ->value,
        ]);

        return $user;
    }

    private function makeDashboard(array $attributes = []): Dashboard
    {
        $dashboard = Dashboard::create(array_merge([
            'name'     => '[TEST] Dashboard ' . Str::random(6),
            'type'     => 'Custom',
            'timezone' => 'UTC',
            'user_id'  => $this->admin->id,
            'layout'   => ['lg' => [], 'md' => [], 'sm' => [], 'xs' => [], 'xxs' => []],
        ], $attributes));

        // Replicate what DashboardController::store does: the owner gets resource permissions,
        // without which DashboardPolicy::update denies even the creator.
        $this->admin->giveResourcePermissionsTo(
            AppResourcePermission::defaultPermissions(), $dashboard, true
        );

        return $dashboard;
    }

    private function makePanel(Dashboard $dashboard, string $title = 'Existing panel'): Panel
    {
        return Panel::create([
            'title'        => $title,
            'chart'        => ['title' => 'A chart', 'type' => 'echarts_line'],
            'dashboard_id' => $dashboard->id,
        ]);
    }
}
