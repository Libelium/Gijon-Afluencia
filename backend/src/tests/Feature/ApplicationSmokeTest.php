<?php

namespace Tests\Feature;

use Illuminate\Support\Facades\Route;
use Tests\TestCase;

/**
 * Replaces the Laravel skeleton's tests/Feature/ExampleTest.php (GDTIS-PT01-FUN-018).
 *
 * That template test asserted `GET /` returns 200. It never could: RouteServiceProvider::boot()
 * registers ONLY routes/api.php (under the `api` prefix) and never calls $this->routes() for
 * routes/web.php, so the `Route::get('/')` declared there is not registered at all — and the
 * `welcome` view it would render does not exist either. The request 404s, which is the correct
 * behaviour for an API-only service and was simply the wrong assertion.
 *
 * What is worth smoke-testing instead is that the application boots, that the API surface is
 * mounted where the clients expect it, and that the authentication wall is actually in front of
 * it. This needs no database.
 */
class ApplicationSmokeTest extends TestCase
{
    public function test_the_application_boots(): void
    {
        $this->assertTrue($this->app->isBooted(), 'The application container failed to boot.');
        $this->assertSame('testing', $this->app->environment());
    }

    /**
     * Pins the fact that routes/web.php is dead code: RouteServiceProvider only loads
     * routes/api.php. If someone later wires web.php up, this test tells them the file has been
     * unreachable and its contents (a `welcome` view that does not exist) need reviewing.
     */
    public function test_no_web_routes_are_registered(): void
    {
        $this->assertFileExists(
            base_path('routes/web.php'),
            'routes/web.php was deleted — remove this test with it.'
        );

        // sanctum and laravel-ignition register their own routes from their service providers;
        // everything the application itself declares must live under api/.
        $vendorPrefixes = ['sanctum/', '_ignition/'];

        $ownNonApiRoutes = array_values(array_filter(
            Route::getRoutes()->getRoutes(),
            function ($route) use ($vendorPrefixes) {
                $uri = $route->uri();
                if (str_starts_with($uri, 'api/') || $uri === 'api') {
                    return false;
                }
                foreach ($vendorPrefixes as $prefix) {
                    if (str_starts_with($uri, $prefix)) {
                        return false;
                    }
                }

                return true;
            }
        ));

        $this->assertSame(
            [],
            array_map(fn ($r) => $r->methods()[0] . ' /' . $r->uri(), $ownNonApiRoutes),
            'A first-party route outside the api/ prefix appeared. RouteServiceProvider only '
                . 'groups routes/api.php, so this is either a new provider or a surprise.'
        );

        // The `/` route declared in routes/web.php is specifically not reachable.
        $this->get('/')->assertNotFound();
    }

    /** The V1 API is mounted where every client expects it. */
    public function test_the_v1_api_is_mounted(): void
    {
        $uris = array_map(fn ($r) => $r->uri(), Route::getRoutes()->getRoutes());

        // La sesion vive entera en Keycloak: ni el inicio de sesion ni el refresco pasan por la API.
        $this->assertNotContains('api/V1/login', $uris, 'The password-grant login endpoint came back.');
        $this->assertNotContains('api/V1/refresh-token', $uris, 'The token refresh endpoint came back.');
        $this->assertContains('api/V1/entities/{id}/properties', $uris, 'The entity properties endpoint moved.');
        $this->assertContains('api/V1/dashboards/from-json', $uris, 'The dashboard JSON endpoint moved.');
    }

    /**
     * The authentication wall is in front of the protected surface. A regression here would expose
     * the whole management API, so it is worth one cheap assertion.
     *
     * @dataProvider protectedEndpointProvider
     */
    public function test_protected_endpoints_reject_anonymous_callers(string $method, string $uri): void
    {
        $response = $this->json($method, $uri);

        $this->assertContains(
            $response->status(),
            [401, 403],
            "{$method} {$uri} answered {$response->status()} to an anonymous caller; expected 401/403."
        );
    }

    public static function protectedEndpointProvider(): array
    {
        return [
            'current user'      => ['GET', '/api/V1/user'],
            'entity properties' => ['PATCH', '/api/V1/entities/1/properties'],
            'dashboard listing' => ['POST', '/api/V1/dashboards/paginate'],
            'create from json'  => ['POST', '/api/V1/dashboards/from-json'],
        ];
    }
}
