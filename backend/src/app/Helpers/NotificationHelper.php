<?php

namespace App\Helpers;

use App\Helpers\Entities\RealtimeEntityResourcesHelper;
use App\Models\EntityGroup;
use App\Models\Realtime\EntityProperty;
use App\Models\Realtime\UserNotification;
use App\Services\PushNotifications\PushNotificationDispatcher;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class NotificationHelper
{
    /** Create a notification for a user. No-ops if $userId is not positive. */
    public static function push(int $userId, string $title, string $subtitle = '', array $params = [], string $type = 'light-info', string $icon = 'tabler-bell'): void
    {
        if ($userId <= 0) {
            return;
        }

        UserNotification::create([
            'user_id' => $userId,
            'data' => [
                'Title' => $title,
                'Subtitle' => $subtitle,
                'params' => (object) $params,
                'type' => $type,
                'icon' => $icon,
            ],
            'read' => false,
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        // Second channel: the same notification pushed to the user's phones. Best-effort by design —
        // a failed push must never break the state change that produced it.
        try {
            app(PushNotificationDispatcher::class)->dispatch($userId, $title, $subtitle, $params);
        } catch (\Throwable $e) {
            Log::warning('[push-notifications] dispatch failed: ' . $e->getMessage());
        }
    }

    /** Read a single incident attribute value from the local entity_properties mirror. */
    public static function incidentAttr(int $entityId, string $name): ?string
    {
        $value = EntityProperty::where('entity_id', $entityId)->where('name', $name)->value('value');

        return $value === null ? null : (string) $value;
    }

    /** Short reference label for an incident (its `ref`, falling back to the entity id). */
    public static function incidentRef(int $entityId): string
    {
        return self::incidentAttr($entityId, 'ref') ?? (string) $entityId;
    }

    /** Truncate a chat body for a notification subtitle. */
    public static function excerpt(string $text, int $limit = 80): string
    {
        return Str::limit(trim($text), $limit);
    }

    /** True unless `notifyConsent` is an explicit false (false, 'false', '0', 0). Closes BR_05. */
    public static function consentAllows(mixed $value): bool
    {
        return !($value === false || $value === 'false' || $value === '0' || $value === 0);
    }

    /**
     * Notify the incident's reporter about an operator's activity. No-ops when there's no reporter
     * or the actor IS the reporter. `$gateByConsent` applies the `notifyConsent` opt-out (BR_05):
     * true for status changes, false for chat replies (a direct interaction is never silenced).
     */
    public static function notifyIncidentReporter(int $entityId, int $actorUserId, string $titleKey, string $subtitle, string $icon, array $params = [], bool $gateByConsent = true): void
    {
        $reportedBy = self::incidentAttr($entityId, 'reportedBy');
        if ($reportedBy === null || $reportedBy === '') {
            return;
        }
        if ((int) $reportedBy === $actorUserId) {
            return;
        }
        // Consent gate: skip when the reporter explicitly declined notifications (status only).
        if ($gateByConsent && !self::consentAllows(self::incidentAttr($entityId, 'notifyConsent'))) {
            return;
        }
        self::push((int) $reportedBy, $titleKey, $subtitle, $params, 'light-info', $icon);
    }

    /** Notify the operator(s) assigned to an AssetIntervention (direct operator + team members). */
    public static function notifyAssignees(?string $assignedTo, ?string $assignedTeam, int $actorUserId, array $params = []): void
    {
        self::pushToAssignees(
            $assignedTo,
            $assignedTeam,
            $actorUserId,
            'notifications.assignment',
            'notifications.assignmentSub',
            'tabler-user-check',
            $params,
        );
    }

    /**
     * Notify the operator(s) handling an incident that its reporter posted a chat message. Resolves
     * the incident's AssetIntervention and fans out to its `assignedTo` / `assignedTeam`. Best-effort;
     * no-ops when the incident belongs to no intervention or nothing is assigned.
     */
    public static function notifyIncidentOperators(int $incidentEntityId, int $actorUserId, array $params = []): void
    {
        // The AssetIntervention group whose member entities include this incident.
        $group = EntityGroup::where('type', 'AssetIntervention')
            ->whereHas('entities', fn ($q) => $q->where('entities.id', $incidentEntityId))
            ->first();
        if ($group === null || $group->entity_id === null) {
            return;
        }

        // assignedTo / assignedTeam live on the intervention's linked (mirror) entity.
        $interventionEntityId = (int) $group->entity_id;
        $assignedTo = self::incidentAttr($interventionEntityId, 'assignedTo');
        $assignedTeam = self::incidentAttr($interventionEntityId, 'assignedTeam');

        self::pushToAssignees(
            $assignedTo,
            $assignedTeam,
            $actorUserId,
            'notifications.incidentMessageOp',
            'notifications.incidentMessageOpSub',
            'tabler-message',
            $params,
        );
    }

    /**
     * Shared fan-out for assignment recipients: push to the directly `assignedTo` operator and to
     * every member of the `assignedTeam`. Both are stable ids. The actor is always skipped and
     * duplicates are collapsed. Title/Subtitle are i18n keys.
     */
    private static function pushToAssignees(?string $assignedTo, ?string $assignedTeam, int $actorUserId, string $titleKey, string $subtitleKey, string $icon, array $params = []): void
    {
        foreach (self::assigneeIds($assignedTo, $assignedTeam) as $id) {
            if ($id !== $actorUserId) {
                self::push($id, $titleKey, $subtitleKey, $params, 'light-info', $icon);
            }
        }
    }

    /** Resolve the direct assignee + every team member to a deduplicated list of positive user ids. */
    private static function assigneeIds(?string $assignedTo, ?string $assignedTeam): array
    {
        $ids = [];
        if ($assignedTo !== null && $assignedTo !== '') {
            $ids[] = (int) $assignedTo;
        }
        if ($assignedTeam !== null && $assignedTeam !== '') {
            $ids = array_merge($ids, self::teamMemberIds($assignedTeam));
        }

        return array_values(array_unique(array_filter($ids, fn ($id) => $id > 0)));
    }

    /**
     * Return the member user ids of an OperatorsTeam given its entity id (empty if none). Resolving
     * by id is unambiguous — no name lookup, no cross-tenant collision. `members` is decoded with the
     * shared realtime caster (the mirror serializes arrays NGSI-style, which a bare json_decode drops).
     */
    private static function teamMemberIds(string $teamId): array
    {
        $membersRaw = self::incidentAttr((int) $teamId, 'members');
        $members = $membersRaw !== null ? RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($membersRaw) : null;

        return is_array($members) ? array_map('intval', $members) : [];
    }
}
