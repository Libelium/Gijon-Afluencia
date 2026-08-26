<?php

namespace App\Repositories;

use App\Models\AccessAttempt;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

class AccessAttemptRepository
{
    /**
     * Return paginated results using query and filters
     *
     * @return Illuminate\Support\Collection
     */
    public static function paginate($pagination_size, $page, $order_column, $order_direction, $search_text = null, $start_date = null, $end_date = null)
    {
        $position = (intval($page) - 1) * intval($pagination_size);
        $records = self::queryShared($search_text)
            ->orderBy($order_column, $order_direction)
            ->offset($position)
            ->take($pagination_size)
            ->when($search_text, function ($query, $search_text) {
                $query->where('access_attempts.ip', 'ILIKE', '%' . $search_text . '%');
            })
            ->when($end_date, function ($query, $end_date) {
                $query->where('access_attempts.created_at', '<', $end_date);
            })
            ->when($start_date, function ($query, $start_date) {
                $query->where('access_attempts.created_at', '>', $start_date);
            })
            ->get();

        return $records;
    }

    /**
     * Get the total count needed to create the numbers of the pagination in the frontend
     *
     * @return integer
     */
    public static function recordsCount($search_text = null, $start_date = null, $end_date = null)
    {
        $count = self::queryShared($search_text)
            ->when($end_date, function ($query, $end_date) {
                $query->where('access_attempts.created_at', '<', $end_date);
            })
            ->when($start_date, function ($query, $start_date) {
                $query->where('access_attempts.created_at', '>', $start_date);
            })
            ->count();

        return $count;
    }

    /**
     * Makes the main part of the query, with filters and conditions to restrict the search
     * @param $query
     * @param $search_text
     * @param $filters
     * @return object
     */
    private static function setSearch($query, $search_text)
    {
        return $query
            ->when($search_text, function ($query, $search_text) {
                $query->where('access_attempts.email', 'ILIKE', '%' . $search_text . '%');
            });
    }

    private static function queryShared($search_text = null)
    {
        $userEmail = Auth::user()->email;
        $query = AccessAttempt::select(
            'id',
            'email',
            'ip',
            'success',
            'created_at',
        )->where('email', $userEmail);

        return $query;
    }

    /**
     * Check if the user should be locked, based on the last logins
     */
    public static function shouldLock(string $email, int $maxAccessAttempts, int $blockIntervalCheck): bool
    {

        $lastLoginsQuery = AccessAttempt::where('email', $email)
            ->where('created_at', '>=', now()->subMinutes($blockIntervalCheck))
            ->orderBy('created_at', 'desc')
            ->limit($maxAccessAttempts);

        $countNotSuccess = DB::query()
            ->fromSub($lastLoginsQuery, 'last_logins')
            ->where('success', false)
            ->count();

        return $countNotSuccess >= $maxAccessAttempts;
    }

    public static function cleanLogsUntilLastSuccess(string $email)
    {
        $lastSuccess = AccessAttempt::where('email', $email)
            ->where('success', true)
            ->orderBy('created_at', 'desc')
            ->first();

        if ($lastSuccess) {
            AccessAttempt::where('email', $email)
                ->where('created_at', '>', $lastSuccess->created_at)
                ->delete();
        }
    }
}
