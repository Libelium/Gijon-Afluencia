<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Controllers\Controller;
use App\Models\Entity;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Str;
use Illuminate\Http\Response;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use App\Models\MarkdownFile;
use Elastic\ScoutDriverPlus\Support\Query;
use Symfony\Component\HttpFoundation\StreamedResponse;

class HelpController extends Controller
{
    const DOCS_FOLDER = '/platform-docs/';

    /**
     * Checks if the folder given is a valid one from the documentation
     * and if the user has access to it
     */
    private function validateRoute($folder): bool
    {
        $userValidTypes = $this->getUserLicenses();

        return in_array($folder, $userValidTypes);
    }

    public function getChangelog(string $version): Response
    {
        $file = Storage::disk('s3')->get(self::DOCS_FOLDER . '/changelog/' . $version . '.md');

        if ($file == null) {
            return response("File not found", 404);
        }

        return response($file, 200)->header('Access-Control-Allow-Origin', '*')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    }

    public function getChangelogIndex(): Response
    {

        $resultIndex = [];

        $files = Storage::disk('s3')->files(self::DOCS_FOLDER . '/changelog');

        if ($files != null) {
            foreach ($files as $file) {
                $filename = basename($file, '.md');
                $resultIndex[] = $filename;
            }
        }

        return response($resultIndex, 200)->header('Access-Control-Allow-Origin', '*')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    }

    /**
     * Returns an image file linked from the documentation
     */
    public function getImage(string $folder, string $filepath): Response
    {
        $file = Storage::disk('s3')->get(self::DOCS_FOLDER . $folder . '/' . $filepath);

        if ($file == null) {
            return response("File not found", 404);
        }

        return response($file, 200)->header('Content-Type', 'image/png')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    }


    /**
     * Returns an array with the licenses the user has access to
     */
    public function getUserLicenses(): array
    {
        // Available options at the moment are:
        // ['libeliumcloud', 'meshlium', 'waspmote', 'aqs', 'smartspot', 'parking-v2'];
        $user = Auth::user();
        $entititesTypeToDoc = [
            'Meshlium' => 'meshlium',
            'Sensor Board' => 'waspmote',
            'Air Quality Station' => 'aqs',
            'SmartSpot' => 'smartspot',
            'Smart Parking' => 'parking-v2'
        ];

        // ====================Disabled for pre================================================
        // $userEntitiesTypes = Entity::join('entity_user', 'entities.id', '=', 'entity_user.entity_id')
        //     ->join('entity_types', 'entities.entity_type_id', '=', 'entity_types.id')
        //     ->where('entities.subscribed_until', '>', now())
        //     ->where('entity_user.user_id', $user->id)
        //     ->where('entity_user.status', 'owner')
        //     ->distinct()
        //     ->pluck('entity_types.name');

        // $resultList = collect($userEntitiesTypes)->map(function ($item) use ($entititesTypeToDoc) {
        //     return isset($entitiesTypeToDoc[$item]) ? $entititesTypeToDoc[$item] : null;
        // })->filter();

        // Now the cloud license is not checked with the DB, so it will be added
        // if there the user has any other license
        // if ($resultList->isNotEmpty()) {
        //     $resultList->push('libeliumcloud');
        // }
        // return $resultList->values()->all();
        // =============================================================================================

        $resultList = [
            'meshlium',
            'waspmote',
            'aqs',
            'smartspot',
            'parking-v2',
            'libeliumcloud'
        ];

        return $resultList;
    }

    /**
     * Returns the Markdown content of an existing file from the 'documentacion' folder in the S3 bucket
     */
    public function getFileContent(string $folder, string $filepath): Response
    {
        if (!$this->validateRoute($folder)) {
            return response('Not a valid route', 404);
        }

        $file = Storage::disk('s3')->get(self::DOCS_FOLDER . $folder . '/' . $filepath . '.md');

        if ($file == null) {
            return response("File not found", 404);
        }

        return response($file, 200)->header('Access-Control-Allow-Origin', '*')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    }


    /**
     * Processes the content of an index.md file and returns an array with the
     * structure of the index ready to be used on the front-end
     */
    function parseMarkdownIndexes(string $folder, string $file, int &$id)
    {
        $lines = explode("\n", $file);

        $result = [];
        $currentParent = null;

        foreach ($lines as $line) {
            // Trim spaces to ensure the detection works even if there are leading/trailing spaces
            $trimmedLine = trim($line);

            // Check for parent line
            if (Str::startsWith($trimmedLine, '- ##')) {
                if ($currentParent) {
                    $result[] = $currentParent; // Save the last parent object
                }

                preg_match('/\[(.*?)\]\((.*?)\)/', $trimmedLine, $matches);

                $noPrefixLink = str_replace('/{{route}}/{{version}}', $folder, $matches[2] ?? '');

                $currentParent = [
                    'title' => $matches[1] ?? '',
                    'id' => $id,
                    'to' => [
                        'name' => 'helpview',
                        'params' => [
                            'filePath' => $noPrefixLink
                        ]
                    ],
                    //$matches[2] ?? '',
                ];
            }
            // Check for child line
            elseif (Str::startsWith($trimmedLine, '- ')) {
                preg_match('/\[(.*?)\]\((.*?)\)/', $trimmedLine, $matches);

                // a preg_replace for the string /{{route}}/{{version}} at the beginning of another string
                $noPrefixLink = str_replace('/{{route}}/{{version}}', $folder, $matches[2] ?? '');

                $child = [
                    'title' => $matches[1] ?? '',
                    'id' => $id,
                    'to' => [
                        'name' => 'helpview',
                        'params' => [
                            'filePath' => $noPrefixLink
                        ]
                    ],
                    //$matches[2] ?? '',
                ];

                if ($currentParent) {
                    $currentParent['children'][] = $child;
                } else {
                    $result[] = $child;
                }
            }
            $id++;
        }

        // Ensure the last parent object is saved
        if ($currentParent) {
            $result[] = $currentParent;
        }

        return $result;
    }

