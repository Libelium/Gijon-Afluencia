<?php

namespace App\Http\V1\Controllers;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Enums\UserStatus;
use App\Helpers\UserLocaleSyncHelper;
use App\Models\Organization;
use App\Models\Preference;
use App\Models\Preferencable;
use App\Models\User;
use App\Services\UserDeletion\UserDeletionService;
use App\Traits\KeycloakHelper;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpKernel\Exception\HttpException;

/**
 * Users of an organization, as its administrator sees them: list, create, enable or disable,
 * send the password e-mail and delete. Keycloak holds the credentials; the local row holds the
 * organization, the permissions and the preferences, so every write keeps both in step.
 *
 * Only the organization's administrator and the application administrator get here. The
 * personal data travels in clear because the caller is entitled to it; hiding it on screen is
 * the interface's job (it is masked by default).
 */
class OrganizationUserController extends Controller
{
    use KeycloakHelper;

    public function __construct(
        private readonly UserDeletionService $deletionService
    ) {}

    public function index(int $id): Response
    {
        $organization = Organization::findOrFail($id);
        $this->authorizeManagement($organization);

        $users = $organization->users()
            ->with('roles:id,name')
            ->where(fn ($query) => $query->whereNull('status')->orWhere('status', '!=', UserStatus::Deleted->value))
            ->orderBy('name')
            ->get();

        $mfa = $this->mfaByUser($users->pluck('id')->all());

        return response($users->map(fn (User $user) => $this->present($user, $organization, $mfa))->values(), 200);
    }

    public function store(int $id, Request $request): Response
    {
        $organization = Organization::findOrFail($id);
        $this->authorizeManagement($organization);

        $data = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|email:rfc|max:255',
        ]);
        $email = strtolower($data['email']);

        // Case-insensitive: older rows may keep the capitals they were created with.
        if (User::whereRaw('lower(email) = ?', [$email])->exists()) {
            return response(['error' => 'A user with this e-mail already exists'], 409);
        }

        try {
            $keycloakId = $this->createKeycloakUser($data['name'], $email);
        } catch (HttpException $e) {
            return response(['error' => $e->getMessage()], $e->getStatusCode() === 409 ? 409 : 502);
        }

        $user = User::create([
            'name' => $data['name'],
            'email' => $email,
            'enabled' => true,
            'keycloak_client_id' => $keycloakId,
            'organization_id' => $organization->id,
            'created_by' => Auth::id(),
            'status' => UserStatus::Active,
        ]);

        // Same grants a self-registered user gets: its own record, also to the organization
        // administrator so that it can manage it from here.
        $user->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $user, true);

        try {
            (new UserLocaleSyncHelper())->syncUserLocale($user);
        } catch (\Throwable $e) {
            Log::warning('organization.user.locale_sync_failed', ['user_id' => $user->id, 'error' => $e->getMessage()]);
        }

        // The account is created with a random password nobody knows: the e-mail lets the person
        // choose theirs. A failure is reported, not fatal, since it can be resent from the list.
        $invited = $this->sendKeycloakResetPasswordEmail($keycloakId);

        return response([
            'user' => $this->present($user->load('roles:id,name'), $organization, []),
            'invitationSent' => $invited,
        ], 201);
    }

    public function setEnabled(int $id, int $userId, Request $request): Response
    {
        [$organization, $user] = $this->resolve($id, $userId);

        $enabled = $request->validate(['enabled' => 'required|boolean'])['enabled'];

        if (!$enabled && $user->id === Auth::id()) {
            return response(['error' => 'You cannot disable your own account'], 422);
        }

        $keycloakId = $this->resolveKeycloakUserId($user);
        $synced = $keycloakId && ($enabled ? $this->enableUser($keycloakId) : $this->disableUser($keycloakId));

        if (!$synced) {
            return response(['error' => 'The account could not be updated in Keycloak'], 502);
        }

        $user->enabled = $enabled;
        $user->status = $enabled ? UserStatus::Active : UserStatus::Suspended;
        $user->save();

        return response($this->present($user->load('roles:id,name'), $organization, $this->mfaByUser([$user->id])), 200);
    }

    public function sendPasswordEmail(int $id, int $userId): Response
    {
        [, $user] = $this->resolve($id, $userId);

        $keycloakId = $this->resolveKeycloakUserId($user);

        if (!$keycloakId || !$this->sendKeycloakResetPasswordEmail($keycloakId)) {
            return response(['error' => 'The e-mail could not be sent'], 502);
        }

        return response(['success' => true], 200);
    }

    public function destroy(int $id, int $userId): Response
    {
        [$organization, $user] = $this->resolve($id, $userId);

        if ($user->id === Auth::id()) {
            return response(['error' => 'You cannot delete your own account'], 422);
        }

        if ($user->id === $organization->admin) {
            return response(['error' => 'The organization administrator cannot be deleted'], 422);
        }

        // The resolved id, so that a seeded 'pending' does not leave the Keycloak account behind.
        $this->resolveKeycloakUserId($user);
        $this->deletionService->deleteCompletely($user);

        return response('', 204);
    }

    private function authorizeManagement(Organization $organization): void
    {
        $caller = Auth::user();

        $allowed = $caller->can(AppPermission::APPLICATION_ADMIN->value)
            || ($caller->organization_id === $organization->id && $caller->isOrganizationAdmin());

        if (!$allowed) {
            abort(403, 'Only the organization administrator can manage its users');
        }
    }

    /** @return array{0: Organization, 1: User} */
    private function resolve(int $organizationId, int $userId): array
    {
        $organization = Organization::findOrFail($organizationId);
        $this->authorizeManagement($organization);

        $user = User::where('id', $userId)->where('organization_id', $organization->id)->firstOrFail();

        return [$organization, $user];
    }

    /** @return array<int, bool> */
    private function mfaByUser(array $userIds): array
    {
        $preference = Preference::where('name', 'activeMFA')->first();

        if (!$preference || !$userIds) {
            return [];
        }

        return Preferencable::where('preference_id', $preference->id)
            ->whereIn('user_id', $userIds)
            ->pluck('value', 'user_id')
            ->map(fn ($value) => $value === 'true')
            ->all();
    }

    private function present(User $user, Organization $organization, array $mfa): array
    {
        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'enabled' => (bool) $user->enabled,
            'status' => $user->status?->value ?? UserStatus::Active->value,
            'isOrganizationAdmin' => $user->id === $organization->admin,
            'roles' => $user->roles->pluck('name')->values(),
            'mfa' => $mfa[$user->id] ?? false,
            'lastActivity' => $user->last_activity,
            'createdAt' => $user->created_at?->format('Y-m-d H:i:s'),
        ];
    }
}
