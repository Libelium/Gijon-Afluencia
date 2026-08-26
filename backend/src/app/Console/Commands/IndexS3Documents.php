<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Models\MarkdownFile;
use Illuminate\Support\Facades\Storage;

class IndexS3Documents extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'app:index-s3-documents';
    const DOCS_FOLDER = '/platform-docs/';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Update the Elasticearch index for S3 documents content';


    private function getFileNameFromIndex($indexList, $file)
    {
        // Get the index file for the current file
        $index = $indexList[explode('/', $file)[1]];

        // Get the file name from the index file
        $fileName = basename($file, '.md');

        $indexNameRow = collect(explode("\n", $index))->filter(function ($line) use ($fileName) {
            return strpos(trim($line), $fileName) !== false;
        });


        preg_match('/\[(.*?)\]\(\/\{\{route\}\}\/\{\{version\}\}\/(.*?)\)/', $indexNameRow->first(), $matches);

        return $matches;
    }

    /**
     * Loads every index file from the S3 bucket
     * to be used later to get the file name
     * 
     * @return array
     */
    private function loadIndexList()
    {
        $indexList = [];

        // List the first level folders of the s3 disk
        $folders = Storage::disk('s3')->directories(self::DOCS_FOLDER);

        foreach ($folders as $folder) {
            $index = Storage::disk('s3')->get($folder . '/index.md');
            $indexList[basename($folder)] = $index;
        }

        return $indexList;
    }

    /**
     * Execute the console command.
     */
    public function handle()
    {

        $indexList = $this->loadIndexList();

        $filesList = collect(Storage::disk('s3')->allFiles(self::DOCS_FOLDER))->filter(function ($file) {
            return strpos($file, '.md') !== false;
        });

        foreach ($filesList as $file) {
            $content = Storage::disk('s3')->get($file);

            $name = $this->getFileNameFromIndex($indexList, $file);

            if ($name) {
                $markdownFile = new MarkdownFile();
                $parentDir = explode('/', $file)[1];
                $markdownFile->fill([
                    'route' => $parentDir . "/" . $name[2],
                    'title' => $parentDir . " - " . $name[1],
                    'content' => $content,
                ]);

                print("Indexing file: " . $name[1] . "\n");

                // Indexes into Elasticsearch
                $markdownFile->searchable();
            }

        }
    }
}
