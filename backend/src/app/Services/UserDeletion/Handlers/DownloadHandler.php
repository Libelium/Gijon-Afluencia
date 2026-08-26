<?php

namespace App\Services\UserDeletion\Handlers;

use App\Contracts\UserResourceHandlerInterface;
use App\Models\Download;
use App\Models\User;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Log;

class DownloadHandler implements UserResourceHandlerInterface
{
    /**
     * Transfers download records from one user to another.
     * S3 files are deleted beforehand since the new owner will regenerate them on demand.
     *
     * @param User $from User whose downloads will be transferred.
     * @param User $to User who will receive the download records.
     * @param string|null $modelClass Unused — model is hardcoded to Download.
     * @return void
     */
    public static function transfer(User $from, User $to, ?string $modelClass = null): void
    {
        self::deleteS3Files($from);

        Download::where('user_id', $from->id)
            ->update(['user_id' => $to->id]);
    }

    /**
     * Deletes all S3 files and download records belonging to the given user.
     *
     * @param User $user User whose downloads will be deleted.
     * @param string|null $modelClass Unused — model is hardcoded to Download.
     * @return void
     */
    public static function clean(User $user, ?string $modelClass = null): void
    {
        self::deleteS3Files($user);

        Download::where('user_id', $user->id)->delete();
    }

    /**
     * Deletes the S3 files associated with a user's downloads.
     * Failures are logged as warnings and do not interrupt the process.
     *
     * @param User $user User whose S3 files will be deleted.
     * @return void
     */
    private static function deleteS3Files(User $user): void
    {
        Download::where('user_id', $user->id)
            ->get()
            ->each(function (Download $download) {
                $path = $download->file_name . '.' . $download->file_extension;

                try {
                    Storage::delete($path);
                } catch (\Throwable $e) {
                    Log::warning('user_deletion.download.s3_delete_failed', [
                        'download_id' => $download->id,
                        'path'        => $path,
                        'error'       => $e->getMessage(),
                    ]);
                }
            });
    }
}
