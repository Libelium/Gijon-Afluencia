<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Controllers\Controller;
use App\Models\Regulation;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Validator;
use App\Repositories\OrganizationRepository;
use App\Repositories\ResourcePermissionRepository;
use App\Authorization\AppResourcePermission;
use App\Http\V1\Resources\RegulationResource;

class RegulationController extends Controller
{
    /**
     * Display a listing of the resource. Paginated.
     *
     * @return \Illuminate\Http\Response
     */

    public function paginate(Request $request)
    {
        $request->validate([
            'pagination' => 'boolean',
            'page' => 'numeric',
            'paginationSize' => 'numeric',
            'search' => 'string | nullable',
            'orderBy' => 'string | nullable',
            'orderDirection' => 'boolean | nullable',
            'datamodel' => 'string | nullable',
        ]);

        $query = Regulation::when($request->datamodel, function ($query, $datamodel) {
            return $query->where('datamodel', $datamodel);
        })
            // search
            ->when($request->search, function ($query, $search) {
                return $query->where('name', 'like', '%' . $search . '%');
            })
            // sort
            ->when($request->orderBy, function ($query, $orderBy) use ($request) {
                return $query->orderBy($orderBy, $request->orderDirection ? 'asc' : 'desc');
            });

        $query = ResourcePermissionRepository::updateQueryWithPermissionCheck(
            $query,
            AppResourcePermission::READ,
            Auth::id(),
            Regulation::class
        );

        // pagination
        $regulations = $query->paginate($request->paginationSize, ['regulations.*'], 'page', $request->page);

        $response = [
            "rows" => RegulationResource::collection($regulations->items()),
            "count" => $regulations->total(),
        ];

        return response()->json($response);
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request)
    {
        $request->validate([
            'name' => 'required|string',
            'datamodel' => 'nullable|string',
            'content' => 'nullable|array',
        ]);

        $request['user_id'] = Auth::id();

        $this->authorize('create', Regulation::class);

        $regulation = Regulation::create($request->all());

        OrganizationRepository::assignResourceToOrganization(Auth::user()->organization_id, $regulation);

        $default_permissions = AppResourcePermission::defaultPermissions();
        Auth::user()->giveResourcePermissionsTo($default_permissions, $regulation, true);

        return response(new RegulationResource($regulation), 200);
    }

    /**
     * Display the specified resource.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function show($id)
    {
        $user = Auth::user();
        $regulation = Regulation::findOrFail($id);

        $this->authorize('read', $regulation);

        return response(new RegulationResource($regulation), 200);
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request, $id)
    {
        $request->validate([
            'name' => 'required|string',
            'datamodel' => 'nullable|string',
            'content' => 'nullable|array',
        ]);

        $regulation = Regulation::findOrFail($id);

        $this->authorize('update', $regulation);

        $regulation->update($request->all());

        return response(new RegulationResource($regulation), 200);
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function destroy($id)
    {
        $regulation = Regulation::findOrFail($id);

        $this->authorize('delete', $regulation);

        ResourcePermissionRepository::deleteAllPermissionsForResource($regulation);
        OrganizationRepository::unassignResourceFromAnyOrganization($regulation);

        $regulation->deleteOrFail();

        return response()->json(true, 200);
    }
}