    /**
     * Encapsulate the obtention of a simplified element of the index
     * to be used for the next and prev values
     */
    private function getNavigableChildren($element): array
    {
        return [
            'to' => $element['to'],
            'title' => $element['title']
        ];
    }


    /**
     * Flattens the array to simplify the obtention of the next and prev values
     */
    private function flattenArray(array $array)
    {
        return array_reduce($array, function ($carry, $item) {
            if (isset($item['to'])) {
                $carry[$item['id'] . $item['title']] = [
                    'title' => $item['title'],
                    'to' => $item['to']['params']['filePath']
                ];
            }
            if (!empty($item['children'])) {
                $carry += $this->flattenArray($item['children']);
            }
            return $carry;
        }, []);
    }

    private function getPrevAndNextValues($flattenedArray, $key): array
    {
        $keys = array_keys($flattenedArray);
        $keyPosition = array_search($key, $keys);

        $prev = null;
        $next = null;

        if ($keyPosition > 0) {
            $prev = $this->getNavigableChildren($flattenedArray[$keys[$keyPosition - 1]]);
        }

        if ($keyPosition < count($keys) - 1) {
            $next = $this->getNavigableChildren($flattenedArray[$keys[$keyPosition + 1]]);
        }

        return [
            'prev' => $prev,
            'next' => $next
        ];
    }

    private function applyFunctionToNestedArrays(&$array, $function, &$functionParams = null)
    {
        foreach ($array as &$value) {
            if (!empty($value['children'])) {
                $this->applyFunctionToNestedArrays($value['children'], $function, $functionParams);
            }
            if (isset($value['to'])) {
                $value = $function($value, $functionParams);
            }
        }
    }

    /**
     *  Takes the generated array and adds the prev and next values for every item
     */
    private function populateNavigationValues(array $elements): array
    {
        $flattenedArray = $this->flattenArray($elements);

        // Generate a variable function that will be used to add the prev and next values for every item
        $function = function ($element) use ($flattenedArray) {
            return array_merge($element, $this->getPrevAndNextValues($flattenedArray, $element['id'] . $element['title']));
        };

        $this->applyFunctionToNestedArrays($elements, $function, $flattenedArray);

        // Maybe use it as a reference?
        return $elements;
    }

    public function searchContent(Request $request)
    {
        $searchText = $request->input('searchText');

        if ($searchText == null || $searchText == '') {
            return response([], 200)->header('Access-Control-Allow-Origin', '*')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
        }

        // Query builder that tries to match the content field with the given text
        $query = Query::match()
            ->field('content')
            ->query($request->input('searchText'))
            ->fuzziness(1);

        $results = MarkdownFile::searchQuery($query)->execute()->hits();

        $contents = $results->map(function ($result) {
            return [
                'path' => $result->document()->content()['route'],
                'title' => $result->document()->content()['title'],
            ];
        });

        return response($contents, 200)->header('Access-Control-Allow-Origin', '*')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    }

    /**
     * Generate the index for the given folder of the documentation
     * The S3 returns the markdown content of the index.md file inside the folder
     * and it is parsed to generate the array that will be used to build the
     * navigable index on the front-end
     */
    public function getFolderIndex(): Response
    {

        $options = $this->getUserLicenses();

        $resultIndex = [];

        $id = 1;

        foreach ($options as $folder) {
            $file = Storage::disk('s3')->get(self::DOCS_FOLDER . $folder . '/index.md');

            if ($file != null) {
                $indexContent = $this->parseMarkdownIndexes($folder, $file, $id);
                $resultIndex[] = [
                    'title' => $folder,
                    'id' => $id,
                    'icon' => [
                        'icon' => 'tabler-folder'
                    ],
                    'children' => $indexContent
                ];
            }
            $id++;
        }


        $resultIndex = $this->populateNavigationValues($resultIndex);

        return response($resultIndex, 200)->header('Access-Control-Allow-Origin', '*')->header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
    }

    public function downloadDocumentation(string $lang): Response|StreamedResponse
    {
        $folder = 'documentation/' . $lang;

        $storage = Storage::disk('s3');

        $files = $storage->files($folder);

        if (empty($files)) {
            $folder = 'documentation/en';
            $files = $storage->files($folder);

            if (empty($files)) {
                return response('No documentation found for the specified language.', 404);
            }
        }

        $firstFile = $files[0];
        $filename = basename($firstFile);

        // Stream the file from S3 instead of loading it into memory:
        // the PDFs weigh tens of MB and response($contents) would duplicate
        // the string, exceeding PHP's memory_limit
        return $storage->download($firstFile, $filename, [
            'Content-Type' => 'application/pdf',
            'File-Name' => $filename
        ]);
    }
}
