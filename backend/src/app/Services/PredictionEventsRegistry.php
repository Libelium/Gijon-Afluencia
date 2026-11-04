<?php

namespace App\Services;

use Illuminate\Contracts\Filesystem\Filesystem;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;

/**
 * The events registry of the predictions component: the CSV that says which days the occupancy
 * model must not learn from (a market, some fairs) and that the prediction panel's scenario
 * simulator draws on top of the normal forecast.
 *
 * predictions reads it (crowd_predictions/events_registry.py) from the same bucket, under the
 * same key and with the same columns, so this class must stay in step with that file:
 *   - key: {models prefix}/{tenant}/{scope as one segment}/events_registry.csv, the scope "/"
 *     being "_" and "/a/b" being "a_b" (helpers/model_storage.tenant_scope);
 *   - columns: date,event_type,device_ids,notes,end_date,start_hour,end_hour; local calendar
 *     days in ISO, device_ids a comma-separated list of zone URNs (empty = every zone), hours
 *     0-24 or empty.
 *
 * A row is addressed by its position in the file plus a hash of its values, so deleting a row
 * that someone else changed or moved in the meantime fails instead of deleting another one.
 * Writes are serialised with a lock: two people saving at once would otherwise each rewrite the
 * file from the copy they read, and one of the two events would be lost. It is a PostgreSQL
 * advisory lock, not Cache::lock: the database cache driver the deployments use would need a
 * cache_locks table this application does not create.
 */
class PredictionEventsRegistry
{
    public const FIELDS = ['date', 'event_type', 'device_ids', 'notes', 'end_date', 'start_hour', 'end_hour'];

    private const FILENAME = 'events_registry.csv';

    private const LOCK_WAIT = '5s';

    private Filesystem $storage;

    /** A disk name, not a Filesystem: the container would inject the default disk for that type. */
    public function __construct(?string $disk = null, private ?string $prefix = null)
    {
        $this->storage = Storage::disk($disk ?? config('predictions.events_disk'));
        $this->prefix ??= config('predictions.models_prefix');
    }

    public function key(string $tenant, string $scope): string
    {
        $segment = str_replace('/', '_', trim(trim($scope), '/')) ?: '_';

        return trim($this->prefix, '/') . '/' . trim($tenant) . "/{$segment}/" . self::FILENAME;
    }

    /**
     * The events, in file order.
     *
     * @return array<int, array{id: string, date: string, end_date: string, event_type: string,
     *     device_ids: string[], notes: string, start_hour: ?int, end_hour: ?int}>
     */
    public function events(string $tenant, string $scope): array
    {
        $events = [];
        foreach ($this->read($this->key($tenant, $scope)) as $index => $row) {
            if ($row['date'] === '') {
                continue;
            }
            $events[] = [
                'id' => self::idOf($index, $row),
                'date' => $row['date'],
                'end_date' => $row['end_date'] ?: $row['date'],
                'event_type' => $row['event_type'],
                'device_ids' => array_values(array_filter(array_map('trim', explode(',', $row['device_ids'])))),
                'notes' => $row['notes'],
                'start_hour' => $row['start_hour'] === '' ? null : (int) $row['start_hour'],
                'end_hour' => $row['end_hour'] === '' ? null : (int) $row['end_hour'],
            ];
        }

        return $events;
    }

    /**
     * Appends an event, already validated by the caller, and returns it as events() would.
     *
     * @param array{date: string, end_date?: ?string, event_type: string, device_ids?: ?string[],
     *     notes?: ?string, start_hour?: ?int, end_hour?: ?int} $event
     */
    public function append(string $tenant, string $scope, array $event): array
    {
        $key = $this->key($tenant, $scope);

        return $this->locked($key, function () use ($key, $event, $tenant, $scope) {
            $rows = $this->read($key);
            $rows[] = [
                'date' => $event['date'],
                'event_type' => $event['event_type'],
                'device_ids' => implode(',', $event['device_ids'] ?? []),
                'notes' => $event['notes'] ?? '',
                'end_date' => ($event['end_date'] ?? null) && $event['end_date'] !== $event['date'] ? $event['end_date'] : '',
                'start_hour' => isset($event['start_hour']) ? (string) $event['start_hour'] : '',
                'end_hour' => isset($event['end_hour']) ? (string) $event['end_hour'] : '',
            ];
            $this->write($key, $rows);

            $events = $this->events($tenant, $scope);

            return end($events);
        });
    }

    /** False if no row has that id any more: deleted, moved or changed since it was listed. */
    public function delete(string $tenant, string $scope, string $id): bool
    {
        $key = $this->key($tenant, $scope);

        return $this->locked($key, function () use ($key, $id) {
            $rows = $this->read($key);
            [$index] = explode(':', $id, 2) + [null];
            if (!ctype_digit((string) $index) || !isset($rows[(int) $index]) || self::idOf((int) $index, $rows[(int) $index]) !== $id) {
                return false;
            }
            unset($rows[(int) $index]);
            $this->write($key, array_values($rows));

            return true;
        });
    }

    private static function idOf(int $index, array $row): string
    {
        return $index . ':' . substr(sha1(json_encode(array_values($row))), 0, 12);
    }

    /** Released with the transaction, also if the callback throws. */
    private function locked(string $key, callable $callback): mixed
    {
        return DB::transaction(function () use ($key, $callback) {
            DB::statement("SET LOCAL lock_timeout = '" . self::LOCK_WAIT . "'");
            DB::select('SELECT pg_advisory_xact_lock(?)', [crc32("prediction-events:{$key}")]);

            return $callback();
        });
    }

    /**
     * The data rows with every column, in file order, keyed from 0 as predictions numbers them.
     * A file written with fewer columns (the first version had four) reads as empty in the rest.
     *
     * @return array<int, array<string, string>>
     */
    private function read(string $key): array
    {
        if (!$this->storage->exists($key)) {
            return [];
        }

        $stream = fopen('php://temp', 'r+');
        fwrite($stream, (string) $this->storage->get($key));
        rewind($stream);

        $header = null;
        $rows = [];
        while (($line = fgetcsv($stream, null, ',', '"', '')) !== false) {
            if ($line === [null]) {
                continue; // a blank line, as csv.DictReader skips it
            }
            if ($header === null) {
                // A file saved from a spreadsheet may start with a byte order mark.
                $header = array_map(fn ($name) => preg_replace('/^\x{FEFF}/u', '', trim((string) $name)), $line);
                continue;
            }
            $values = [];
            foreach (self::FIELDS as $field) {
                $position = array_search($field, $header, true);
                $values[$field] = $position === false ? '' : trim((string) ($line[$position] ?? ''));
            }
            $rows[] = $values;
        }
        fclose($stream);

        return $rows;
    }

    private function write(string $key, array $rows): void
    {
        $stream = fopen('php://temp', 'r+');
        fputcsv($stream, self::FIELDS, ',', '"', '');
        foreach ($rows as $row) {
            fputcsv($stream, array_map(fn ($field) => $row[$field] ?? '', self::FIELDS), ',', '"', '');
        }
        rewind($stream);
        $this->storage->put($key, stream_get_contents($stream));
        fclose($stream);
    }
}
